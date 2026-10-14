"""SQS adapter contracts. No AWS account and no backend process."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from temperature_demo.config import repo_root
from temperature_demo.sqs_adapter.config import load_adapter_config
from temperature_demo.sqs_adapter.contracts import DeliveryFailed, EventRejected
from temperature_demo.sqs_adapter.processor import process_message
from temperature_demo.sqs_adapter.transform import reading_from_event
from temperature_demo.sqs_adapter.worker import poll, poll_once

EVENT = {
    "event_id": "demo-002",
    "device_id": "thermostat-001",
    "temperature": 72.4,
    "unit": "F",
    "observed_at": "2026-10-14T15:00:00Z",
}

READING = {
    "house_id": "home-a",
    "sensor_id": "thermostat-001",
    "temperature": 72.4,
    "unit": "F",
    "observed_at": "2026-10-14T15:00:00Z",
}


class FakeQueue:
    def __init__(self, messages: list[dict[str, str]] | None = None) -> None:
        self.messages = list(messages or [])
        self.deleted: list[str] = []
        self.receives = 0

    def receive_one(self) -> dict[str, str] | None:
        self.receives += 1
        if not self.messages:
            return None
        return self.messages.pop(0)

    def delete(self, receipt_handle: str) -> None:
        self.deleted.append(receipt_handle)


class FakePoster:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, backend_url: str, payload: dict[str, object], *, timeout: float) -> dict[str, object]:
        self.calls.append((backend_url, payload))
        if self.fail is not None:
            raise self.fail
        return {"id": "stored-1", "house_id": payload["house_id"]}


def test_valid_event_becomes_a_reading() -> None:
    assert reading_from_event(dict(EVENT), "home-a") == READING


def test_missing_required_fields_fail() -> None:
    for field in ("event_id", "device_id", "temperature", "unit", "observed_at"):
        payload = dict(EVENT)
        del payload[field]
        try:
            reading_from_event(payload, "home-a")
        except EventRejected as exc:
            if field not in str(exc):
                raise AssertionError(f"{field} error was {exc}") from exc
        else:
            raise AssertionError(f"missing {field} was accepted")


def test_invalid_unit_timestamp_and_temperature_fail() -> None:
    _reject(dict(EVENT, unit="K"), "home-a")
    _reject(dict(EVENT, unit="f"), "home-a")
    _reject(dict(EVENT, observed_at="2026-10-14T15:00:00"), "home-a")
    _reject(dict(EVENT, observed_at="yesterday"), "home-a")
    _reject(dict(EVENT, temperature=True), "home-a")
    _reject(dict(EVENT, temperature="72.4"), "home-a")


def test_absent_house_id_uses_configured_home() -> None:
    reading = reading_from_event(dict(EVENT), "home-a")
    if reading["house_id"] != "home-a":
        raise AssertionError(f"broadcast event did not use HOME_ID: {reading}")
    other = reading_from_event(dict(EVENT), "home-b")
    if other["house_id"] != "home-b" or other["sensor_id"] != "thermostat-001":
        raise AssertionError(f"home-b reading drifted: {other}")


def test_present_house_id_must_match_home_id() -> None:
    matched = reading_from_event(dict(EVENT, house_id="home-a"), "home-a")
    if matched["house_id"] != "home-a" or matched["sensor_id"] != "thermostat-001":
        raise AssertionError(f"matching house_id was rewritten: {matched}")
    try:
        reading_from_event(dict(EVENT, house_id="home-b"), "home-a")
    except EventRejected as exc:
        if "home-b" not in str(exc) or "home-a" not in str(exc):
            raise AssertionError(f"mismatch error was {exc}") from exc
    else:
        raise AssertionError("mismatched house_id was accepted")


def test_mismatched_house_id_is_not_posted_or_deleted() -> None:
    import json

    poster = FakePoster()
    queue = FakeQueue(
        [
            {
                "MessageId": "msg-mismatch",
                "ReceiptHandle": "receipt-mismatch",
                "Body": json.dumps(dict(EVENT, house_id="home-b", event_id="routing-home-b-001")),
            }
        ]
    )
    outcome = poll_once(queue, home_id="home-a", backend_url="http://127.0.0.1:18081", post=poster)
    if outcome != "retained" or queue.deleted or poster.calls:
        raise AssertionError(
            f"mismatch outcome={outcome} deleted={queue.deleted} posts={poster.calls}"
        )


def test_http_success_and_failure() -> None:
    poster = FakePoster()
    process_message(dict(EVENT), "home-a", "http://127.0.0.1:18081", post=poster)
    if poster.calls != [("http://127.0.0.1:18081", READING)]:
        raise AssertionError(f"POST was {poster.calls}")

    failing = FakePoster(fail=DeliveryFailed("backend unavailable", status=500))
    try:
        process_message(dict(EVENT), "home-a", "http://127.0.0.1:18081", post=failing)
    except DeliveryFailed:
        pass
    else:
        raise AssertionError("HTTP failure was ignored")
    if len(failing.calls) != 1:
        raise AssertionError("failed delivery did not attempt the POST")


def test_sqs_delete_follows_http_result() -> None:
    poster = FakePoster()
    queue = FakeQueue([_message("receipt-a")])
    outcome = poll_once(queue, home_id="home-a", backend_url="http://127.0.0.1:18081", post=poster)
    if outcome != "deleted" or queue.deleted != ["receipt-a"]:
        raise AssertionError(f"success outcome={outcome} deleted={queue.deleted}")

    failing = FakePoster(fail=DeliveryFailed("backend unavailable", status=500))
    retained = FakeQueue([_message("receipt-b")])
    outcome = poll_once(
        retained,
        home_id="home-b",
        backend_url="http://127.0.0.1:18082",
        post=failing,
    )
    if outcome != "retained" or retained.deleted:
        raise AssertionError(f"failure outcome={outcome} deleted={retained.deleted}")


def test_malformed_json_is_retained() -> None:
    queue = FakeQueue(
        [
            {"MessageId": "m1", "ReceiptHandle": "receipt-bad", "Body": "{not-json"},
            {
                "MessageId": "m2",
                "ReceiptHandle": "receipt-envelope",
                "Body": '{"Type":"Notification","TopicArn":"arn:aws:sns:us-east-2:1:temperature-readings","Message":"{}"}',
            },
        ]
    )
    poster = FakePoster()
    first = poll_once(queue, home_id="home-a", backend_url="http://127.0.0.1:18081", post=poster)
    second = poll_once(queue, home_id="home-a", backend_url="http://127.0.0.1:18081", post=poster)
    if first != "retained" or second != "retained" or queue.deleted or poster.calls:
        raise AssertionError(
            f"malformed outcomes {(first, second)} deleted={queue.deleted} posts={poster.calls}"
        )


def test_two_configs_share_one_implementation() -> None:
    home_a = load_adapter_config(_environ("home-a", "18081"))
    home_b = load_adapter_config(_environ("home-b", "18082"))
    if home_a.home_id == home_b.home_id or home_a.queue_url == home_b.queue_url:
        raise AssertionError("homes collapsed to one configuration")
    if home_a.backend_url != "http://127.0.0.1:18081":
        raise AssertionError(home_a.backend_url)
    if home_b.backend_url != "http://127.0.0.1:18082":
        raise AssertionError(home_b.backend_url)
    try:
        load_adapter_config({})
    except Exception as exc:
        if "HOME_ID" not in str(exc):
            raise
    else:
        raise AssertionError("empty environment was accepted")


def test_processor_does_not_import_boto3_or_the_backend() -> None:
    root = repo_root() / "temperature_demo" / "sqs_adapter"
    for name in ("contracts.py", "config.py", "transform.py", "delivery.py", "processor.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                if module.split(".")[0] in {"boto3", "temperature_iot_backend"}:
                    raise AssertionError(f"{name} imports {module}")
    worker = (root / "worker.py").read_text(encoding="utf-8")
    if "import boto3" not in worker:
        raise AssertionError("worker has no boto3 import")
    tree = ast.parse(worker)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("boto3"):
            raise AssertionError("boto3 is imported at worker module scope")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "boto3":
                    raise AssertionError("boto3 is imported at worker module scope")


def test_poll_stops_without_a_receive() -> None:
    queue = FakeQueue([_message("receipt-a")])
    poll(queue, home_id="home-a", backend_url="http://127.0.0.1:18081", stop=lambda: True)
    if queue.receives != 0:
        raise AssertionError("stopped poll still received")


def test_help_is_local() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "temperature_demo.sqs_adapter", "--help"],
        cwd=repo_root(),
        check=False,
        text=True,
        capture_output=True,
        env=_help_env(),
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    if "HOME_ID" not in completed.stdout:
        raise AssertionError("help text does not describe HOME_ID")


def _reject(payload: dict[str, object], home_id: str) -> None:
    try:
        reading_from_event(payload, home_id)
    except EventRejected:
        return
    raise AssertionError(f"accepted {payload}")


def _message(receipt: str) -> dict[str, str]:
    import json

    return {
        "MessageId": "msg-1",
        "ReceiptHandle": receipt,
        "Body": json.dumps(EVENT),
    }


def _environ(home_id: str, port: str) -> dict[str, str]:
    return {
        "HOME_ID": home_id,
        "SQS_QUEUE_URL": f"https://sqs.us-east-2.amazonaws.com/123456789012/temperature-{home_id}",
        "BACKEND_URL": f"http://127.0.0.1:{port}",
        "AWS_REGION": "us-east-2",
        "AWS_PROFILE": "temperature-iot-terraform",
    }


def _help_env() -> dict[str, str]:
    import os

    hidden = {"HOME_ID", "SQS_QUEUE_URL", "BACKEND_URL", "AWS_REGION", "AWS_PROFILE"}
    return {key: value for key, value in os.environ.items() if key not in hidden}


def _adapter_sources_exist() -> None:
    root = Path(repo_root() / "temperature_demo" / "sqs_adapter")
    if not (root / "processor.py").is_file():
        raise AssertionError(f"missing {root / 'processor.py'}")


if __name__ == "__main__":
    _adapter_sources_exist()
    test_valid_event_becomes_a_reading()
    test_missing_required_fields_fail()
    test_invalid_unit_timestamp_and_temperature_fail()
    test_absent_house_id_uses_configured_home()
    test_present_house_id_must_match_home_id()
    test_mismatched_house_id_is_not_posted_or_deleted()
    test_http_success_and_failure()
    test_sqs_delete_follows_http_result()
    test_malformed_json_is_retained()
    test_two_configs_share_one_implementation()
    test_processor_does_not_import_boto3_or_the_backend()
    test_poll_stops_without_a_receive()
    test_help_is_local()
    print("passed")

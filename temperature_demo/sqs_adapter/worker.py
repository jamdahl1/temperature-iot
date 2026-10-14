"""Poll one SQS queue. boto3 is imported only while building the live client."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import time
from typing import Any, Callable

from temperature_demo.sqs_adapter.config import load_adapter_config
from temperature_demo.sqs_adapter.contracts import DeliveryFailed, EventRejected
from temperature_demo.sqs_adapter.delivery import HTTP_TIMEOUT_SECONDS
from temperature_demo.sqs_adapter.processor import Poster, process_message

_LOG = logging.getLogger("temperature_demo.sqs_adapter")
WAIT_SECONDS = 20
RECEIVE_ERROR_PAUSE_SECONDS = 5.0


class BotoSqsQueue:
    """One queue. Long-polls a single message and deletes by receipt handle."""

    def __init__(self, client: Any, queue_url: str, wait_seconds: int = WAIT_SECONDS) -> None:
        self._client = client
        self._queue_url = queue_url
        self._wait_seconds = wait_seconds

    def receive_one(self) -> dict[str, Any] | None:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=self._wait_seconds,
        )
        messages = response.get("Messages") or []
        if not messages:
            return None
        return messages[0]

    def delete(self, receipt_handle: str) -> None:
        self._client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt_handle,
        )


def build_sqs_client(region: str, profile: str | None) -> Any:
    """Open an SQS client through the default credential chain."""

    import boto3

    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)
    return session.client("sqs", region_name=region)


def poll_once(
    queue: Any,
    *,
    home_id: str,
    backend_url: str,
    post: Poster | None = None,
) -> str:
    """Handle at most one message. Return empty, deleted, or retained."""

    message = queue.receive_one()
    if message is None:
        return "empty"
    receipt = message.get("ReceiptHandle")
    body = message.get("Body")
    if not isinstance(body, str) or not isinstance(receipt, str) or not receipt:
        _LOG.warning("home=%s outcome=retained reason=incomplete_message", home_id)
        return "retained"
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError:
        _LOG.warning("home=%s outcome=retained reason=malformed_json", home_id)
        return "retained"
    event_id = _event_id(decoded)
    try:
        if post is None:
            process_message(decoded, home_id, backend_url)
        else:
            process_message(decoded, home_id, backend_url, post=post)
    except (EventRejected, DeliveryFailed) as exc:
        _LOG.warning(
            "home=%s event_id=%s outcome=retained error=%s",
            home_id,
            event_id,
            exc,
        )
        return "retained"
    queue.delete(receipt)
    _LOG.info("home=%s event_id=%s outcome=deleted", home_id, event_id)
    return "deleted"


def poll(
    queue: Any,
    *,
    home_id: str,
    backend_url: str,
    stop: Callable[[], bool],
    post: Poster | None = None,
    pause_seconds: float = RECEIVE_ERROR_PAUSE_SECONDS,
) -> None:
    """Poll until stop() is true. Receive errors pause instead of spinning."""

    while not stop():
        try:
            poll_once(queue, home_id=home_id, backend_url=backend_url, post=post)
        except Exception:
            if stop():
                return
            _LOG.exception("home=%s outcome=retained reason=receive_failed", home_id)
            time.sleep(pause_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="temperature-demo-sqs-adapter",
        description=(
            "Poll one SQS queue and POST /temperatures. "
            "Requires HOME_ID, SQS_QUEUE_URL, BACKEND_URL, and AWS_REGION. "
            "AWS_PROFILE is optional. The same program serves every home."
        ),
    )
    parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_adapter_config()
    _LOG.info(
        "home=%s region=%s profile=%s backend=%s timeout=%s",
        config.home_id,
        config.aws_region,
        config.aws_profile or "",
        config.backend_url,
        HTTP_TIMEOUT_SECONDS,
    )
    queue = BotoSqsQueue(
        build_sqs_client(config.aws_region, config.aws_profile),
        config.queue_url,
    )
    stopped = False

    def stop() -> bool:
        return stopped

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stopped
        stopped = True
        _LOG.info("home=%s outcome=stopping signal=%s", config.home_id, signum)

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)
    try:
        poll(queue, home_id=config.home_id, backend_url=config.backend_url, stop=stop)
    except KeyboardInterrupt:
        return 0
    return 0


def _event_id(decoded: Any) -> str:
    if isinstance(decoded, dict) and isinstance(decoded.get("event_id"), str):
        return decoded["event_id"]
    return ""

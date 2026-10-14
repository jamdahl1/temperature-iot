"""Isolated SNS/SQS root checks. Importing this module does not call AWS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from temperature_demo.config import repo_root

TOPIC_NAME = "temperature-readings"
HOME_A_QUEUE = "temperature-home-a"
HOME_B_QUEUE = "temperature-home-b"
HOME_A_DLQ = "temperature-home-a-dlq"
HOME_B_DLQ = "temperature-home-b-dlq"
AWS_PROFILE = "temperature-iot-demo"
AWS_REGION = "us-east-2"

DEMO_EVENT = {
    "event_id": "demo-001",
    "device_id": "thermostat-001",
    "temperature": 72.4,
    "unit": "F",
    "observed_at": "2026-10-14T14:00:00Z",
}

REQUIRED_OUTPUTS = (
    "topic_arn",
    "home_a_queue_url",
    "home_b_queue_url",
    "home_a_queue_arn",
    "home_b_queue_arn",
    "home_a_dlq_url",
    "home_b_dlq_url",
    "home_a_dlq_arn",
    "home_b_dlq_arn",
)

_SECRET_MARKERS = (
    "AKIA",
    "aws_secret_access_key",
    "aws_access_key_id",
    "BEGIN PRIVATE KEY",
)


def messaging_root() -> Path:
    return repo_root() / "infra" / "aws-messaging"


def demo_event_path() -> Path:
    return messaging_root() / "events" / "demo-001.json"


def assert_messaging_root() -> None:
    """The Terraform root declares one topic, two queues, and raw fan-out."""

    root = messaging_root()
    main = _read(root / "main.tf")
    variables = _read(root / "variables.tf")
    outputs = _read(root / "outputs.tf")
    versions = _read(root / "versions.tf")
    text = "\n".join((main, variables, outputs, versions))

    for name in (TOPIC_NAME, HOME_A_QUEUE, HOME_B_QUEUE, HOME_A_DLQ, HOME_B_DLQ):
        if f'"{name}"' not in text:
            raise AssertionError(f"{name} is not declared")
    if 'resource "aws_sns_topic"' not in main:
        raise AssertionError("SNS topic resource is missing")
    if main.count('resource "aws_sqs_queue"') < 2:
        raise AssertionError("expected a queue resource and a dead-letter resource")
    if 'resource "aws_sns_topic_subscription"' not in main:
        raise AssertionError("SNS subscription resource is missing")
    if 'resource "aws_sqs_queue_policy"' not in main:
        raise AssertionError("SQS queue policy resource is missing")
    if "for_each" not in main or "raw_message_delivery = true" not in main:
        raise AssertionError("both subscriptions must use raw message delivery")
    if "raw_message_delivery = false" in main:
        raise AssertionError("raw message delivery is disabled")
    if "aws:SourceArn" not in main or "sqs:SendMessage" not in main:
        raise AssertionError("queue policy must scope send to the topic ARN")
    if 'identifiers = ["*"]' in main or 'Principal = "*"' in text:
        raise AssertionError("queue policy allows a public principal")
    if f'"{AWS_REGION}"' not in variables:
        raise AssertionError("region default is not us-east-2")
    if f'"{AWS_PROFILE}"' not in variables:
        raise AssertionError("profile default is not temperature-iot-demo")
    for name in REQUIRED_OUTPUTS:
        if f'output "{name}"' not in outputs:
            raise AssertionError(f"output {name} is missing")
    if "hashicorp/aws" not in versions:
        raise AssertionError("AWS provider is not required")
    _assert_no_secret_material(root)


def assert_demo_event_file() -> None:
    payload = json.loads(demo_event_path().read_text(encoding="utf-8"))
    if payload != DEMO_EVENT:
        raise AssertionError(f"demo event drifted: {payload}")


def assert_raw_delivery(body: Any, expected: dict[str, Any] | None = None) -> None:
    """Accept the published JSON object. Reject an SNS notification envelope."""

    wanted = DEMO_EVENT if expected is None else expected
    if not isinstance(body, dict):
        raise AssertionError("message body is not a JSON object")
    if body.get("Type") == "Notification" or "TopicArn" in body:
        raise AssertionError("message is an SNS envelope; raw delivery is off")
    if body != wanted:
        raise AssertionError(f"message body is {body}")


def assert_topic_only_send(policy: Any, topic_arn: str) -> None:
    """The queue may receive from this topic and from nobody public."""

    if not isinstance(policy, dict):
        raise AssertionError("queue policy is not an object")
    statements = policy.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    if not isinstance(statements, list) or not statements:
        raise AssertionError("queue policy has no statements")

    matched = False
    for statement in statements:
        if not isinstance(statement, dict):
            raise AssertionError("queue policy statement is not an object")
        if _principal_is_public(statement.get("Principal")):
            raise AssertionError("queue policy allows a public principal")
        actions = statement.get("Action")
        if isinstance(actions, str):
            actions = [actions]
        if not isinstance(actions, list) or "sqs:SendMessage" not in actions:
            continue
        condition = statement.get("Condition") or {}
        if not isinstance(condition, dict):
            raise AssertionError("queue policy condition is not an object")
        arn_equals = condition.get("ArnEquals") or {}
        if not isinstance(arn_equals, dict):
            raise AssertionError("queue policy ArnEquals is not an object")
        source = arn_equals.get("aws:SourceArn")
        if isinstance(source, list):
            source_ok = topic_arn in source
        else:
            source_ok = source == topic_arn
        if source_ok and statement.get("Effect", "Allow") == "Allow":
            matched = True
    if not matched:
        raise AssertionError("queue policy does not allow this SNS topic to send")


def _principal_is_public(principal: Any) -> bool:
    if principal == "*":
        return True
    if not isinstance(principal, dict):
        return False
    for value in principal.values():
        if value == "*":
            return True
        if isinstance(value, list) and "*" in value:
            return True
    return False


def _assert_no_secret_material(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ".terraform" in path.parts:
            continue
        if path.suffix.lower() not in {".tf", ".json", ".md", ".py", ".hcl", ".example"}:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in _SECRET_MARKERS:
            if marker in text:
                raise AssertionError(f"{path.name} contains {marker}")


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing {path}")
    return path.read_text(encoding="utf-8")

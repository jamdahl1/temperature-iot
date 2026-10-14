"""Publish one temperature event and prove both queues receive it.

Importing this module does not read the environment or call AWS.
`python -m temperature_demo.aws_verify --help` stays local.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

from temperature_demo.config import repo_root
from temperature_demo.messaging_contract import (
    AWS_PROFILE,
    AWS_REGION,
    assert_raw_delivery,
    assert_topic_only_send,
    demo_event_path,
    messaging_root,
)
from temperature_demo.process import run


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="temperature-demo-aws-messaging",
        description=(
            "Publish events/demo-001.json to SNS and require the same JSON "
            "in temperature-home-a and temperature-home-b."
        ),
    )
    parser.add_argument(
        "--profile",
        default=AWS_PROFILE,
        help="AWS CLI profile (default: temperature-iot-demo).",
    )
    parser.add_argument(
        "--region",
        default=AWS_REGION,
        help="AWS region (default: us-east-2).",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=6,
        help="Long-poll attempts per queue.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    expected = json.loads(demo_event_path().read_text(encoding="utf-8"))
    topic_arn = _terraform_output("topic_arn")
    queues = {
        "home-a": _terraform_output("home_a_queue_url"),
        "home-b": _terraform_output("home_b_queue_url"),
    }

    published = _aws_json(
        [
            "sns",
            "publish",
            "--topic-arn",
            topic_arn,
            "--message",
            json.dumps(expected),
        ],
        profile=args.profile,
        region=args.region,
    )
    message_id = str(published.get("MessageId") or "")
    if not message_id:
        raise SystemExit("SNS publish did not return MessageId")
    print(f"sns_message_id: {message_id}", flush=True)

    for home, queue_url in queues.items():
        message, body = _receive_match(
            queue_url,
            event_id=str(expected["event_id"]),
            profile=args.profile,
            region=args.region,
            attempts=args.attempts,
        )
        assert_raw_delivery(body, expected)
        policy = _queue_policy(queue_url, profile=args.profile, region=args.region)
        assert_topic_only_send(policy, topic_arn)
        _aws_json(
            [
                "sqs",
                "delete-message",
                "--queue-url",
                queue_url,
                "--receipt-handle",
                str(message["ReceiptHandle"]),
            ],
            profile=args.profile,
            region=args.region,
            allow_empty=True,
        )
        print(
            f"{home}: matched event_id={expected['event_id']} raw=true deleted=true",
            flush=True,
        )

    print("passed", flush=True)
    return 0


def _receive_match(
    queue_url: str,
    *,
    event_id: str,
    profile: str,
    region: str,
    attempts: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    for _ in range(attempts):
        payload = _aws_json(
            [
                "sqs",
                "receive-message",
                "--queue-url",
                queue_url,
                "--max-number-of-messages",
                "1",
                "--wait-time-seconds",
                "10",
                "--visibility-timeout",
                "30",
            ],
            profile=profile,
            region=region,
            allow_empty=True,
        )
        messages = payload.get("Messages") if isinstance(payload, dict) else None
        if not messages:
            continue
        message = messages[0]
        body = json.loads(str(message["Body"]))
        if isinstance(body, dict) and body.get("event_id") == event_id:
            return message, body
        _aws_json(
            [
                "sqs",
                "change-message-visibility",
                "--queue-url",
                queue_url,
                "--receipt-handle",
                str(message["ReceiptHandle"]),
                "--visibility-timeout",
                "0",
            ],
            profile=profile,
            region=region,
            allow_empty=True,
        )
    raise SystemExit(f"{queue_url} did not return event_id {event_id}")


def _queue_policy(queue_url: str, *, profile: str, region: str) -> dict[str, Any]:
    payload = _aws_json(
        [
            "sqs",
            "get-queue-attributes",
            "--queue-url",
            queue_url,
            "--attribute-names",
            "Policy",
        ],
        profile=profile,
        region=region,
    )
    attributes = payload.get("Attributes") if isinstance(payload, dict) else None
    if not isinstance(attributes, dict) or "Policy" not in attributes:
        raise SystemExit(f"{queue_url} has no queue policy")
    policy = json.loads(str(attributes["Policy"]))
    if not isinstance(policy, dict):
        raise SystemExit(f"{queue_url} policy is not a JSON object")
    return policy


def _terraform_output(name: str) -> str:
    completed = run(
        ["terraform", f"-chdir={messaging_root().as_posix()}", "output", "-raw", name],
        cwd=repo_root(),
        capture=True,
    )
    value = (completed.stdout or "").strip()
    if not value:
        raise SystemExit(f"terraform output {name} was empty")
    return value


def _aws_json(
    args: list[str],
    *,
    profile: str,
    region: str,
    allow_empty: bool = False,
) -> dict[str, Any]:
    completed = run(
        ["aws", "--profile", profile, "--region", region, *args, "--output", "json"],
        cwd=repo_root(),
        capture=True,
    )
    text = (completed.stdout or "").strip()
    if not text:
        if allow_empty:
            return {}
        raise SystemExit(f"aws {' '.join(args[:2])} returned no JSON")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise SystemExit(f"aws {' '.join(args[:2])} returned {type(payload).__name__}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())

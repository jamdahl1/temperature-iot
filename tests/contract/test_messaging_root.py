"""The messaging root stays a private SNS fan-out. No AWS calls."""

from __future__ import annotations

import subprocess
import sys

from temperature_demo.config import repo_root
from temperature_demo.messaging_contract import (
    DEMO_EVENT,
    assert_demo_event_file,
    assert_messaging_root,
    assert_raw_delivery,
    assert_topic_only_send,
)


def test_messaging_root_declares_fanout() -> None:
    assert_messaging_root()
    assert_demo_event_file()


def test_raw_delivery_rejects_sns_envelope() -> None:
    assert_raw_delivery(dict(DEMO_EVENT))
    envelope = {
        "Type": "Notification",
        "TopicArn": "arn:aws:sns:us-west-2:123456789012:temperature-readings",
        "Message": '{"event_id":"demo-001"}',
    }
    try:
        assert_raw_delivery(envelope)
    except AssertionError as exc:
        if "SNS envelope" not in str(exc):
            raise
    else:
        raise AssertionError("SNS envelope was accepted")


def test_queue_policy_requires_the_topic_arn() -> None:
    topic = "arn:aws:sns:us-west-2:123456789012:temperature-readings"
    assert_topic_only_send(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "sns.amazonaws.com"},
                    "Action": "sqs:SendMessage",
                    "Resource": "arn:aws:sqs:us-west-2:123456789012:temperature-home-a",
                    "Condition": {"ArnEquals": {"aws:SourceArn": topic}},
                }
            ],
        },
        topic,
    )
    try:
        assert_topic_only_send(
            {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "sqs:SendMessage",
                        "Resource": "*",
                    }
                ]
            },
            topic,
        )
    except AssertionError as exc:
        if "public principal" not in str(exc):
            raise
    else:
        raise AssertionError("public queue policy was accepted")


def test_aws_verify_help_is_local() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "temperature_demo.aws_verify", "--help"],
        cwd=repo_root(),
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    if "temperature-iot-demo" not in completed.stdout:
        raise AssertionError("help text does not name the demo profile")


if __name__ == "__main__":
    test_messaging_root_declares_fanout()
    test_raw_delivery_rejects_sns_envelope()
    test_queue_policy_requires_the_topic_arn()
    test_aws_verify_help_is_local()
    print("passed")

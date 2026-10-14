"""Routing composition stays on shared modules and off the broadcast names."""

from __future__ import annotations

from temperature_demo.config import repo_root


def test_routing_root_composes_shared_modules() -> None:
    root = repo_root() / "infra" / "aws-messaging-routing"
    main = (root / "main.tf").read_text(encoding="utf-8")
    variables = (root / "variables.tf").read_text(encoding="utf-8")
    text = main + "\n" + variables
    for name in (
        "temperature-readings-routing",
        "temperature-routing-home-a",
        "temperature-routing-home-b",
        "temperature-routing-home-a-dlq",
        "temperature-routing-home-b-dlq",
    ):
        if f'"{name}"' not in text:
            raise AssertionError(f"{name} is not declared")
    if '"temperature-readings"' in variables or '"temperature-home-a"' in variables:
        raise AssertionError("routing variables reuse broadcast resource names")
    if 'resource "aws_sns_topic"' in main or 'resource "aws_sqs_queue"' in main:
        raise AssertionError("routing root defines SNS or SQS inline")
    for source in ("/sns\"", "/sqs\"", "/sns-sqs-binding\""):
        if source not in main:
            raise AssertionError(f"module source {source} is missing")
    if "module.queue[each.key].queue_arn" not in main:
        raise AssertionError("binding is not wired to the matching queue")
    if "house_id = [each.key]" not in main or "MessageBody" not in main:
        raise AssertionError("filter is not derived from the home key")
    if "raw_message_delivery" not in main or "true" not in main:
        raise AssertionError("raw message delivery is not enabled")


def test_binding_module_scopes_send_to_the_topic() -> None:
    binding = (
        repo_root().parents[2]
        / "10_Infrastructure"
        / "01_Terraform"
        / "terraform-modules"
        / "modules"
        / "aws"
        / "messaging"
        / "sns-sqs-binding"
        / "main.tf"
    )
    if not binding.is_file():
        raise AssertionError(f"missing {binding}")
    text = binding.read_text(encoding="utf-8")
    for needle in ("sqs:SendMessage", "aws:SourceArn", "sns.amazonaws.com", "var.topic_arn"):
        if needle not in text:
            raise AssertionError(f"binding policy is missing {needle}")
    if 'identifiers = ["*"]' in text:
        raise AssertionError("binding policy allows a public principal")


def test_broadcast_root_was_not_moved_onto_modules() -> None:
    main = (repo_root() / "infra" / "aws-messaging" / "main.tf").read_text(encoding="utf-8")
    if 'resource "aws_sns_topic"' not in main:
        raise AssertionError("broadcast topic resource was removed")
    if "module \"topic\"" in main:
        raise AssertionError("broadcast root now calls the shared topic module")


if __name__ == "__main__":
    test_routing_root_composes_shared_modules()
    test_binding_module_scopes_send_to_the_topic()
    test_broadcast_root_was_not_moved_onto_modules()
    print("passed")

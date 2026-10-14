"""Map a queue event onto TemperatureReading. No HTTP and no AWS."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from temperature_demo.sqs_adapter.contracts import EventRejected

SUPPORTED_UNITS = frozenset({"F", "C"})


def reading_from_event(event: Any, home_id: str) -> dict[str, Any]:
    """Build the backend body. HOME_ID supplies house_id.

    A missing house_id is filled from HOME_ID. A present house_id must match it.
    """

    if not isinstance(event, dict):
        raise EventRejected("invalid_event", "temperature event must be an object")
    if event.get("Type") == "Notification" or "TopicArn" in event:
        raise EventRejected("unexpected_message", "message is an SNS envelope")

    _identifier(event.get("event_id"), "event_id")
    configured = _identifier(home_id, "HOME_ID")
    if "house_id" in event:
        presented = _identifier(event.get("house_id"), "house_id")
        if presented != configured:
            raise EventRejected(
                "house_mismatch",
                f"event house_id {presented} does not match HOME_ID {configured}",
            )
    return {
        "house_id": configured,
        "sensor_id": _identifier(event.get("device_id"), "device_id"),
        "temperature": _temperature(event.get("temperature")),
        "unit": _unit(event.get("unit")),
        "observed_at": _observed_at(event.get("observed_at")),
    }


def _identifier(value: Any, field: str) -> str:
    if value is None or value == "":
        raise EventRejected("missing_field", f"missing required field: {field}")
    if not isinstance(value, str):
        raise EventRejected("invalid_identifier", f"{field} must be a string")
    text = value.strip()
    if not text:
        raise EventRejected("missing_field", f"missing required field: {field}")
    return text


def _temperature(value: Any) -> float:
    if value is None or value == "":
        raise EventRejected("missing_field", "missing required field: temperature")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventRejected("invalid_temperature", "temperature must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise EventRejected("invalid_temperature", "temperature must be a finite number")
    return number


def _unit(value: Any) -> str:
    if value is None or value == "":
        raise EventRejected("missing_field", "missing required field: unit")
    if not isinstance(value, str) or value not in SUPPORTED_UNITS:
        raise EventRejected("unsupported_unit", f"unsupported unit: {value}")
    return value


def _observed_at(value: Any) -> str:
    if value is None or value == "":
        raise EventRejected("missing_field", "missing required field: observed_at")
    if not isinstance(value, str):
        raise EventRejected("invalid_observed_at", "observed_at must be an ISO-8601 timestamp")
    text = value.strip()
    parsed_text = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(parsed_text)
    except ValueError as exc:
        raise EventRejected(
            "invalid_observed_at",
            "observed_at must be an ISO-8601 timestamp",
        ) from exc
    if parsed.tzinfo is None:
        raise EventRejected("invalid_observed_at", "observed_at must include a timezone")
    return text

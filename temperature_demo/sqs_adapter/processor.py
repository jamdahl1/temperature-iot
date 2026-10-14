"""Validate, transform, and deliver one event. This module does not call AWS."""

from __future__ import annotations

from typing import Any, Callable

from temperature_demo.sqs_adapter.contracts import DeliveryFailed
from temperature_demo.sqs_adapter.delivery import HTTP_TIMEOUT_SECONDS, post_reading
from temperature_demo.sqs_adapter.transform import reading_from_event

Poster = Callable[..., dict[str, Any]]


def process_message(
    message: dict[str, Any],
    home_id: str,
    backend_url: str,
    *,
    post: Poster = post_reading,
) -> None:
    """Deliver one event. Return only after the backend accepts that home's reading."""

    reading = reading_from_event(message, home_id)
    stored = post(backend_url, reading, timeout=HTTP_TIMEOUT_SECONDS)
    if not isinstance(stored, dict):
        raise DeliveryFailed("backend response is not an object")
    if stored.get("house_id") != reading["house_id"]:
        raise DeliveryFailed(
            f"backend stored house_id {stored.get('house_id')!r} for {reading['house_id']}"
        )

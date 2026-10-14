"""Errors for the SQS adapter. Importing this module has no side effects."""

from __future__ import annotations


class AdapterConfigError(Exception):
    """Adapter environment is missing or malformed."""


class EventRejected(Exception):
    """A queue event cannot be turned into a temperature reading."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DeliveryFailed(Exception):
    """The backend did not accept the reading."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status

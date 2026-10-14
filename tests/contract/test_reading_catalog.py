"""The two homes stay distinct before any container starts."""

from __future__ import annotations

from temperature_demo.contracts import assert_backend_not_vendored, assert_reading_catalog


def test_reading_catalog() -> None:
    assert_reading_catalog()


def test_backend_source_is_not_vendored() -> None:
    assert_backend_not_vendored()


if __name__ == "__main__":
    test_reading_catalog()
    test_backend_source_is_not_vendored()
    print("passed")

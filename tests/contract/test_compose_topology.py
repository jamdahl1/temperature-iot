"""Compose must keep one image and two databases on two networks."""

from __future__ import annotations

from temperature_demo.contracts import assert_compose_topology


def test_compose_uses_one_image_and_two_databases() -> None:
    assert_compose_topology()


if __name__ == "__main__":
    test_compose_uses_one_image_and_two_databases()
    print("passed")

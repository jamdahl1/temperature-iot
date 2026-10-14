"""Home A stays in PostgreSQL A. Home B stays in PostgreSQL B."""

from __future__ import annotations

from temperature_demo.isolation import ProofFailed, prove_database_isolation, prove_same_image_and_config


def test_home_readings_stay_in_their_own_database() -> None:
    print(prove_same_image_and_config(), end="")
    print(prove_database_isolation(), end="")


if __name__ == "__main__":
    try:
        test_home_readings_stay_in_their_own_database()
    except ProofFailed as exc:
        print(exc)
        raise SystemExit(1) from exc
    print("passed")

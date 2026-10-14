"""Docker network DNS matches the configured database path."""

from __future__ import annotations

from temperature_demo.isolation import ProofFailed, prove_dns


def test_backend_resolves_only_its_own_postgres() -> None:
    print(prove_dns(), end="")


if __name__ == "__main__":
    try:
        test_backend_resolves_only_its_own_postgres()
    except ProofFailed as exc:
        print(exc)
        raise SystemExit(1) from exc
    print("passed")

"""Command line for the local system demo.

`--help` does not build an image, start containers, or read DATABASE_*.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from temperature_demo.build_image import build_image, image_exists
from temperature_demo.compose_ctl import clean, status_text, stop, up
from temperature_demo.config import DB_PASSWORD, PARTITIONS, repo_root
from temperature_demo.contracts import (
    assert_backend_not_vendored,
    assert_compose_topology,
    assert_reading_catalog,
)
from temperature_demo.isolation import (
    prove_database_isolation,
    prove_dns,
    prove_same_image_and_config,
    seed,
)
from temperature_demo.process import CommandFailed, run


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="temperature-demo",
        description="Compose two local Temperature IoT backends and prove database isolation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Build the image if needed and start both homes.")
    start_parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Build the backend image again from the external checkouts.",
    )
    subparsers.add_parser("stop", help="Stop containers. Volumes stay.")
    subparsers.add_parser("status", help="Show containers and Docker networks.")
    subparsers.add_parser("seed", help="Store the deterministic Home A and Home B readings.")
    subparsers.add_parser(
        "verify",
        help="Prove configuration, database isolation, and Docker DNS isolation.",
    )
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove containers, networks, and database volumes.",
    )
    clean_parser.add_argument(
        "--images",
        action="store_true",
        help="Also remove the local temperature-iot-backend:demo image.",
    )
    subparsers.add_parser(
        "contracts",
        help="Check the reading catalog and compose file without starting containers.",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "start":
            _start(rebuild=args.rebuild)
        elif args.command == "stop":
            stop()
        elif args.command == "status":
            print(status_text(), end="")
            print(_network_summary(), end="")
        elif args.command == "seed":
            print(seed(), end="")
        elif args.command == "verify":
            print(_verify(), end="")
        elif args.command == "clean":
            clean(remove_image=args.images)
        elif args.command == "contracts":
            assert_reading_catalog()
            assert_backend_not_vendored()
            assert_compose_topology()
            print("contracts: passed")
        else:
            parser.error(f"unknown command: {args.command}")
    except (CommandFailed, AssertionError) as exc:
        print(exc)
        return 1
    return 0


def _start(*, rebuild: bool) -> None:
    if rebuild or not image_exists():
        build_image()
    else:
        print("image temperature-iot-backend:demo already present", flush=True)
    up()
    print(status_text(), end="")
    for partition in PARTITIONS:
        print(f"{partition.ref} {partition.base_url}")


def _verify() -> str:
    parts = ["reading catalog: passed", "backend source was not copied into this repo"]
    assert_reading_catalog()
    assert_backend_not_vendored()
    assert_compose_topology()
    parts.append("compose topology: passed")
    parts.append(prove_same_image_and_config().rstrip())
    parts.append(prove_database_isolation().rstrip())
    parts.append(prove_dns().rstrip())
    rendered = _redact("\n\n".join(parts).rstrip() + "\n")
    destination = repo_root() / "evidence" / "runs" / "stage-3-isolation.txt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return rendered + f"\nwrote {destination}\n"


def _network_summary() -> str:
    lines = []
    for partition in PARTITIONS:
        completed = run(
            [
                "docker",
                "network",
                "inspect",
                partition.network_name,
                "--format",
                "{{range .Containers}}{{.Name}} {{end}}",
            ],
            check=False,
            capture=True,
        )
        if completed.returncode != 0:
            lines.append(f"{partition.network_name}: absent")
        else:
            names = completed.stdout.strip() or "(empty)"
            lines.append(f"{partition.network_name}: {names}")
    return "\n".join(lines) + "\n"


def _redact(text: str) -> str:
    return text.replace(DB_PASSWORD, "***")


def evidence_path() -> Path:
    return repo_root() / "evidence" / "runs" / "stage-3-isolation.txt"


if __name__ == "__main__":
    raise SystemExit(main())

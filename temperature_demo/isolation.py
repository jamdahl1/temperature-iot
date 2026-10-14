"""Persistence and DNS proofs for the two local homes."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from temperature_demo.config import (
    DB_PASSWORD,
    DB_USER,
    IMAGE,
    PARTITIONS,
    Partition,
)
from temperature_demo.process import CommandFailed, run


class ProofFailed(AssertionError):
    """A system proof did not hold."""


@dataclass(frozen=True)
class StoredRow:
    house_id: str
    sensor_id: str
    temperature: float
    unit: str
    observed_at: str


def seed() -> str:
    lines = []
    for partition in PARTITIONS:
        lines.append(_ensure_reading(partition))
    return "\n".join(lines) + "\n"


def prove_database_isolation() -> str:
    """POST when needed, then require each reading to exist in one database."""

    seed_report = seed().rstrip()
    blocks = [seed_report, ""]
    rows_by_ref: dict[str, list[StoredRow]] = {}
    for partition in PARTITIONS:
        rows = query_rows(partition)
        rows_by_ref[partition.ref] = rows
        blocks.append(f"database {partition.database_name} ({partition.postgres_container})")
        if rows:
            for row in rows:
                blocks.append(
                    "  "
                    f"{row.house_id} {row.sensor_id} {row.temperature} {row.unit} {row.observed_at}"
                )
        else:
            blocks.append("  (no rows)")
        blocks.append("")

    for partition in PARTITIONS:
        own = rows_by_ref[partition.ref]
        other = rows_by_ref[_other(partition).ref]
        if not _contains(own, partition):
            raise ProofFailed(
                f"{partition.database_name} does not contain the {partition.ref} reading"
            )
        if _contains(other, partition):
            raise ProofFailed(
                f"{_other(partition).database_name} contains the {partition.ref} reading"
            )
    blocks.append("persistence isolation: passed")
    return "\n".join(blocks).rstrip() + "\n"


def prove_dns() -> str:
    lines = ["dns"]
    for partition in PARTITIONS:
        other = _other(partition)
        _expect_resolve(partition.backend_container, partition.database_host, True)
        _expect_resolve(partition.backend_container, other.database_host, False)
        lines.append(
            f"  {partition.backend_container} resolves {partition.database_host}"
        )
        lines.append(
            f"  {partition.backend_container} does not resolve {other.database_host}"
        )
    lines.append("docker dns isolation: passed")
    return "\n".join(lines) + "\n"


def prove_same_image_and_config() -> str:
    lines = ["runtime configuration"]
    image_ids: list[str] = []
    for partition in PARTITIONS:
        image_id = _inspect(partition.backend_container, "{{.Image}}").strip()
        image_ids.append(image_id)
        host = _env(partition.backend_container, "DATABASE_HOST")
        name = _env(partition.backend_container, "DATABASE_NAME")
        password = _env(partition.backend_container, "DATABASE_PASSWORD")
        if host != partition.database_host or name != partition.database_name:
            raise ProofFailed(
                f"{partition.backend_container} configuration is "
                f"DATABASE_HOST={host} DATABASE_NAME={name}"
            )
        if password != DB_PASSWORD:
            raise ProofFailed(
                f"{partition.backend_container} database password does not match the demo"
            )
        networks = _network_names(partition.backend_container)
        if networks != {partition.network_name}:
            raise ProofFailed(
                f"{partition.backend_container} networks are {sorted(networks)}"
            )
        lines.append(
            f"  {partition.backend_container} image={image_id} "
            f"DATABASE_HOST={host} DATABASE_NAME={name} network={partition.network_name}"
        )
    if len(set(image_ids)) != 1:
        raise ProofFailed(f"backend image ids differ: {image_ids}")
    lines.append(f"  shared image tag: {IMAGE}")
    lines.append("same image and configuration isolation: passed")
    return "\n".join(lines) + "\n"


def query_rows(partition: Partition) -> list[StoredRow]:
    sql = """
    SELECT house_id,
           sensor_id,
           temperature::text,
           unit,
           to_char(observed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
    FROM temperature_reading
    ORDER BY house_id, sensor_id, observed_at, id
    """
    completed = run(
        [
            "docker",
            "exec",
            partition.postgres_container,
            "psql",
            "-U",
            DB_USER,
            "-d",
            partition.database_name,
            "-v",
            "ON_ERROR_STOP=1",
            "-A",
            "-F",
            "|",
            "-t",
            "-c",
            sql,
        ],
        capture=True,
    )
    rows: list[StoredRow] = []
    for line in completed.stdout.splitlines():
        text = line.strip()
        if not text:
            continue
        house_id, sensor_id, temperature, unit, observed_at = text.split("|")
        rows.append(
            StoredRow(
                house_id=house_id,
                sensor_id=sensor_id,
                temperature=float(temperature),
                unit=unit,
                observed_at=observed_at,
            )
        )
    return rows


def _ensure_reading(partition: Partition) -> str:
    if _contains(query_rows(partition), partition):
        return f"seed {partition.ref}: already stored"
    payload = json.dumps(partition.reading()).encode("utf-8")
    request = urllib.request.Request(
        partition.base_url + "/temperatures",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ProofFailed(f"POST {partition.base_url} failed: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise ProofFailed(
            f"POST {partition.base_url} failed: {exc.reason}. Start the demo first."
        ) from exc
    if status != 200:
        raise ProofFailed(f"POST {partition.base_url} returned {status}: {body}")
    stored = json.loads(body)
    if stored.get("house_id") != partition.house_id:
        raise ProofFailed(f"POST {partition.ref} returned an unexpected house_id")
    return f"seed {partition.ref}: stored id={stored.get('id')}"


def _contains(rows: list[StoredRow], partition: Partition) -> bool:
    for row in rows:
        if (
            row.house_id == partition.house_id
            and row.sensor_id == partition.sensor_id
            and row.unit == partition.unit
            and row.observed_at == partition.observed_at
            and abs(row.temperature - partition.temperature) < 0.001
        ):
            return True
    return False


def _other(partition: Partition) -> Partition:
    for candidate in PARTITIONS:
        if candidate.ref != partition.ref:
            return candidate
    raise ProofFailed("a second partition is required")


def _expect_resolve(container: str, host: str, should_resolve: bool) -> None:
    script = (
        "import socket, sys\n"
        "host = sys.argv[1]\n"
        "try:\n"
        "    socket.getaddrinfo(host, 5432)\n"
        "except socket.gaierror:\n"
        "    raise SystemExit(2)\n"
        "raise SystemExit(0)\n"
    )
    try:
        completed = run(
            ["docker", "exec", container, "python", "-c", script, host],
            check=False,
            capture=True,
        )
    except CommandFailed as exc:
        raise ProofFailed(str(exc)) from exc
    if completed.returncode not in (0, 2):
        detail = (completed.stderr or completed.stdout or "").strip()
        raise ProofFailed(f"{container} dns check for {host} failed: {detail}")
    resolved = completed.returncode == 0
    if resolved != should_resolve:
        state = "resolved" if resolved else "did not resolve"
        raise ProofFailed(f"{container} {state} {host}")


def _inspect(container: str, template: str) -> str:
    completed = run(
        ["docker", "inspect", "-f", template, container],
        capture=True,
    )
    return completed.stdout


def _env(container: str, name: str) -> str:
    script = (
        "import os, sys\n"
        "value = os.environ.get(sys.argv[1], '')\n"
        "sys.stdout.write(value)\n"
    )
    completed = run(
        ["docker", "exec", container, "python", "-c", script, name],
        capture=True,
    )
    return completed.stdout


def _network_names(container: str) -> set[str]:
    completed = run(
        ["docker", "inspect", "-f", "{{json .NetworkSettings.Networks}}", container],
        capture=True,
    )
    payload = json.loads(completed.stdout)
    return set(payload)

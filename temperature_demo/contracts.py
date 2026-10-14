"""Topology contracts. Importing this module does not start containers."""

from __future__ import annotations

from typing import Any

from temperature_demo.compose_ctl import compose_config, env_map
from temperature_demo.config import (
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    IMAGE,
    PARTITIONS,
    POSTGRES_IMAGE,
    READING_FIELDS,
    Partition,
    repo_root,
)


def assert_reading_catalog() -> None:
    refs = [item.ref for item in PARTITIONS]
    if refs != ["home-a", "home-b"]:
        raise AssertionError(f"partition order is {refs}")
    hosts = {item.database_host for item in PARTITIONS}
    names = {item.database_name for item in PARTITIONS}
    ports = {item.http_port for item in PARTITIONS}
    if len(hosts) != len(PARTITIONS) or len(names) != len(PARTITIONS):
        raise AssertionError("database host and name must differ per partition")
    if len(ports) != len(PARTITIONS):
        raise AssertionError("http ports must differ per partition")
    for partition in PARTITIONS:
        reading = partition.reading()
        missing = [field for field in READING_FIELDS if field not in reading]
        if missing:
            raise AssertionError(f"{partition.ref} reading is missing {missing}")
        if reading["unit"] not in {"F", "C"}:
            raise AssertionError(f"{partition.ref} unit is not F or C")
        if reading["house_id"] != partition.ref:
            raise AssertionError(
                f"{partition.ref} house_id is data and is set to the partition "
                "only in this slice"
            )
        if not str(reading["sensor_id"]).strip():
            raise AssertionError(f"{partition.ref} sensor_id is blank")
        if not str(reading["observed_at"]).endswith("Z"):
            raise AssertionError(f"{partition.ref} observed_at must be UTC")
    home_a, home_b = PARTITIONS
    if home_a.temperature != 72.4 or home_a.unit != "F" or home_a.sensor_id != "living-room":
        raise AssertionError("home-a deterministic reading drifted")
    if home_b.temperature != 20.5 or home_b.unit != "C" or home_b.sensor_id != "kitchen":
        raise AssertionError("home-b deterministic reading drifted")


def assert_backend_not_vendored() -> None:
    vendored = repo_root() / "src" / "temperature_iot_backend"
    if vendored.exists():
        raise AssertionError("backend package was copied into this repo")


def assert_compose_topology() -> None:
    document = compose_config()
    services = document.get("services") or {}
    for partition in PARTITIONS:
        backend_key = f"backend-{partition.ref.removeprefix('home-')}"
        postgres_key = f"postgres-{partition.ref.removeprefix('home-')}"
        backend = services.get(backend_key)
        postgres = services.get(postgres_key)
        if backend is None or postgres is None:
            raise AssertionError(
                f"compose is missing {backend_key} or {postgres_key}; "
                f"services={sorted(services)}"
            )
        _assert_backend(partition, backend_key, backend)
        _assert_postgres(partition, postgres_key, postgres)


def _assert_backend(partition: Partition, key: str, service: dict[str, Any]) -> None:
    if service.get("image") != IMAGE:
        raise AssertionError(f"{key} image is {service.get('image')}")
    env = env_map(service)
    expected = {
        "DATABASE_HOST": partition.database_host,
        "DATABASE_PORT": DB_PORT,
        "DATABASE_NAME": partition.database_name,
        "DATABASE_USER": DB_USER,
        "DATABASE_PASSWORD": DB_PASSWORD,
    }
    for name, value in expected.items():
        if env.get(name) != value:
            shown = name if name != "DATABASE_PASSWORD" else "DATABASE_PASSWORD"
            raise AssertionError(f"{key} {shown} does not match the partition contract")
    networks = _network_keys(service)
    if networks != {"home-" + partition.ref.removeprefix("home-")}:
        raise AssertionError(f"{key} networks are {sorted(networks)}")
    published = _published(service)
    expected_port = ( "127.0.0.1", str(partition.http_port), "8000" )
    if expected_port not in published:
        raise AssertionError(f"{key} ports are {published}")


def _assert_postgres(partition: Partition, key: str, service: dict[str, Any]) -> None:
    if service.get("image") != POSTGRES_IMAGE:
        raise AssertionError(f"{key} image is {service.get('image')}")
    env = env_map(service)
    if env.get("POSTGRES_DB") != partition.database_name:
        raise AssertionError(f"{key} POSTGRES_DB does not match the partition")
    if env.get("POSTGRES_USER") != DB_USER:
        raise AssertionError(f"{key} POSTGRES_USER does not match the demo")
    if env.get("POSTGRES_PASSWORD") != DB_PASSWORD:
        raise AssertionError(f"{key} POSTGRES_PASSWORD does not match the demo")
    if _published(service):
        raise AssertionError(f"{key} publishes a host port")
    networks = _network_keys(service)
    if networks != {"home-" + partition.ref.removeprefix("home-")}:
        raise AssertionError(f"{key} networks are {sorted(networks)}")


def _network_keys(service: dict[str, Any]) -> set[str]:
    raw = service.get("networks") or {}
    if isinstance(raw, dict):
        return set(map(str, raw))
    return {str(item) for item in raw}


def _published(service: dict[str, Any]) -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for item in service.get("ports") or []:
        if isinstance(item, str):
            found.add(("", item, ""))
            continue
        if not isinstance(item, dict):
            continue
        host_ip = str(item.get("host_ip") or "")
        published = str(item.get("published") or "")
        target = str(item.get("target") or "")
        found.add((host_ip, published, target))
    return found

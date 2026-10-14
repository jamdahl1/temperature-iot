"""Disposable local topology.

Importing this module does not read the environment, open a socket,
or touch the filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


IMAGE = "temperature-iot-backend:demo"
POSTGRES_IMAGE = "postgres:16"
DB_USER = "temperature"
DB_PASSWORD = "local-demo-pw"
DB_PORT = "5432"
PROJECT_NAME = "temperature-demo"
COMPOSE_FILE = "docker/compose.yml"
DOCKERFILE = "docker/backend.Dockerfile"

BACKEND_ENV = "TEMPERATURE_IOT_BACKEND"
COMMONS_ENV = "COMMONS_REPO"
DEFAULT_BACKEND_RELATIVE = "../../21_PythonProjects/temperature-iot-backend"
DEFAULT_COMMONS_RELATIVE = "../../06_Common"


@dataclass(frozen=True)
class Partition:
    """One deployed copy of the logical backend and database."""

    ref: str
    http_port: int
    database_name: str
    database_host: str
    postgres_container: str
    backend_container: str
    network_name: str
    house_id: str
    sensor_id: str
    temperature: float
    unit: str
    observed_at: str

    def reading(self) -> dict[str, object]:
        return {
            "house_id": self.house_id,
            "sensor_id": self.sensor_id,
            "temperature": self.temperature,
            "unit": self.unit,
            "observed_at": self.observed_at,
        }

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.http_port}"


HOME_A = Partition(
    ref="home-a",
    http_port=18081,
    database_name="temperature_a",
    database_host="postgres-a",
    postgres_container="temperature-demo-postgres-a",
    backend_container="temperature-demo-backend-a",
    network_name="temperature-demo-home-a",
    house_id="home-a",
    sensor_id="living-room",
    temperature=72.4,
    unit="F",
    observed_at="2026-10-11T16:00:00Z",
)

HOME_B = Partition(
    ref="home-b",
    http_port=18082,
    database_name="temperature_b",
    database_host="postgres-b",
    postgres_container="temperature-demo-postgres-b",
    backend_container="temperature-demo-backend-b",
    network_name="temperature-demo-home-b",
    house_id="home-b",
    sensor_id="kitchen",
    temperature=20.5,
    unit="C",
    observed_at="2026-10-11T16:00:00Z",
)

PARTITIONS = (HOME_A, HOME_B)

READING_FIELDS = (
    "house_id",
    "sensor_id",
    "temperature",
    "unit",
    "observed_at",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

"""Docker Compose operations for the local demo."""

from __future__ import annotations

import json
from typing import Any

from temperature_demo.config import COMPOSE_FILE, DB_PASSWORD, repo_root
from temperature_demo.process import run


def compose_command(*args: str) -> list[str]:
    root = repo_root()
    return [
        "docker",
        "compose",
        "-f",
        str(root / COMPOSE_FILE),
        "--project-directory",
        str(root),
        *args,
    ]


def compose_config() -> dict[str, Any]:
    completed = run(compose_command("config", "--format", "json"), capture=True)
    return json.loads(completed.stdout)


def up() -> None:
    run(compose_command("up", "-d", "--wait", "--no-build"))


def stop() -> None:
    run(compose_command("stop"))


def clean(*, remove_image: bool) -> None:
    run(compose_command("down", "-v", "--remove-orphans"))
    if remove_image:
        run(["docker", "image", "rm", "temperature-iot-backend:demo"], check=False)


def status_text() -> str:
    completed = run(compose_command("ps", "-a"), capture=True)
    rendered = _redact(completed.stdout)
    if completed.stderr:
        rendered += _redact(completed.stderr)
    return rendered.rstrip() + "\n"


def env_map(service: dict[str, Any]) -> dict[str, str]:
    raw = service.get("environment") or {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    mapped: dict[str, str] = {}
    for item in raw:
        text = str(item)
        key, value = text.split("=", 1)
        mapped[key] = value
    return mapped


def _redact(text: str) -> str:
    return text.replace(DB_PASSWORD, "***")

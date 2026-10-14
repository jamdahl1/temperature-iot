"""Build the demo image from external checkouts.

Staged files live under the system temp directory, not in this repo.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from temperature_demo.config import (
    BACKEND_ENV,
    COMMONS_ENV,
    DEFAULT_BACKEND_RELATIVE,
    DEFAULT_COMMONS_RELATIVE,
    DOCKERFILE,
    IMAGE,
    repo_root,
)
from temperature_demo.process import run

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info")
_STAGE_NAME = "temperature-iot-system-demo-build"


def image_exists() -> bool:
    completed = run(
        ["docker", "image", "inspect", IMAGE],
        check=False,
        capture=True,
    )
    return completed.returncode == 0


def build_image() -> None:
    root = repo_root()
    backend = _resolve_checkout(BACKEND_ENV, root / DEFAULT_BACKEND_RELATIVE)
    commons = _resolve_checkout(COMMONS_ENV, root / DEFAULT_COMMONS_RELATIVE)
    _require(backend / "pyproject.toml")
    _require(backend / "src" / "temperature_iot_backend")
    _require(commons / "compute-manager" / "pyproject.toml")
    _require(commons / "uapi-adapter" / "pyproject.toml")

    stage_root = Path(tempfile.gettempdir()) / _STAGE_NAME
    if stage_root.exists():
        shutil.rmtree(stage_root)
    backend_stage = stage_root / "backend"
    commons_stage = stage_root / "commons"
    _copy_inputs(
        backend,
        backend_stage,
        ("pyproject.toml", "README.md", "src/temperature_iot_backend"),
    )
    _copy_inputs(
        commons / "compute-manager",
        commons_stage / "compute-manager",
        ("pyproject.toml", "README.md", "src/compute_manager"),
    )
    _copy_inputs(
        commons / "uapi-adapter",
        commons_stage / "uapi-adapter",
        ("pyproject.toml", "README.md", "src/universal_adapter_api"),
    )
    if any(backend_stage.rglob(".venv")) or any(commons_stage.rglob(".venv")):
        raise RuntimeError("staged build context contains a virtualenv")

    print(f"backend checkout: {backend}", flush=True)
    print(f"commons checkout: {commons}", flush=True)
    run(
        [
            "docker",
            "build",
            "--build-context",
            f"backend={backend_stage.as_posix()}",
            "--build-context",
            f"commons={commons_stage.as_posix()}",
            "-f",
            str(root / DOCKERFILE),
            "-t",
            IMAGE,
            str(root / "docker"),
        ],
        cwd=root,
    )


def _resolve_checkout(env_name: str, default: Path) -> Path:
    override = os.environ.get(env_name, "").strip()
    path = Path(override) if override else default
    return path.resolve()


def _require(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"missing build input: {path}")


def _copy_inputs(source_root: Path, dest_root: Path, parts: tuple[str, ...]) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    for part in parts:
        source = source_root / part
        if not source.exists():
            if part == "README.md":
                continue
            raise SystemExit(f"missing build input: {source}")
        target = dest_root / part
        if source.is_dir():
            shutil.copytree(source, target, ignore=_IGNORE)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

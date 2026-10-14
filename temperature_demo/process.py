"""Subprocess helper. Commands run only when a caller asks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from temperature_demo.config import DB_PASSWORD


class CommandFailed(RuntimeError):
    """A local command exited non-zero."""

    def __init__(self, args: list[str], returncode: int, detail: str) -> None:
        self.args_list = args
        self.returncode = returncode
        self.detail = detail
        rendered = _redact(" ".join(args))
        super().__init__(f"command failed ({returncode}): {rendered}\n{_redact(detail)}".rstrip())


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("+ " + _redact(" ".join(args)), flush=True)
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        text=True,
        capture_output=capture,
    )
    if check and completed.returncode != 0:
        detail = ""
        if capture:
            detail = (completed.stdout or "") + (completed.stderr or "")
        raise CommandFailed(args, completed.returncode, detail)
    return completed


def _redact(text: str) -> str:
    return text.replace(DB_PASSWORD, "***")

"""Adapter settings. The environment is read only when a caller asks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from temperature_demo.sqs_adapter.contracts import AdapterConfigError

REQUIRED_VARIABLES = (
    "HOME_ID",
    "SQS_QUEUE_URL",
    "BACKEND_URL",
    "AWS_REGION",
)


@dataclass(frozen=True)
class AdapterConfig:
    """One running consumer. Home identity comes only from HOME_ID."""

    home_id: str
    queue_url: str
    backend_url: str
    aws_region: str
    aws_profile: str | None


def load_adapter_config(
    environ: Mapping[str, str] | None = None,
) -> AdapterConfig:
    """Load consumer settings from environ, or from the process environment."""

    source = os.environ if environ is None else environ
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in REQUIRED_VARIABLES:
        raw = source.get(name, "")
        text = raw.strip() if isinstance(raw, str) else ""
        if not text:
            missing.append(name)
        else:
            values[name] = text
    if missing:
        raise AdapterConfigError("missing adapter configuration: " + ", ".join(missing))

    profile_raw = source.get("AWS_PROFILE", "")
    profile = profile_raw.strip() if isinstance(profile_raw, str) else ""
    backend_url = values["BACKEND_URL"].rstrip("/")
    queue_url = values["SQS_QUEUE_URL"]
    if not backend_url.startswith(("http://", "https://")):
        raise AdapterConfigError("BACKEND_URL must be an http or https URL")
    if not queue_url.startswith(("http://", "https://")):
        raise AdapterConfigError("SQS_QUEUE_URL must be an http or https URL")

    return AdapterConfig(
        home_id=values["HOME_ID"],
        queue_url=queue_url,
        backend_url=backend_url,
        aws_region=values["AWS_REGION"],
        aws_profile=profile or None,
    )

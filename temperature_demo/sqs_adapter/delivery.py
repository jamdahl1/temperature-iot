"""POST a temperature reading. Importing this module does not open a socket."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from temperature_demo.sqs_adapter.contracts import DeliveryFailed

HTTP_TIMEOUT_SECONDS = 10.0


def post_reading(
    backend_url: str,
    payload: dict[str, Any],
    *,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST /temperatures. Raise DeliveryFailed unless the response is successful."""

    base = backend_url.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise DeliveryFailed("BACKEND_URL must be an http or https URL")
    url = base + "/temperatures"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise DeliveryFailed(f"POST {url} failed: {exc.code} {detail}", status=exc.code) from exc
    except urllib.error.URLError as exc:
        raise DeliveryFailed(f"POST {url} failed: {exc.reason}") from exc
    if status < 200 or status >= 300:
        raise DeliveryFailed(f"POST {url} returned {status}", status=status)
    if not raw.strip():
        raise DeliveryFailed(f"POST {url} returned an empty body", status=status)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DeliveryFailed(f"POST {url} returned non-JSON", status=status) from exc
    if not isinstance(parsed, dict):
        raise DeliveryFailed(f"POST {url} returned {type(parsed).__name__}", status=status)
    return parsed

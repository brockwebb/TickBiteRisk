from __future__ import annotations

import os
from collections.abc import Mapping


class NoaaTokenMissingError(RuntimeError):
    """Raised when the NOAA CDO API token is unavailable."""


def get_noaa_token(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    token = source.get("NOAA_TOKEN", "").strip()
    if not token:
        raise NoaaTokenMissingError("NOAA_TOKEN is required for NOAA CDO validation")
    return token

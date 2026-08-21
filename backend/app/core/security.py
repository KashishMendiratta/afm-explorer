"""Optional API-key gate for write endpoints. See Settings.api_key's
docstring in app/core/config.py for the on/off behavior — disabled by
default (matching pre-auth behavior), opt-in via the AFM_API_KEY env var.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.api_key is None:
        return  # auth disabled — default, unauthenticated dev/demo mode
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key header")

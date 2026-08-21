from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration, overridable via environment variables (see
    docker-compose.yml) or a .env file for local dev."""

    data_dir: Path = Path("./data")
    cors_allow_origins: list[str] = ["*"]
    window_size: int = 50
    window_step: int = 10
    log_level: str = "INFO"

    # If unset (the default), write endpoints (POST /api/scans, /api/labels,
    # /api/train) require no auth — matches this project's original
    # behavior, so existing local/dev usage is unaffected. Set AFM_API_KEY
    # to require an `X-API-Key` header matching this value on those
    # endpoints — do this before exposing the API beyond a trusted demo
    # audience, especially once an MCP-based assistant (packages/mcp_server)
    # can call them on your behalf. Read-only GET endpoints are never
    # gated, so browsing scans/heatmaps/curves always works without a key.
    api_key: str | None = None

    model_config = {"env_prefix": "AFM_"}

    @property
    def scans_dir(self) -> Path:
        d = self.data_dir / "scans"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def models_dir(self) -> Path:
        d = self.data_dir / "models"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def labels_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "labels.jsonl"


@lru_cache
def get_settings() -> Settings:
    return Settings()

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

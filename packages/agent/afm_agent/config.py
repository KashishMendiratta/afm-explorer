from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def default_knowledge_path() -> Path:
    return Path(__file__).resolve().parents[3] / "knowledge"


@dataclass(frozen=True)
class AgentSettings:
    backend_url: str
    model: str
    max_turns: int
    allow_writes: bool
    api_key: str
    knowledge_path: Path

    @classmethod
    def from_env(cls) -> "AgentSettings":
        max_turns = int(os.getenv("AFM_AGENT_MAX_TURNS", "8"))
        if not 1 <= max_turns <= 20:
            raise ValueError("AFM_AGENT_MAX_TURNS must be between 1 and 20")
        return cls(
            backend_url=os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/"),
            model=os.getenv("AFM_AGENT_MODEL", "gpt-5.6-luna"),
            max_turns=max_turns,
            allow_writes=_env_bool("AFM_AGENT_ALLOW_WRITES", False),
            api_key=os.getenv("AFM_API_KEY", ""),
            knowledge_path=Path(os.getenv("AFM_KNOWLEDGE_PATH", str(default_knowledge_path()))),
        )

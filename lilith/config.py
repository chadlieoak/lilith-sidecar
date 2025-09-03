from __future__ import annotations
import os
from dataclasses import dataclass

def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v is not None else default

@dataclass
class Settings:
    llm_provider: str = _env("LLM_PROVIDER", "openai") or "openai"  # openai|anthropic|ollama
    llm_model: str = _env("LLM_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
    openai_api_key: str | None = _env("OPENAI_API_KEY")
    openai_base_url: str = _env("OPENAI_BASE_URL", "https://api.openai.com/v1") or "https://api.openai.com/v1"
    anthropic_api_key: str | None = _env("ANTHROPIC_API_KEY")
    anthropic_base_url: str = _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1") or "https://api.anthropic.com/v1"
    ollama_base_url: str = _env("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434"
    temperature: float = float(_env("LLM_TEMPERATURE", "0.2"))
    timeout_s: int = int(_env("LLM_TIMEOUT_S", "40"))
    max_steps: int = int(_env("LLM_STEPS_MAX", "12"))

_settings: Settings | None = None
def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

from __future__ import annotations
import json
from typing import Protocol, Optional, Dict, Any
from lilith.config import get_settings

# Use requests if available, else fallback to urllib
try:
    import requests  # type: ignore
except Exception as _e:
    requests = None

class LLMClient(Protocol):
    def generate(self, *, system: str, user: str) -> str:
        ...

def _require_requests():
    if requests is None:
        raise RuntimeError("The 'requests' package is required for remote LLM providers. pip install requests")

class OpenAIClient:
    def __init__(self, api_key: Optional[str], base_url: str, model: str, temperature: float, timeout_s: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_s = timeout_s

    def generate(self, *, system: str, user: str) -> str:
        _require_requests()
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY missing")
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        # Try common shapes
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)

class AnthropicClient:
    def __init__(self, api_key: Optional[str], base_url: str, model: str, temperature: float, timeout_s: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_s = timeout_s

    def generate(self, *, system: str, user: str) -> str:
        _require_requests()
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        url = f"{self.base_url}/messages"
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": self.temperature,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        try:
            # Anthropic returns content as a list of blocks
            blocks = data.get("content", [])
            texts = [b.get("text", "") for b in blocks if isinstance(b, dict)]
            return "\n".join(texts).strip()
        except Exception:
            return json.dumps(data)

class OllamaClient:
    def __init__(self, base_url: str, model: str, temperature: float, timeout_s: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_s = timeout_s

    def generate(self, *, system: str, user: str) -> str:
        _require_requests()
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": self.temperature},
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        try:
            return data["message"]["content"]
        except Exception:
            return json.dumps(data)

def get_client() -> LLMClient:
    s = get_settings()
    if s.llm_provider == "openai":
        return OpenAIClient(s.openai_api_key, s.openai_base_url, s.llm_model, s.temperature, s.timeout_s)
    if s.llm_provider == "anthropic":
        return AnthropicClient(s.anthropic_api_key, s.anthropic_base_url, s.llm_model, s.temperature, s.timeout_s)
    if s.llm_provider == "ollama":
        return OllamaClient(s.ollama_base_url, s.llm_model, s.temperature, s.timeout_s)
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {s.llm_provider}")

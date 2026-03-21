"""Multi-provider LLM abstraction layer.

Supports: OpenAI, Anthropic, Mistral, Groq, Ollama (local),
LMStudio (local), and a deterministic fallback provider.

Usage:
    from market_insights.llm.providers import get_llm, list_providers
    llm = get_llm("openai")
    response = llm.generate(
        "Analyse technique AAPL",
        system="Tu es un analyste financier.",
    )
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from market_insights.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: dict | None = None


class BaseLLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse: ...

    def models(self) -> list[str]:
        return []


# ━━ OpenAI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    DEFAULT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    def available(self) -> bool:
        return bool(settings.openai_api_key)

    def models(self) -> list[str]:
        return self.DEFAULT_MODELS

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        import openai

        client = openai.OpenAI(api_key=settings.openai_api_key)
        model = settings.llm_model or "gpt-4o-mini"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature or settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
        )
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            model=model,
            provider="openai",
            usage={
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
            }
            if resp.usage
            else None,
        )


# ━━ Anthropic ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"

    DEFAULT_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-haiku-4-20250414",
        "claude-3-5-sonnet-20241022",
    ]

    def available(self) -> bool:
        return bool(settings.anthropic_api_key)

    def models(self) -> list[str]:
        return self.DEFAULT_MODELS

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        model = settings.llm_model or "claude-sonnet-4-20250514"
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens or settings.llm_max_tokens,
            temperature=temperature or settings.llm_temperature,
            system=system or "Tu es un analyste financier expert.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return LLMResponse(
            text=text,
            model=model,
            provider="anthropic",
            usage={
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
        )


# ━━ Mistral ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MistralProvider(BaseLLMProvider):
    name = "mistral"

    DEFAULT_MODELS = [
        "mistral-large-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
        "open-mistral-nemo",
    ]

    def available(self) -> bool:
        return bool(settings.mistral_api_key)

    def models(self) -> list[str]:
        return self.DEFAULT_MODELS

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        model = settings.llm_model or "mistral-small-latest"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.mistral_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature or settings.llm_temperature,
                    "max_tokens": max_tokens or settings.llm_max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            model=model,
            provider="mistral",
            usage=data.get("usage"),
        )


# ━━ Groq ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class GroqProvider(BaseLLMProvider):
    name = "groq"

    DEFAULT_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def available(self) -> bool:
        return bool(settings.groq_api_key)

    def models(self) -> list[str]:
        return self.DEFAULT_MODELS

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        model = settings.llm_model or "llama-3.3-70b-versatile"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature or settings.llm_temperature,
                    "max_tokens": max_tokens or settings.llm_max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            model=model,
            provider="groq",
            usage=data.get("usage"),
        )


# ━━ Ollama (local) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def available(self) -> bool:
        try:
            resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def models(self) -> list[str]:
        try:
            resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return [settings.ollama_model]

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        model = settings.llm_model or settings.ollama_model
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {
                "temperature": temperature or settings.llm_temperature,
                "num_predict": max_tokens or settings.llm_max_tokens,
            },
        }
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return LLMResponse(
            text=data.get("response", ""),
            model=model,
            provider="ollama",
            usage={
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
            },
        )


# ━━ LMStudio (local, OpenAI-compatible) ━━━━━━━━━━━━━━━━━━━━━━━━━━


class LMStudioProvider(BaseLLMProvider):
    name = "lmstudio"

    def available(self) -> bool:
        try:
            resp = httpx.get(f"{settings.lmstudio_base_url}/v1/models", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def models(self) -> list[str]:
        try:
            resp = httpx.get(f"{settings.lmstudio_base_url}/v1/models", timeout=5)
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return [settings.lmstudio_model]

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        model = settings.llm_model or settings.lmstudio_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{settings.lmstudio_base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature or settings.llm_temperature,
                    "max_tokens": max_tokens or settings.llm_max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            model=model,
            provider="lmstudio",
            usage=data.get("usage"),
        )


# ━━ Fallback (deterministic, no LLM) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FallbackProvider(BaseLLMProvider):
    name = "fallback"

    def available(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        # Return the prompt context as-is for deterministic behavior
        return LLMResponse(
            text=f"[Mode fallback — aucun LLM configuré] Contexte reçu: {prompt[:800]}",
            model="fallback",
            provider="fallback",
        )


# ━━ Registry ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_PROVIDERS: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "mistral": MistralProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
    "lmstudio": LMStudioProvider,
    "fallback": FallbackProvider,
}


def get_llm(backend: str | None = None) -> BaseLLMProvider:
    """Get an LLM provider instance by name."""
    name = (backend or settings.llm_backend).lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        logger.warning("Unknown LLM backend '%s', using fallback", name)
        return FallbackProvider()
    return cls()


def list_providers() -> list[dict]:
    """List all providers with availability status."""
    result = []
    for name, cls in _PROVIDERS.items():
        inst = cls()
        try:
            avail = inst.available()
        except Exception:
            avail = False
        try:
            models = inst.models() if avail else []
        except Exception:
            models = []
        result.append({"name": name, "available": avail, "models": models})
    return result

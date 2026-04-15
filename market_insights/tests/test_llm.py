"""Tests for public LLM provider exposure."""

from market_insights.llm.providers import (
    FallbackProvider,
    get_llm,
    is_public_provider,
    list_providers,
)


def test_fallback_always_available():
    llm = get_llm("fallback")
    assert llm.available()


def test_fallback_generates_text():
    llm = get_llm("fallback")
    resp = llm.generate("test prompt")
    assert resp.text
    assert resp.provider == "fallback"


def test_unknown_backend_returns_fallback():
    llm = get_llm("nonexistent_provider")
    assert isinstance(llm, FallbackProvider)


def test_list_providers_hides_internal_backends():
    provs = list_providers()
    names = [p["name"] for p in provs]
    assert "litellm" in names
    assert "openai" in names
    assert "anthropic" in names
    assert "lmstudio" in names
    assert "fallback" in names
    assert "ollama" not in names
    # Fallback should always be available
    fallback = next(p for p in provs if p["name"] == "fallback")
    assert fallback["available"] is True


def test_ollama_is_not_public():
    assert is_public_provider("litellm") is True
    assert is_public_provider("ollama") is False

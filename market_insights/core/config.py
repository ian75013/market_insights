from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────
    app_env: str = "dev"
    app_name: str = "Market Insights"
    database_url: str = "sqlite:///./market_insights.db"

    # ── Network & provider routing ─────────────────────────────────
    use_network: bool = False
    default_price_provider: str = "sample"

    # ── IBKR ───────────────────────────────────────────────────────
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 1

    # ── Data API keys (all optional) ──────────────────────────────
    alpha_vantage_api_key: str = ""
    fred_api_key: str = ""
    fmp_api_key: str = ""
    sec_user_agent: str = "MarketInsights/1.0 contact@example.com"

    # ── LLM — multi-provider ──────────────────────────────────────
    llm_backend: str = (
        "fallback"  # fallback | openai | anthropic | mistral | groq | ollama | lmstudio
    )
    llm_model: str = (
        ""  # model name override (e.g. gpt-4o, claude-sonnet-4-20250514, llama3)
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    mistral_api_key: str = ""
    groq_api_key: str = ""

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    lmstudio_base_url: str = "http://localhost:1234"
    lmstudio_model: str = "default"

    llm_temperature: float = 0.3
    llm_max_tokens: int = 800

    # ── RAG ────────────────────────────────────────────────────────
    rag_embedding_model: str = "all-MiniLM-L6-v2"  # sentence-transformers model
    rag_use_vectors: bool = True  # True=vector, False=lexical fallback
    rag_top_k: int = 5
    rag_chunk_size: int = 400
    rag_chunk_overlap: int = 60

    # ── Cache ──────────────────────────────────────────────────────
    cache_ttl_prices: int = 900
    cache_ttl_fundamentals: int = 3600
    cache_ttl_macro: int = 1800
    cache_ttl_news: int = 600

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

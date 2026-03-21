from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────
    app_env: str = "dev"
    app_name: str = "Market Insights"
    database_url: str = "sqlite:///./market_insights.db"

    # ── LLM ────────────────────────────────────────────────────────
    openai_api_key: str = ""
    llm_backend: str = "fallback"

    # ── IBKR ───────────────────────────────────────────────────────
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 1

    # ── Network & provider routing ─────────────────────────────────
    use_network: bool = False
    default_price_provider: str = "sample"

    # ── Free-tier API keys (all optional) ──────────────────────────
    alpha_vantage_api_key: str = ""
    fred_api_key: str = ""
    fmp_api_key: str = ""              # financialmodelingprep.com
    sec_user_agent: str = "MarketInsights/1.0 contact@example.com"

    # ── Cache ──────────────────────────────────────────────────────
    cache_ttl_prices: int = 900        # 15 min
    cache_ttl_fundamentals: int = 3600 # 1 h
    cache_ttl_macro: int = 1800        # 30 min
    cache_ttl_news: int = 600          # 10 min

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_name: str = "Market Insights"
    database_url: str = "sqlite:///./market_insights.db"
    openai_api_key: str = ""
    llm_backend: str = "fallback"
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 1
    use_network: bool = False
    default_price_provider: str = "sample"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APT_HUNTER_",
        extra="ignore",
    )

    app_name: str = "APT Hunter API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://apt_hunter:change-me@localhost:5432/apt_hunter"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "change-me"
    minio_secret_key: str = "change-me"
    minio_secure: bool = False
    minio_bucket: str = "apt-hunter-raw"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    rss_user_agent: str = "APT-Hunter/0.1 (+https://localhost)"
    rss_timeout_seconds: float = 20.0
    rss_relevance_threshold: int = 50
    rss_scheduler_batch_size: int = 20
    article_timeout_seconds: float = 30.0
    article_max_bytes: int = 5_242_880
    enrichment_scheduler_batch_size: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()

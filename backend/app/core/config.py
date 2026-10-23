from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://eva:change-me@localhost:5432/eva_explorer"
    test_database_url: str = (
        "postgresql+psycopg://eva:change-me@localhost:5432/eva_explorer_test"
    )
    cors_origins: list[str] = ["http://localhost:3000"]
    api_prefix: str = "/api/v1"
    export_max_rows: int = Field(default=200_000, ge=1)
    export_batch_size: int = Field(default=1_000, ge=1)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

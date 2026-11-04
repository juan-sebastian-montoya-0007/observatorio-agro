from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
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
    openai_api_key: SecretStr | None = None
    openai_model: str = 'gpt-5-mini'
    assistant_provider: Literal['ollama', 'openai'] = 'ollama'
    ollama_base_url: str = 'http://localhost:11434'
    ollama_model: str = 'qwen3:4b'
    ollama_timeout: int = Field(default=180, ge=10, le=300)

    @field_validator('openai_api_key', mode='before')
    @classmethod
    def empty_key(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Library Management API"
    app_env: str = "development"
    app_debug: bool = False

    database_url: str = "sqlite:///./library.db"

    cors_origins: str = "http://localhost:3000"

    auth_disabled: bool = False
    auth0_domain: str = ""
    auth0_audience: str = ""
    owner_auth0_sub: str = ""

    ai_enabled: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_app_name: str = "BookFlow"

    checkout_days: int = Field(default=14, ge=1, le=60)

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

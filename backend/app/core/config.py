from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Komorebi"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./komorebi.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    storage_root: str = "storage"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-5.5"
    openai_review_model: str = "gpt-5.4-mini"
    internal_render_url: str = "http://127.0.0.1:52897/internal/render"
    playwright_chromium_executable: str = "/usr/bin/google-chrome"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

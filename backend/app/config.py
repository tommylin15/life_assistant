import json
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_bundle() -> None:
    bundle_json = os.environ.get("LIFE_ASSISTANT_BUNDLE")
    if not bundle_json:
        return
    try:
        for key, value in json.loads(bundle_json).items():
            os.environ[key] = value
    except json.JSONDecodeError:
        pass


_load_bundle()


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/life_assistant"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8081/auth/callback"
    frontend_url: str = "http://localhost:5000"

    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")


settings = Settings()

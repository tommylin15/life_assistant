import json
import os
from io import StringIO
from urllib.parse import quote

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/life_assistant"


def _normalize_database_url(value: str) -> str:
    value = value.strip()
    if value.startswith("postgresql://"):
        return "postgresql+asyncpg://" + value[len("postgresql://") :]
    return value


def _parse_bundle(raw: str) -> tuple[dict[str, str], str]:
    raw = raw.strip()
    if not raw:
        return {}, "empty"

    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = None

    if isinstance(value, dict):
        parsed: dict[str, str] = {}
        for key, item in value.items():
            if not isinstance(key, str) or item is None or isinstance(item, (dict, list)):
                return {}, "unknown"
            parsed[key] = str(item)
        if "DATABASE_URL" in parsed:
            parsed["DATABASE_URL"] = _normalize_database_url(parsed["DATABASE_URL"])
        if "database_url" in parsed:
            parsed["database_url"] = _normalize_database_url(parsed["database_url"])
        return parsed, "json-object"

    if raw.startswith(("postgresql://", "postgresql+asyncpg://")):
        return {"DATABASE_URL": _normalize_database_url(raw)}, "raw-database-url"

    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if lines and all("=" in line.removeprefix("export ") for line in lines):
        values = dotenv_values(stream=StringIO(raw))
        if values and all(value is not None for value in values.values()):
            parsed = {str(key): str(value) for key, value in values.items()}
            if "DATABASE_URL" in parsed:
                parsed["DATABASE_URL"] = _normalize_database_url(parsed["DATABASE_URL"])
            if "database_url" in parsed:
                parsed["database_url"] = _normalize_database_url(parsed["database_url"])
            return parsed, "dotenv"

    return {}, "unknown"


def _database_url_from_password(password: str) -> str | None:
    host = os.environ.get("DATABASE_HOST", "").strip()
    user = os.environ.get("DATABASE_USER", "").strip()
    database = os.environ.get("DATABASE_NAME", "").strip()
    port = os.environ.get("DATABASE_PORT", "5432").strip() or "5432"
    sslmode = os.environ.get("DATABASE_SSLMODE", "require").strip() or "require"
    if not host or not user or not database:
        return None

    return (
        "postgresql+asyncpg://"
        + quote(user, safe="")
        + ":"
        + quote(password, safe="")
        + "@"
        + host
        + ":"
        + port
        + "/"
        + quote(database, safe="")
        + "?sslmode="
        + quote(sslmode, safe="")
    )


def _load_bundle() -> str:
    raw = os.environ.get("LIFE_ASSISTANT_BUNDLE", "")
    values, bundle_format = _parse_bundle(raw)

    if (
        bundle_format == "unknown"
        and raw.strip()
        and "\n" not in raw.strip()
        and os.environ.get("LIFE_ASSISTANT_OPAQUE_SECRET_KIND") == "database-password"
    ):
        database_url = _database_url_from_password(raw.strip())
        if database_url:
            values = {"DATABASE_URL": database_url}
            bundle_format = "opaque-database-password"

    for key, value in values.items():
        os.environ[key] = value
    return bundle_format


BUNDLE_FORMAT = _load_bundle()


class Settings(BaseSettings):
    database_url: str = DEFAULT_DATABASE_URL
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8081/auth/callback"
    frontend_url: str = "http://localhost:5000"

    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")


settings = Settings()

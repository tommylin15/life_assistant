import json
import os
from io import StringIO
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import yaml
from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/life_assistant"
DATABASE_PASSWORD_KEYS = {
    "database_password",
    "postgres_password",
    "postgresql_password",
    "db_password",
}


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(".", "_")


def _normalize_database_url(value: str) -> str:
    value = value.strip()
    if value.startswith("postgresql://"):
        value = "postgresql+asyncpg://" + value[len("postgresql://") :]

    if value.startswith("postgresql+asyncpg://"):
        parsed = urlsplit(value)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        has_ssl = any(key == "ssl" for key, _ in query)
        normalized_query = [
            ("ssl" if key == "sslmode" and not has_ssl else key, item)
            for key, item in query
            if not (key == "sslmode" and has_ssl)
        ]
        value = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(normalized_query),
                parsed.fragment,
            )
        )
    return value


def _flatten_mapping(value: dict, prefix: str = "") -> dict[str, str]:
    parsed: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or item is None:
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            parsed.update(_flatten_mapping(item, path))
        elif isinstance(item, (str, int, float, bool)):
            parsed[path] = str(item)
    return parsed


def _normalize_parsed_values(values: dict[str, str]) -> dict[str, str]:
    parsed = dict(values)
    for key, value in list(parsed.items()):
        normalized_key = _normalize_key(key)
        if normalized_key == "database_url":
            parsed[key] = _normalize_database_url(value)
    return parsed


def _parse_bundle(raw: str) -> tuple[dict[str, str], str]:
    raw = raw.strip()
    if not raw:
        return {}, "empty"

    try:
        value = json.loads(raw)
        if isinstance(value, str):
            try:
                nested = json.loads(value)
            except json.JSONDecodeError:
                nested = None
            if isinstance(nested, dict):
                value = nested
    except json.JSONDecodeError:
        value = None

    if isinstance(value, dict):
        return _normalize_parsed_values(_flatten_mapping(value)), "json-object"

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
            return _normalize_parsed_values(parsed), "dotenv"

    try:
        value = yaml.safe_load(raw)
    except yaml.YAMLError:
        value = None
    if isinstance(value, dict):
        return _normalize_parsed_values(_flatten_mapping(value)), "yaml-object"

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
        + "?ssl="
        + quote(sslmode, safe="")
    )


def _extract_database_url(values: dict[str, str]) -> str | None:
    for key, value in values.items():
        if _normalize_key(key) == "database_url":
            return _normalize_database_url(value)
    return None


def _extract_database_password(values: dict[str, str]) -> str | None:
    for key, value in values.items():
        if _normalize_key(key) in DATABASE_PASSWORD_KEYS and value:
            return value
    return None


def _load_bundle() -> str:
    raw = os.environ.get("LIFE_ASSISTANT_BUNDLE", "")
    values, bundle_format = _parse_bundle(raw)

    database_url = _extract_database_url(values)
    if not database_url:
        password = _extract_database_password(values)
        if password:
            database_url = _database_url_from_password(password)
    if database_url:
        values["DATABASE_URL"] = database_url

    for key, value in values.items():
        if "." not in key:
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

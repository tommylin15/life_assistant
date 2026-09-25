import base64
import json
import os
import re
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
    "database_pass",
    "postgres_pass",
    "postgresql_pass",
    "db_pass",
    "pg_pass",
}
COLON_COMMA_BUNDLE_KEYS = (
    "DATABASE_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
)


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(".", "_")


def _strip_matching_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _strip_wrapper_quotes(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^(?:\\?[\"'])+", "", value)
    value = re.sub(r"(?:\\?[\"'])+$", "", value)
    return value.strip()


def _normalize_database_url(value: str) -> str:
    value = _strip_matching_quotes(value)
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
        else:
            parsed[key] = _strip_matching_quotes(value)
    return parsed


def _parse_known_key_bundle(raw: str) -> dict[str, str] | None:
    """Parse known bundle keys even when a legacy wrapper precedes them."""
    key_pattern = "|".join(re.escape(key) for key in COLON_COMMA_BUNDLE_KEYS)
    pattern = re.compile(
        rf"(?i)(?:^|[\s{{,;|])(?:\\?[\"'])*({key_pattern})(?:\\?[\"'])*\s*[:=]\s*"
    )
    matches = list(pattern.finditer(raw))
    if not matches:
        return None

    parsed: dict[str, str] = {}
    for index, match in enumerate(matches):
        key = match.group(1).upper()
        # OAuth secret rotation can temporarily leave the previous secret in a
        # legacy bundle and append the replacement. Last value wins only for
        # GOOGLE_CLIENT_SECRET; duplicate database/client-id keys remain
        # ambiguous and therefore fail closed.
        if key in parsed and key != "GOOGLE_CLIENT_SECRET":
            return None
        value_start = match.end()
        value_end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        value = raw[value_start:value_end].strip()
        value = re.sub(r"[\s,;|]+$", "", value)
        value = _strip_wrapper_quotes(value)
        value = re.sub(r"[\s}\])]+$", "", value).strip()
        if not value:
            return None
        parsed[key] = value

    if "DATABASE_URL" not in parsed:
        return None
    return parsed


def _extract_embedded_database_url(raw: str) -> str | None:
    """Extract only the PostgreSQL URL from an otherwise unknown bundle framing."""
    url_match = re.search(r"postgresql(?:\+asyncpg)?://", raw, re.IGNORECASE)
    if url_match is None:
        return None

    start = url_match.start()
    tail = raw[start:]
    next_key = re.search(
        r"(?i)(?:,|;|\|)\s*(?:\\?[\"'])*"
        r"(?:GOOGLE_CLIENT_ID|GOOGLE_CLIENT_SECRET)"
        r"(?:\\?[\"'])*\s*[:=]",
        tail,
    )
    end = start + next_key.start() if next_key is not None else len(raw)
    candidate = raw[start:end].strip()
    candidate = re.sub(r"[\s,;|]+$", "", candidate)
    candidate = re.sub(r"(?:\\?[\"'])+$", "", candidate)
    candidate = re.sub(r"[\s}\])]+$", "", candidate).strip()
    if not candidate:
        return None

    normalized = _normalize_database_url(candidate)
    parsed = urlsplit(normalized)
    if parsed.scheme != "postgresql+asyncpg" or not parsed.hostname or not parsed.path:
        return None
    return normalized


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
    dotenv_assignment = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*=")
    if lines and all(
        dotenv_assignment.match(line.removeprefix("export ").lstrip())
        for line in lines
    ):
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

    known_key_bundle = _parse_known_key_bundle(raw)
    if known_key_bundle is not None:
        return _normalize_parsed_values(known_key_bundle), "known-key-bundle"

    embedded_database_url = _extract_embedded_database_url(raw)
    if embedded_database_url:
        return {"DATABASE_URL": embedded_database_url}, "embedded-database-url"

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


def _decoded_base64_text(raw: str) -> str | None:
    compact = "".join(raw.split())
    if not compact or len(compact) % 4 != 0:
        return None
    try:
        decoded = base64.b64decode(compact, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if not decoded or any(ord(ch) < 9 for ch in decoded):
        return None
    return decoded


def _bundle_structure_hints(raw: str) -> tuple[list[str], list[str], list[str]]:
    raw = raw.strip()
    if not raw:
        return ["empty"], [], []

    shape: list[str] = []
    if "\n" in raw:
        shape.append("multiline")
    for token, name in (("=", "equals"), (":", "colon"), (";", "semicolon"), ("|", "pipe"), (",", "comma")):
        if token in raw:
            shape.append(name)
    if raw.startswith("{"):
        shape.append("brace-prefix")
    if raw.startswith("["):
        shape.append("bracket-prefix")
    if raw.startswith(('"', "'")):
        shape.append("quote-prefix")

    texts = [raw]
    decoded = _decoded_base64_text(raw)
    if decoded is not None:
        shape.append("base64-text")
        texts.append(decoded)

    all_keys: set[str] = set()
    password_hints: set[str] = set()
    assignment_pattern = re.compile(
        r"(?im)(?:^|[\s{,;|])['\"]?([A-Za-z][A-Za-z0-9_.-]{0,63})['\"]?\s*[:=]"
    )
    password_word_pattern = re.compile(
        r"(?i)\b([A-Za-z][A-Za-z0-9_.-]*(?:password|passwd|pwd|pgpass|_pass|-pass)[A-Za-z0-9_.-]*)\b"
    )
    for text in texts:
        candidates = [match.group(1) for match in assignment_pattern.finditer(text)]
        all_keys.update(candidates)
        password_candidates = list(candidates)
        password_candidates.extend(match.group(1) for match in password_word_pattern.finditer(text))
        for candidate in password_candidates:
            normalized = _normalize_key(candidate)
            if (
                normalized in DATABASE_PASSWORD_KEYS
                or any(token in normalized for token in ("password", "passwd", "pwd", "pgpass"))
                or normalized.endswith("_pass")
            ):
                password_hints.add(candidate)

    return shape or ["opaque"], sorted(password_hints)[:8], sorted(all_keys)[:16]


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


_RAW_BUNDLE = os.environ.get("LIFE_ASSISTANT_BUNDLE", "")
BUNDLE_SHAPE, BUNDLE_PASSWORD_KEY_HINTS, BUNDLE_KEY_HINTS = _bundle_structure_hints(_RAW_BUNDLE)
BUNDLE_FORMAT = _load_bundle()


class Settings(BaseSettings):
    database_url: str = DEFAULT_DATABASE_URL
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8081/auth/callback"
    frontend_url: str = "http://localhost:5000"

    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")


settings = Settings()

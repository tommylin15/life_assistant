#!/usr/bin/env python3
"""Deterministic, fail-closed SQLite -> PostgreSQL historical backfill.

The SQLite source is opened read-only. The importer never overwrites an
existing Cloud row without its own migration ledger entry. A rerun of the same
bundle is therefore idempotent while a collision or source drift fails closed.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable
from urllib.parse import quote
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings

FORMAT_VERSION = "1"
SUPPORTED_SOURCE_VERSIONS = {1, 2, 3}

SOURCE_TABLE_KEYS: dict[str, tuple[str, ...]] = {
    "projects": ("id",),
    "items": ("id",),
    "checklist_items": ("id",),
    "notes": ("id",),
    "note_links": ("source_note_id", "target_note_id"),
    "habits": ("id",),
    "habit_logs": ("id",),
    "shopping_lists": ("id",),
    "shopping_items": ("id",),
    "tags": ("id",),
    "entity_tags": ("entity_type", "entity_id", "tag_id"),
    "reminders": ("id",),
    "templates": ("id",),
    "attachments": ("id",),
    "calendar_events_cache": ("id",),
    "gmail_refs": ("id",),
    "activity_logs": ("id",),
    "preferences": ("key",),
    "bridge_state": ("key",),
}

LOCAL_ONLY_TABLES = (
    "sync_pairs",
    "sync_files",
    "sync_operations",
    "bridge_executions",
)

VALID_TASK_STATUSES = {
    "pending",
    "in_progress",
    "waiting",
    "scheduled",
    "completed",
    "cancelled",
}
VALID_TASK_PRIORITIES = {"low", "normal", "high"}


class BackfillError(RuntimeError):
    pass


class BundleValidationError(BackfillError):
    pass


class RelationshipValidationError(BackfillError):
    pass


class TargetCollisionError(BackfillError):
    pass


class RerunDriftError(BackfillError):
    pass


@dataclass(frozen=True)
class MigrationItem:
    source_table: str
    source_key: str
    row_sha256: str
    target_table: str
    target_key: dict[str, Any]
    values: dict[str, Any]


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"$base64": base64.b64encode(value).decode("ascii")}
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _open_sqlite_readonly(path: Path) -> sqlite3.Connection:
    resolved = path.expanduser().resolve(strict=True)
    uri = f"file:{quote(str(resolved))}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')]


def _table_rows(
    connection: sqlite3.Connection,
    table: str,
    key_columns: tuple[str, ...],
) -> list[dict[str, Any]]:
    columns = _table_columns(connection, table)
    if not columns:
        return []
    missing = set(key_columns) - set(columns)
    if missing:
        raise BundleValidationError(
            f"source table {table} missing key columns: {','.join(sorted(missing))}"
        )
    select_columns = ", ".join(f'"{column}"' for column in columns)
    order_by = ", ".join(f'"{column}"' for column in key_columns)
    rows = connection.execute(
        f'SELECT {select_columns} FROM "{table}" ORDER BY {order_by}'
    ).fetchall()
    return [
        {column: _json_safe(row[column]) for column in columns}
        for row in rows
    ]


def export_bundle(sqlite_path: Path) -> dict[str, Any]:
    connection = _open_sqlite_readonly(sqlite_path)
    try:
        source_schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if source_schema_version not in SUPPORTED_SOURCE_VERSIONS:
            raise BundleValidationError(
                f"unsupported SQLite schema version: {source_schema_version}"
            )
        if not _table_exists(connection, "items"):
            raise BundleValidationError("source is not a life_assistant SQLite database")

        tables: dict[str, list[dict[str, Any]]] = {}
        for table, key_columns in SOURCE_TABLE_KEYS.items():
            tables[table] = (
                _table_rows(connection, table, key_columns)
                if _table_exists(connection, table)
                else []
            )

        local_only_state_counts = {
            table: int(connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
            if _table_exists(connection, table)
            else 0
            for table in LOCAL_ONLY_TABLES
        }
    finally:
        connection.close()

    payload: dict[str, Any] = {
        "format_version": FORMAT_VERSION,
        "source_schema_version": source_schema_version,
        "tables": tables,
        "local_only_state_counts": local_only_state_counts,
    }
    payload["source_fingerprint"] = _sha256(payload)
    return payload


def write_bundle(sqlite_path: Path, output_path: Path) -> dict[str, Any]:
    bundle = export_bundle(sqlite_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_canonical_bytes(bundle) + b"\n")
    return bundle


def load_bundle(path: Path) -> dict[str, Any]:
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleValidationError("invalid migration bundle") from exc
    if bundle.get("format_version") != FORMAT_VERSION:
        raise BundleValidationError("unsupported migration bundle format")
    fingerprint = bundle.get("source_fingerprint")
    unsigned = {key: value for key, value in bundle.items() if key != "source_fingerprint"}
    if not isinstance(fingerprint, str) or fingerprint != _sha256(unsigned):
        raise BundleValidationError("migration bundle fingerprint mismatch")
    if int(bundle.get("source_schema_version", 0)) not in SUPPORTED_SOURCE_VERSIONS:
        raise BundleValidationError("unsupported source schema version")
    if not isinstance(bundle.get("tables"), dict):
        raise BundleValidationError("migration bundle tables are missing")
    return bundle


def _source_key(row: dict[str, Any], columns: tuple[str, ...]) -> str:
    return json.dumps(
        [row.get(column) for column in columns],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _require_id(value: Any, field: str) -> str:
    text_value = str(value)
    if not text_value or len(text_value) > 36:
        raise BundleValidationError(f"invalid {field}")
    return text_value


def _nullable_id(value: Any, field: str) -> str | None:
    return None if value is None else _require_id(value, field)


def _as_bool(value: Any, field: str) -> bool:
    if value in (0, False):
        return False
    if value in (1, True):
        return True
    raise BundleValidationError(f"invalid boolean field: {field}")


def _as_datetime(value: Any, field: str, *, nullable: bool = False) -> datetime | None:
    if value is None:
        if nullable:
            return None
        raise BundleValidationError(f"missing datetime field: {field}")
    if isinstance(value, (int, float)):
        number = float(value)
        absolute = abs(number)
        if absolute >= 100_000_000_000_000:
            number /= 1_000_000
        elif absolute >= 100_000_000_000:
            number /= 1_000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    if isinstance(value, str):
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise BundleValidationError(f"ambiguous timezone in {field}")
        return parsed.astimezone(timezone.utc)
    raise BundleValidationError(f"invalid datetime field: {field}")


def _table(bundle: dict[str, Any], name: str) -> list[dict[str, Any]]:
    rows = bundle["tables"].get(name, [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise BundleValidationError(f"invalid rows for {name}")
    return rows


def _ids(rows: Iterable[dict[str, Any]]) -> set[str]:
    return {str(row["id"]) for row in rows}


def validate_relationships(bundle: dict[str, Any]) -> None:
    projects = _ids(_table(bundle, "projects"))
    tasks = _ids(_table(bundle, "items"))
    notes = _ids(_table(bundle, "notes"))
    habits = _ids(_table(bundle, "habits"))
    shopping_lists = _ids(_table(bundle, "shopping_lists"))
    tags = _ids(_table(bundle, "tags"))

    def require_optional_project(rows: Iterable[dict[str, Any]], table: str) -> None:
        for row in rows:
            value = row.get("project_id")
            if value is not None and str(value) not in projects:
                raise RelationshipValidationError(f"{table} references missing project")

    require_optional_project(_table(bundle, "items"), "items")
    require_optional_project(_table(bundle, "notes"), "notes")
    require_optional_project(_table(bundle, "shopping_lists"), "shopping_lists")
    require_optional_project(_table(bundle, "calendar_events_cache"), "calendar_events_cache")

    for row in _table(bundle, "checklist_items"):
        if str(row.get("item_id")) not in tasks:
            raise RelationshipValidationError("checklist_items references missing item")
    for row in _table(bundle, "note_links"):
        if str(row.get("source_note_id")) not in notes or str(row.get("target_note_id")) not in notes:
            raise RelationshipValidationError("note_links references missing note")
    for row in _table(bundle, "habit_logs"):
        if str(row.get("habit_id")) not in habits:
            raise RelationshipValidationError("habit_logs references missing habit")
    for row in _table(bundle, "shopping_items"):
        if str(row.get("list_id")) not in shopping_lists:
            raise RelationshipValidationError("shopping_items references missing list")
    for row in _table(bundle, "entity_tags"):
        if str(row.get("tag_id")) not in tags:
            raise RelationshipValidationError("entity_tags references missing tag")


def _make_item(
    source_table: str,
    row: dict[str, Any],
    target_table: str,
    target_key: dict[str, Any],
    values: dict[str, Any],
) -> MigrationItem:
    return MigrationItem(
        source_table=source_table,
        source_key=_source_key(row, SOURCE_TABLE_KEYS[source_table]),
        row_sha256=_sha256(row),
        target_table=target_table,
        target_key=target_key,
        values=values,
    )


def build_migration_items(bundle: dict[str, Any]) -> list[MigrationItem]:
    validate_relationships(bundle)
    items: list[MigrationItem] = []

    for row in _table(bundle, "projects"):
        key = {"id": _require_id(row["id"], "projects.id")}
        items.append(_make_item("projects", row, "projects", key, {
            **key,
            "name": str(row["name"]),
            "summary": row.get("summary"),
            "status": str(row.get("status") or "active"),
            "created_at": _as_datetime(row["created_at"], "projects.created_at"),
            "updated_at": _as_datetime(row["updated_at"], "projects.updated_at"),
        }))

    for row in _table(bundle, "items"):
        status = str(row.get("status") or "pending")
        priority = str(row.get("priority") or "normal")
        if status not in VALID_TASK_STATUSES:
            raise BundleValidationError(f"unsupported task status: {status}")
        if priority not in VALID_TASK_PRIORITIES:
            raise BundleValidationError(f"unsupported task priority: {priority}")
        key = {"id": _require_id(row["id"], "items.id")}
        items.append(_make_item("items", row, "tasks", key, {
            **key,
            "title": str(row["title"]),
            "note": row.get("note"),
            "status": status,
            "priority": priority,
            "due_at": _as_datetime(row.get("due_at"), "items.due_at", nullable=True),
            "reminder_at": _as_datetime(row.get("reminder_at"), "items.reminder_at", nullable=True),
            "project_id": _nullable_id(row.get("project_id"), "items.project_id"),
            "source_type": row.get("source_type"),
            "source_ref": row.get("source_ref"),
            "created_at": _as_datetime(row["created_at"], "items.created_at"),
            "updated_at": _as_datetime(row["updated_at"], "items.updated_at"),
            "completed_at": _as_datetime(row.get("completed_at"), "items.completed_at", nullable=True),
            "deleted_at": _as_datetime(row.get("deleted_at"), "items.deleted_at", nullable=True),
        }))

    simple_specs = [
        ("checklist_items", "checklist_items", lambda row: {
            "id": _require_id(row["id"], "checklist_items.id"),
            "task_id": _require_id(row["item_id"], "checklist_items.item_id"),
            "title": str(row["title"]),
            "is_done": _as_bool(row.get("is_done", 0), "checklist_items.is_done"),
            "sort_order": int(row.get("sort_order", 0)),
            "created_at": _as_datetime(row["created_at"], "checklist_items.created_at"),
        }),
        ("notes", "notes", lambda row: {
            "id": _require_id(row["id"], "notes.id"),
            "title": row.get("title"),
            "body": row.get("body"),
            "project_id": _nullable_id(row.get("project_id"), "notes.project_id"),
            "created_at": _as_datetime(row["created_at"], "notes.created_at"),
            "updated_at": _as_datetime(row["updated_at"], "notes.updated_at"),
        }),
        ("habits", "habits", lambda row: {
            "id": _require_id(row["id"], "habits.id"),
            "title": str(row["title"]),
            "recurrence_rule": str(row["recurrence_rule"]),
            "reminder_time": row.get("reminder_time"),
            "is_active": _as_bool(row.get("is_active", 1), "habits.is_active"),
            "created_at": _as_datetime(row["created_at"], "habits.created_at"),
        }),
        ("habit_logs", "habit_completions", lambda row: {
            "id": _require_id(row["id"], "habit_logs.id"),
            "habit_id": _require_id(row["habit_id"], "habit_logs.habit_id"),
            "completed_at": _as_datetime(row["completed_at"], "habit_logs.completed_at"),
        }),
        ("shopping_lists", "shopping_lists", lambda row: {
            "id": _require_id(row["id"], "shopping_lists.id"),
            "name": str(row["name"]),
            "project_id": _nullable_id(row.get("project_id"), "shopping_lists.project_id"),
            "created_at": _as_datetime(row["created_at"], "shopping_lists.created_at"),
        }),
        ("shopping_items", "shopping_items", lambda row: {
            "id": _require_id(row["id"], "shopping_items.id"),
            "list_id": _require_id(row["list_id"], "shopping_items.list_id"),
            "name": str(row["name"]),
            "category": row.get("category"),
            "is_done": _as_bool(row.get("is_done", 0), "shopping_items.is_done"),
            "sort_order": int(row.get("sort_order", 0)),
        }),
        ("tags", "tags", lambda row: {
            "id": _require_id(row["id"], "tags.id"),
            "name": str(row["name"]),
        }),
        ("reminders", "reminders", lambda row: {
            "id": _require_id(row["id"], "reminders.id"),
            "entity_type": str(row["entity_type"]),
            "entity_id": _require_id(row["entity_id"], "reminders.entity_id"),
            "scheduled_at": _as_datetime(row["scheduled_at"], "reminders.scheduled_at"),
            "type": str(row.get("type") or "notification"),
            "is_enabled": _as_bool(row.get("is_enabled", 1), "reminders.is_enabled"),
        }),
        ("templates", "templates", lambda row: {
            "id": _require_id(row["id"], "templates.id"),
            "name": str(row["name"]),
            "template_type": str(row["template_type"]),
            "payload_json": str(row["payload_json"]),
            "created_at": _as_datetime(row["created_at"], "templates.created_at"),
            "updated_at": _as_datetime(row["updated_at"], "templates.updated_at"),
        }),
        ("attachments", "legacy_attachments", lambda row: {
            "id": _require_id(row["id"], "attachments.id"),
            "entity_type": str(row["entity_type"]),
            "entity_id": _require_id(row["entity_id"], "attachments.entity_id"),
            "display_name": str(row["display_name"]),
            "source_local_path": str(row["local_path"]),
            "mime_type": row.get("mime_type"),
            "created_at": _as_datetime(row["created_at"], "attachments.created_at"),
        }),
        ("calendar_events_cache", "calendar_event_refs", lambda row: {
            "id": _require_id(row["id"], "calendar_events_cache.id"),
            "google_event_id": str(row["google_event_id"]),
            "calendar_id": str(row["calendar_id"]),
            "title": str(row["title"]),
            "starts_at": _as_datetime(row["starts_at"], "calendar_events_cache.starts_at"),
            "ends_at": _as_datetime(row["ends_at"], "calendar_events_cache.ends_at"),
            "location": row.get("location"),
            "description": row.get("description"),
            "project_id": _nullable_id(row.get("project_id"), "calendar_events_cache.project_id"),
            "last_synced_at": _as_datetime(row["last_synced_at"], "calendar_events_cache.last_synced_at"),
        }),
        ("gmail_refs", "gmail_refs", lambda row: {
            "id": _require_id(row["id"], "gmail_refs.id"),
            "gmail_message_id": str(row["gmail_message_id"]),
            "thread_id": str(row["thread_id"]),
            "subject": str(row["subject"]),
            "sender": str(row["sender"]),
            "received_at": _as_datetime(row["received_at"], "gmail_refs.received_at"),
            "snippet": row.get("snippet"),
            "linked_entity_type": row.get("linked_entity_type"),
            "linked_entity_id": _nullable_id(row.get("linked_entity_id"), "gmail_refs.linked_entity_id"),
            "last_synced_at": _as_datetime(row["last_synced_at"], "gmail_refs.last_synced_at"),
        }),
        ("activity_logs", "legacy_activity_logs", lambda row: {
            "id": _require_id(row["id"], "activity_logs.id"),
            "action_type": str(row["action_type"]),
            "entity_type": row.get("entity_type"),
            "entity_id": _nullable_id(row.get("entity_id"), "activity_logs.entity_id"),
            "summary": str(row["summary"]),
            "result": str(row.get("result") or "success"),
            "created_at": _as_datetime(row["created_at"], "activity_logs.created_at"),
        }),
    ]

    for source_table, target_table, transform in simple_specs:
        for row in _table(bundle, source_table):
            values = transform(row)
            key_columns = SOURCE_TABLE_KEYS[source_table]
            if source_table == "habit_logs":
                target_key = {"id": values["id"]}
            elif source_table == "calendar_events_cache" or source_table == "gmail_refs":
                target_key = {"id": values["id"]}
            else:
                target_key = {column if column != "item_id" else "task_id": values.get(column if column != "item_id" else "task_id") for column in key_columns}
                if "id" in values:
                    target_key = {"id": values["id"]}
            items.append(_make_item(source_table, row, target_table, target_key, values))

    for row in _table(bundle, "note_links"):
        values = {
            "source_note_id": _require_id(row["source_note_id"], "note_links.source_note_id"),
            "target_note_id": _require_id(row["target_note_id"], "note_links.target_note_id"),
        }
        items.append(_make_item("note_links", row, "note_links", values, values))

    for row in _table(bundle, "entity_tags"):
        values = {
            "entity_type": str(row["entity_type"]),
            "entity_id": _require_id(row["entity_id"], "entity_tags.entity_id"),
            "tag_id": _require_id(row["tag_id"], "entity_tags.tag_id"),
        }
        items.append(_make_item("entity_tags", row, "entity_tags", values, values))

    for source_table in ("preferences", "bridge_state"):
        for row in _table(bundle, source_table):
            values = {
                "source_table": source_table,
                "key": str(row["key"]),
                "value_json": str(row["value_json"]),
            }
            target_key = {"source_table": source_table, "key": values["key"]}
            items.append(_make_item(source_table, row, "legacy_key_value_state", target_key, values))

    return items


def _where_clause(key: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    params: dict[str, Any] = {}
    for index, (column, value) in enumerate(key.items()):
        param = f"key_{index}"
        parts.append(f'"{column}" = :{param}')
        params[param] = value
    return " AND ".join(parts), params


async def _target_exists(conn: AsyncConnection, item: MigrationItem) -> bool:
    where, params = _where_clause(item.target_key)
    return bool(await conn.scalar(text(f'SELECT EXISTS(SELECT 1 FROM "{item.target_table}" WHERE {where})'), params))


async def _insert_target(conn: AsyncConnection, item: MigrationItem) -> None:
    columns = list(item.values)
    names = ", ".join(f'"{column}"' for column in columns)
    params = ", ".join(f':v_{index}' for index in range(len(columns)))
    values = {f"v_{index}": item.values[column] for index, column in enumerate(columns)}
    await conn.execute(text(f'INSERT INTO "{item.target_table}" ({names}) VALUES ({params})'), values)


async def import_bundle(bundle: dict[str, Any], *, user_sub: str, database_url: str | None = None) -> dict[str, Any]:
    if not user_sub.strip():
        raise BundleValidationError("user_sub is required for migration audit")
    fingerprint = str(bundle["source_fingerprint"])
    migration_items = build_migration_items(bundle)
    engine = create_async_engine(database_url or settings.database_url, pool_pre_ping=True)
    inserted = 0
    skipped = 0
    try:
        async with engine.begin() as conn:
            for item in migration_items:
                ledger = (
                    await conn.execute(
                        text(
                            "SELECT row_sha256, target_table, target_key FROM legacy_migration_rows "
                            "WHERE source_fingerprint=:fingerprint AND source_table=:source_table "
                            "AND source_key=:source_key"
                        ),
                        {
                            "fingerprint": fingerprint,
                            "source_table": item.source_table,
                            "source_key": item.source_key,
                        },
                    )
                ).mappings().first()
                target_key_json = json.dumps(item.target_key, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                if ledger is not None:
                    if (
                        ledger["row_sha256"] != item.row_sha256
                        or ledger["target_table"] != item.target_table
                        or ledger["target_key"] != target_key_json
                    ):
                        raise RerunDriftError(f"migration ledger drift for {item.source_table}:{item.source_key}")
                    if not await _target_exists(conn, item):
                        raise RerunDriftError(f"migrated target row disappeared for {item.source_table}:{item.source_key}")
                    skipped += 1
                    continue

                if await _target_exists(conn, item):
                    raise TargetCollisionError(
                        f"target collision for {item.target_table}:{target_key_json}"
                    )
                await _insert_target(conn, item)
                await conn.execute(
                    text(
                        "INSERT INTO legacy_migration_rows "
                        "(source_fingerprint, source_table, source_key, row_sha256, target_table, target_key) "
                        "VALUES (:fingerprint, :source_table, :source_key, :row_sha256, :target_table, :target_key)"
                    ),
                    {
                        "fingerprint": fingerprint,
                        "source_table": item.source_table,
                        "source_key": item.source_key,
                        "row_sha256": item.row_sha256,
                        "target_table": item.target_table,
                        "target_key": target_key_json,
                    },
                )
                inserted += 1

        status = "success"
        summary = {
            "status": status,
            "source_fingerprint": fingerprint,
            "source_rows": len(migration_items),
            "inserted": inserted,
            "idempotent_skips": skipped,
            "local_only_state_counts": bundle.get("local_only_state_counts", {}),
        }
        await _record_execution(engine, user_sub=user_sub, status="success", result="migrated", summary=summary)
        return summary
    except Exception as exc:
        try:
            await _record_execution(
                engine,
                user_sub=user_sub,
                status="failure",
                result="failed",
                summary={"error_category": type(exc).__name__},
            )
        except Exception:
            pass
        raise
    finally:
        await engine.dispose()


async def _record_execution(
    engine,
    *,
    user_sub: str,
    status: str,
    result: str,
    summary: dict[str, Any],
) -> None:
    # Only counts/categories/fingerprint are recorded; source row contents are excluded.
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO execution_logs "
                "(id, request_id, user_sub, action_type, provider, status, result, summary, started_at, finished_at) "
                "VALUES (:id, :request_id, :user_sub, 'migration.sqlite_postgres', 'legacy_sqlite', "
                ":status, :result, :summary, now(), now())"
            ),
            {
                "id": str(uuid.uuid4()),
                "request_id": f"sqlite-backfill-{uuid.uuid4()}",
                "user_sub": user_sub,
                "status": status,
                "result": result,
                "summary": json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            },
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export")
    export.add_argument("--sqlite", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--bundle", required=True, type=Path)

    importer = subparsers.add_parser("import")
    importer.add_argument("--bundle", required=True, type=Path)
    importer.add_argument("--user-sub", required=True)
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    if args.command == "export":
        bundle = write_bundle(args.sqlite, args.output)
        print(f"source_fingerprint={bundle['source_fingerprint']}")
        print("export_status=success")
        return 0
    if args.command == "validate":
        bundle = load_bundle(args.bundle)
        items = build_migration_items(bundle)
        print(f"source_fingerprint={bundle['source_fingerprint']}")
        print(f"migration_rows={len(items)}")
        print("validation_status=success")
        return 0
    if args.command == "import":
        bundle = load_bundle(args.bundle)
        result = await import_bundle(bundle, user_sub=args.user_sub)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    raise AssertionError(args.command)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())

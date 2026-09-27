#!/usr/bin/env python3
"""Synthetic dev-test acceptance for the SQLite -> PostgreSQL backfill pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sqlite3
import tempfile
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from scripts.sqlite_postgres_backfill import export_bundle, import_bundle

ACCEPTANCE_LABEL = "[ACCEPTANCE TEST] SQLite backfill"


def _create_fixture(path: Path, ids: dict[str, str]) -> None:
    now = 1_790_000_000
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            PRAGMA user_version = 3;
            CREATE TABLE projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, summary TEXT, status TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE items(id TEXT PRIMARY KEY, title TEXT NOT NULL, note TEXT, status TEXT NOT NULL, priority TEXT NOT NULL, due_at INTEGER, reminder_at INTEGER, project_id TEXT, source_type TEXT, source_ref TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, completed_at INTEGER, deleted_at INTEGER);
            CREATE TABLE checklist_items(id TEXT PRIMARY KEY, item_id TEXT NOT NULL, title TEXT NOT NULL, is_done INTEGER NOT NULL, sort_order INTEGER NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE notes(id TEXT PRIMARY KEY, title TEXT, body TEXT, project_id TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE note_links(source_note_id TEXT NOT NULL, target_note_id TEXT NOT NULL, PRIMARY KEY(source_note_id,target_note_id));
            CREATE TABLE habits(id TEXT PRIMARY KEY, title TEXT NOT NULL, recurrence_rule TEXT NOT NULL, reminder_time TEXT, is_active INTEGER NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE habit_logs(id TEXT PRIMARY KEY, habit_id TEXT NOT NULL, completed_at INTEGER NOT NULL);
            CREATE TABLE shopping_lists(id TEXT PRIMARY KEY, name TEXT NOT NULL, project_id TEXT, created_at INTEGER NOT NULL);
            CREATE TABLE shopping_items(id TEXT PRIMARY KEY, list_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT, is_done INTEGER NOT NULL, sort_order INTEGER NOT NULL);
            CREATE TABLE tags(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
            CREATE TABLE entity_tags(entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, tag_id TEXT NOT NULL, PRIMARY KEY(entity_type,entity_id,tag_id));
            CREATE TABLE reminders(id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, scheduled_at INTEGER NOT NULL, type TEXT NOT NULL, is_enabled INTEGER NOT NULL);
            CREATE TABLE templates(id TEXT PRIMARY KEY, name TEXT NOT NULL, template_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE attachments(id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, display_name TEXT NOT NULL, local_path TEXT NOT NULL, mime_type TEXT, created_at INTEGER NOT NULL);
            CREATE TABLE calendar_events_cache(id TEXT PRIMARY KEY, google_event_id TEXT NOT NULL UNIQUE, calendar_id TEXT NOT NULL, title TEXT NOT NULL, starts_at INTEGER NOT NULL, ends_at INTEGER NOT NULL, location TEXT, description TEXT, project_id TEXT, last_synced_at INTEGER NOT NULL);
            CREATE TABLE gmail_refs(id TEXT PRIMARY KEY, gmail_message_id TEXT NOT NULL UNIQUE, thread_id TEXT NOT NULL, subject TEXT NOT NULL, sender TEXT NOT NULL, received_at INTEGER NOT NULL, snippet TEXT, linked_entity_type TEXT, linked_entity_id TEXT, last_synced_at INTEGER NOT NULL);
            CREATE TABLE activity_logs(id TEXT PRIMARY KEY, action_type TEXT NOT NULL, entity_type TEXT, entity_id TEXT, summary TEXT NOT NULL, result TEXT NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE preferences(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
            CREATE TABLE bridge_state(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
            CREATE TABLE sync_pairs(id TEXT PRIMARY KEY);
            CREATE TABLE sync_files(id TEXT PRIMARY KEY);
            CREATE TABLE sync_operations(id TEXT PRIMARY KEY);
            CREATE TABLE bridge_executions(request_id TEXT NOT NULL, action_id TEXT NOT NULL, PRIMARY KEY(request_id,action_id));
            """
        )
        project = ids["project"]
        connection.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)", (project, ACCEPTANCE_LABEL, "fixture", "active", now, now + 1))
        connection.execute(
            "INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ids["task"], ACCEPTANCE_LABEL, "history", "scheduled", "high", now + 3600, now + 1800, project, "legacy_test", "source-1", now, now + 2, None, None),
        )
        connection.execute("INSERT INTO checklist_items VALUES (?,?,?,?,?,?)", (ids["checklist"], ids["task"], "verify", 1, 3, now))
        connection.execute("INSERT INTO notes VALUES (?,?,?,?,?,?)", (ids["note_a"], "A", "body-a", project, now, now + 1))
        connection.execute("INSERT INTO notes VALUES (?,?,?,?,?,?)", (ids["note_b"], "B", "body-b", project, now, now + 1))
        connection.execute("INSERT INTO note_links VALUES (?,?)", (ids["note_a"], ids["note_b"]))
        connection.execute("INSERT INTO habits VALUES (?,?,?,?,?,?)", (ids["habit"], ACCEPTANCE_LABEL, "daily", "08:00", 1, now))
        connection.execute("INSERT INTO habit_logs VALUES (?,?,?)", (ids["habit_log"], ids["habit"], now + 60))
        connection.execute("INSERT INTO shopping_lists VALUES (?,?,?,?)", (ids["shopping_list"], ACCEPTANCE_LABEL, project, now))
        connection.execute("INSERT INTO shopping_items VALUES (?,?,?,?,?,?)", (ids["shopping_item"], ids["shopping_list"], "milk", "food", 1, 4))
        connection.execute("INSERT INTO tags VALUES (?,?)", (ids["tag"], f"{ACCEPTANCE_LABEL}-{ids['tag'][:8]}"))
        connection.execute("INSERT INTO entity_tags VALUES (?,?,?)", ("task", ids["task"], ids["tag"]))
        connection.execute("INSERT INTO reminders VALUES (?,?,?,?,?,?)", (ids["reminder"], "task", ids["task"], now + 1800, "notification", 1))
        connection.execute("INSERT INTO templates VALUES (?,?,?,?,?,?)", (ids["template"], ACCEPTANCE_LABEL, "task", '{"opaque":true}', now, now + 1))
        connection.execute("INSERT INTO attachments VALUES (?,?,?,?,?,?,?)", (ids["attachment"], "note", ids["note_a"], "fixture.txt", "/legacy/device/fixture.txt", "text/plain", now))
        connection.execute("INSERT INTO calendar_events_cache VALUES (?,?,?,?,?,?,?,?,?,?)", (ids["calendar_ref"], f"google-{ids['calendar_ref']}", "primary", ACCEPTANCE_LABEL, now, now + 3600, None, None, project, now + 5))
        connection.execute("INSERT INTO gmail_refs VALUES (?,?,?,?,?,?,?,?,?,?)", (ids["gmail_ref"], f"gmail-{ids['gmail_ref']}", "thread-1", ACCEPTANCE_LABEL, "acceptance@example.invalid", now, "snippet", "project", project, now + 5))
        connection.execute("INSERT INTO activity_logs VALUES (?,?,?,?,?,?,?)", (ids["activity"], "create_task", "task", ids["task"], ACCEPTANCE_LABEL, "success", now))
        connection.execute("INSERT INTO preferences VALUES (?,?)", (f"pref-{ids['task']}", "true"))
        connection.execute("INSERT INTO bridge_state VALUES (?,?)", (f"bridge-{ids['task']}", "PA-TEST"))
        connection.commit()
    finally:
        connection.close()


async def _verify(ids: dict[str, str], fingerprint: str, user_sub: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            task = (
                await conn.execute(
                    text("SELECT status, priority, source_type, source_ref, deleted_at FROM tasks WHERE id=:id"),
                    {"id": ids["task"]},
                )
            ).mappings().one()
            assert task["status"] == "scheduled"
            assert task["priority"] == "high"
            assert task["source_type"] == "legacy_test"
            assert task["source_ref"] == "source-1"
            assert task["deleted_at"] is None
            assert await conn.scalar(text("SELECT count(*) FROM checklist_items WHERE task_id=:id"), {"id": ids["task"]}) == 1
            assert await conn.scalar(text("SELECT count(*) FROM note_links WHERE source_note_id=:id"), {"id": ids["note_a"]}) == 1
            assert await conn.scalar(text("SELECT count(*) FROM habit_completions WHERE habit_id=:id"), {"id": ids["habit"]}) == 1
            assert await conn.scalar(text("SELECT is_done FROM shopping_items WHERE id=:id"), {"id": ids["shopping_item"]}) is True
            assert await conn.scalar(text("SELECT count(*) FROM entity_tags WHERE tag_id=:id"), {"id": ids["tag"]}) == 1
            assert await conn.scalar(text("SELECT source_local_path FROM legacy_attachments WHERE id=:id"), {"id": ids["attachment"]}) == "/legacy/device/fixture.txt"
            assert await conn.scalar(text("SELECT payload_json FROM templates WHERE id=:id"), {"id": ids["template"]}) == '{"opaque":true}'
            assert await conn.scalar(text("SELECT count(*) FROM legacy_migration_rows WHERE source_fingerprint=:fp"), {"fp": fingerprint}) > 0
            assert await conn.scalar(text("SELECT count(*) FROM execution_logs WHERE user_sub=:user_sub AND action_type='migration.sqlite_postgres' AND status='success'"), {"user_sub": user_sub}) >= 2
    finally:
        await engine.dispose()


async def _cleanup(ids: dict[str, str], fingerprint: str, user_sub: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM legacy_migration_rows WHERE source_fingerprint=:fp"), {"fp": fingerprint})
            await conn.execute(text("DELETE FROM execution_logs WHERE user_sub=:user_sub AND action_type='migration.sqlite_postgres'"), {"user_sub": user_sub})
            await conn.execute(text("DELETE FROM entity_tags WHERE entity_id=:id OR tag_id=:tag"), {"id": ids["task"], "tag": ids["tag"]})
            await conn.execute(text("DELETE FROM checklist_items WHERE id=:id"), {"id": ids["checklist"]})
            await conn.execute(text("DELETE FROM note_links WHERE source_note_id IN (:a,:b) OR target_note_id IN (:a,:b)"), {"a": ids["note_a"], "b": ids["note_b"]})
            await conn.execute(text("DELETE FROM habit_completions WHERE id=:id"), {"id": ids["habit_log"]})
            await conn.execute(text("DELETE FROM shopping_items WHERE id=:id"), {"id": ids["shopping_item"]})
            await conn.execute(text("DELETE FROM reminders WHERE id=:id"), {"id": ids["reminder"]})
            await conn.execute(text("DELETE FROM legacy_attachments WHERE id=:id"), {"id": ids["attachment"]})
            await conn.execute(text("DELETE FROM calendar_event_refs WHERE id=:id"), {"id": ids["calendar_ref"]})
            await conn.execute(text("DELETE FROM gmail_refs WHERE id=:id"), {"id": ids["gmail_ref"]})
            await conn.execute(text("DELETE FROM legacy_activity_logs WHERE id=:id"), {"id": ids["activity"]})
            await conn.execute(text("DELETE FROM legacy_key_value_state WHERE key IN (:pref,:bridge)"), {"pref": f"pref-{ids['task']}", "bridge": f"bridge-{ids['task']}"})
            await conn.execute(text("DELETE FROM templates WHERE id=:id"), {"id": ids["template"]})
            await conn.execute(text("DELETE FROM shopping_lists WHERE id=:id"), {"id": ids["shopping_list"]})
            await conn.execute(text("DELETE FROM habits WHERE id=:id"), {"id": ids["habit"]})
            await conn.execute(text("DELETE FROM notes WHERE id IN (:a,:b)"), {"a": ids["note_a"], "b": ids["note_b"]})
            await conn.execute(text("DELETE FROM tasks WHERE id=:id"), {"id": ids["task"]})
            await conn.execute(text("DELETE FROM tags WHERE id=:id"), {"id": ids["tag"]})
            await conn.execute(text("DELETE FROM projects WHERE id=:id"), {"id": ids["project"]})
        async with engine.connect() as conn:
            remaining = 0
            for table, key in (
                ("tasks", ids["task"]),
                ("projects", ids["project"]),
                ("notes", ids["note_a"]),
                ("habits", ids["habit"]),
                ("shopping_lists", ids["shopping_list"]),
                ("templates", ids["template"]),
            ):
                remaining += int(await conn.scalar(text(f'SELECT count(*) FROM "{table}" WHERE id=:id'), {"id": key}) or 0)
            assert remaining == 0
    finally:
        await engine.dispose()


async def main() -> None:
    ids = {name: str(uuid.uuid4()) for name in (
        "project", "task", "checklist", "note_a", "note_b", "habit", "habit_log",
        "shopping_list", "shopping_item", "tag", "reminder", "template", "attachment",
        "calendar_ref", "gmail_ref", "activity",
    )}
    user_sub = f"acceptance-sqlite-backfill-{uuid.uuid4()}"
    fingerprint = ""
    with tempfile.TemporaryDirectory(prefix="life-assistant-sqlite-backfill-") as tmp:
        sqlite_path = Path(tmp) / "life_assistant.db"
        _create_fixture(sqlite_path, ids)
        first = export_bundle(sqlite_path)
        second = export_bundle(sqlite_path)
        assert first == second
        fingerprint = first["source_fingerprint"]
        try:
            initial = await import_bundle(first, user_sub=user_sub)
            rerun = await import_bundle(second, user_sub=user_sub)
            assert initial["inserted"] == initial["source_rows"]
            assert initial["idempotent_skips"] == 0
            assert rerun["inserted"] == 0
            assert rerun["idempotent_skips"] == rerun["source_rows"]
            await _verify(ids, fingerprint, user_sub)
            print(f"sqlite_backfill_acceptance_fingerprint={fingerprint}")
            print(f"sqlite_backfill_acceptance_rows={initial['source_rows']}")
            print("sqlite_backfill_acceptance=PASS")
        finally:
            if fingerprint:
                await _cleanup(ids, fingerprint, user_sub)
                print("sqlite_backfill_acceptance_cleanup=PASS")


if __name__ == "__main__":
    asyncio.run(main())

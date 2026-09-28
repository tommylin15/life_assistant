#!/usr/bin/env python3
"""Run authenticated cloud-domain parity acceptance against the dev-test database.

The runner exercises the real FastAPI routes and real PostgreSQL sessions from the
exact deployed image. It replaces only the Google identity dependency with a
fixed acceptance identity so no personal OAuth token is required or exposed.
All business artifacts are tagged with [ACCEPTANCE TEST], tracked by exact IDs,
and removed through exact-ID cleanup in a finally path.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import sys
import uuid

import httpx
from sqlalchemy import delete, or_, select

from app.api.auth import current_user
from app.db.session import SessionLocal
from app.main import app
from app.models.habit import Habit, HabitCompletion
from app.models.note import Note, NoteLink
from app.models.project import Project
from app.models.shopping import ShoppingItem, ShoppingList
from app.models.template import Template


ACCEPTANCE_USER_SUB = "acceptance-cloud-domain-parity"
ACCEPTANCE_USER = {
    "sub": ACCEPTANCE_USER_SUB,
    "email": "cloud-domain-acceptance@example.invalid",
    "name": "Cloud Domain Parity Acceptance",
}

LAST_PASSED_CHECK = "bootstrap"
FAILURE_EXIT_CODES = {
    "bootstrap": 41,
    "project_delete_guard_note": 42,
    "note_crud_link_persistence": 43,
    "project_delete_guard_shopping": 44,
    "shopping_nested_persistence": 45,
    "habit_append_history_persistence": 46,
    "template_opaque_payload_persistence": 47,
    "project_delete_after_unlink": 48,
    "execution_log": 49,
}


@dataclass
class AcceptanceArtifacts:
    project_ids: set[str] = field(default_factory=set)
    note_ids: set[str] = field(default_factory=set)
    habit_ids: set[str] = field(default_factory=set)
    habit_completion_ids: set[str] = field(default_factory=set)
    shopping_list_ids: set[str] = field(default_factory=set)
    shopping_item_ids: set[str] = field(default_factory=set)
    template_ids: set[str] = field(default_factory=set)


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _expect(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        body = response.text[:500]
        raise AssertionError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: {body}"
        )


def _json(response: httpx.Response, label: str) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: response was not JSON") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{label}: expected JSON object")
    return payload


def _record(check: str) -> None:
    global LAST_PASSED_CHECK
    LAST_PASSED_CHECK = check
    print(f"acceptance_check={check}:PASS", flush=True)


async def cleanup_exact_artifacts(artifacts: AcceptanceArtifacts) -> None:
    """Delete only IDs created by this acceptance run, in FK-safe order."""

    async with SessionLocal() as db:
        if artifacts.note_ids:
            note_ids = tuple(artifacts.note_ids)
            await db.execute(
                delete(NoteLink).where(
                    or_(
                        NoteLink.source_note_id.in_(note_ids),
                        NoteLink.target_note_id.in_(note_ids),
                    )
                )
            )
            await db.execute(delete(Note).where(Note.id.in_(note_ids)))

        if artifacts.habit_completion_ids:
            await db.execute(
                delete(HabitCompletion).where(
                    HabitCompletion.id.in_(tuple(artifacts.habit_completion_ids))
                )
            )
        if artifacts.habit_ids:
            await db.execute(
                delete(Habit).where(Habit.id.in_(tuple(artifacts.habit_ids)))
            )

        if artifacts.shopping_item_ids:
            await db.execute(
                delete(ShoppingItem).where(
                    ShoppingItem.id.in_(tuple(artifacts.shopping_item_ids))
                )
            )
        if artifacts.shopping_list_ids:
            await db.execute(
                delete(ShoppingList).where(
                    ShoppingList.id.in_(tuple(artifacts.shopping_list_ids))
                )
            )

        if artifacts.template_ids:
            await db.execute(
                delete(Template).where(Template.id.in_(tuple(artifacts.template_ids)))
            )
        if artifacts.project_ids:
            await db.execute(
                delete(Project).where(Project.id.in_(tuple(artifacts.project_ids)))
            )
        await db.commit()

    await _verify_cleanup(artifacts)


async def _verify_cleanup(artifacts: AcceptanceArtifacts) -> None:
    async with SessionLocal() as db:
        checks = (
            (Project, artifacts.project_ids, "project"),
            (Note, artifacts.note_ids, "note"),
            (Habit, artifacts.habit_ids, "habit"),
            (HabitCompletion, artifacts.habit_completion_ids, "habit_completion"),
            (ShoppingList, artifacts.shopping_list_ids, "shopping_list"),
            (ShoppingItem, artifacts.shopping_item_ids, "shopping_item"),
            (Template, artifacts.template_ids, "template"),
        )
        for model, ids, label in checks:
            if not ids:
                continue
            result = await db.execute(select(model).where(model.id.in_(tuple(ids))))
            if result.scalars().first() is not None:
                raise AssertionError(f"cleanup left acceptance {label} rows behind")


async def _delete_shopping_exact(artifacts: AcceptanceArtifacts) -> None:
    """Remove shopping rows early so Project delete guard can be re-tested cleanly."""

    async with SessionLocal() as db:
        if artifacts.shopping_item_ids:
            await db.execute(
                delete(ShoppingItem).where(
                    ShoppingItem.id.in_(tuple(artifacts.shopping_item_ids))
                )
            )
        if artifacts.shopping_list_ids:
            await db.execute(
                delete(ShoppingList).where(
                    ShoppingList.id.in_(tuple(artifacts.shopping_list_ids))
                )
            )
        await db.commit()


async def run_acceptance() -> None:
    artifacts = AcceptanceArtifacts()
    label = f"[ACCEPTANCE TEST] cloud-domain-parity {uuid.uuid4()}"
    expected_activity: set[tuple[str, str]] = set()
    primary_error: BaseException | None = None

    app.dependency_overrides[current_user] = _acceptance_user
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://acceptance.local",
            timeout=30.0,
        ) as client:
            # Project + linked Note delete guard.
            response = await client.post(
                "/api/v1/projects",
                json={"name": f"{label} Project", "summary": label, "status": "active"},
            )
            _expect(response, 201, "project create")
            project_id = _json(response, "project create")["id"]
            artifacts.project_ids.add(project_id)
            expected_activity.add(("project.create", project_id))

            response = await client.post(
                "/api/v1/notes",
                json={"title": f"{label} Note A", "body": "first", "project_id": project_id},
            )
            _expect(response, 201, "note A create")
            note_a = _json(response, "note A create")["id"]
            artifacts.note_ids.add(note_a)
            expected_activity.add(("note.create", note_a))

            response = await client.delete(f"/api/v1/projects/{project_id}")
            _expect(response, 409, "project linked-note delete guard")
            _record("project_delete_guard_note")

            response = await client.patch(
                f"/api/v1/notes/{note_a}",
                json={
                    "title": f"{label} Note A Updated",
                    "body": "updated-body",
                    "project_id": None,
                },
            )
            _expect(response, 200, "note A update")
            expected_activity.add(("note.update", note_a))

            response = await client.get(f"/api/v1/notes/{note_a}")
            _expect(response, 200, "note A reread")
            note_payload = _json(response, "note A reread")
            if (
                note_payload.get("title") != f"{label} Note A Updated"
                or note_payload.get("body") != "updated-body"
                or note_payload.get("project_id") is not None
            ):
                raise AssertionError("note A reread did not persist update")

            response = await client.post(
                "/api/v1/notes",
                json={"title": f"{label} Note B", "body": "second", "project_id": None},
            )
            _expect(response, 201, "note B create")
            note_b = _json(response, "note B create")["id"]
            artifacts.note_ids.add(note_b)
            expected_activity.add(("note.create", note_b))

            response = await client.post(
                f"/api/v1/notes/{note_a}/links",
                json={"target_note_id": note_b},
            )
            _expect(response, 204, "note link")
            expected_activity.add(("note.link", note_a))

            response = await client.get(f"/api/v1/notes/{note_a}/links")
            _expect(response, 200, "note linked reread")
            linked_ids = {str(item["id"]) for item in response.json()}
            if note_b not in linked_ids:
                raise AssertionError("linked note was not visible on reread")
            _record("note_crud_link_persistence")

            # Shopping + linked ShoppingList delete guard.
            response = await client.post(
                "/api/v1/shopping-lists",
                json={"name": f"{label} Shopping", "project_id": project_id},
            )
            _expect(response, 201, "shopping list create")
            shopping_list_id = _json(response, "shopping list create")["id"]
            artifacts.shopping_list_ids.add(shopping_list_id)
            expected_activity.add(("shopping_list.create", shopping_list_id))

            response = await client.delete(f"/api/v1/projects/{project_id}")
            _expect(response, 409, "project linked-shopping delete guard")
            _record("project_delete_guard_shopping")

            response = await client.post(
                f"/api/v1/shopping-lists/{shopping_list_id}/items",
                json={"name": f"{label} Item", "category": "acceptance"},
            )
            _expect(response, 201, "shopping item create")
            shopping_item_id = _json(response, "shopping item create")["id"]
            artifacts.shopping_item_ids.add(shopping_item_id)
            expected_activity.add(("shopping_item.create", shopping_item_id))

            response = await client.patch(
                f"/api/v1/shopping-items/{shopping_item_id}",
                json={"is_done": True},
            )
            _expect(response, 200, "shopping item toggle")
            if _json(response, "shopping item toggle").get("is_done") is not True:
                raise AssertionError("shopping item toggle response mismatch")
            expected_activity.add(("shopping_item.toggle", shopping_item_id))

            response = await client.get(f"/api/v1/shopping-lists/{shopping_list_id}")
            _expect(response, 200, "shopping list nested reread")
            shopping_payload = _json(response, "shopping list nested reread")
            items = shopping_payload.get("items") or []
            matching = [item for item in items if item.get("id") == shopping_item_id]
            if len(matching) != 1 or matching[0].get("is_done") is not True:
                raise AssertionError("shopping nested reread did not persist toggled item")
            _record("shopping_nested_persistence")

            # Habit create/update/two completions/history.
            response = await client.post(
                "/api/v1/habits",
                json={
                    "title": f"{label} Habit",
                    "recurrence_rule": "FREQ=DAILY",
                    "reminder_time": "08:00",
                },
            )
            _expect(response, 201, "habit create")
            habit_id = _json(response, "habit create")["id"]
            artifacts.habit_ids.add(habit_id)
            expected_activity.add(("habit.create", habit_id))

            response = await client.patch(
                f"/api/v1/habits/{habit_id}",
                json={"title": f"{label} Habit Updated", "reminder_time": "09:30"},
            )
            _expect(response, 200, "habit update")
            expected_activity.add(("habit.update", habit_id))

            completion_ids: list[str] = []
            for index in (1, 2):
                response = await client.post(f"/api/v1/habits/{habit_id}/complete")
                _expect(response, 201, f"habit completion {index}")
                completion_id = _json(response, f"habit completion {index}")["id"]
                completion_ids.append(completion_id)
                artifacts.habit_completion_ids.add(completion_id)
            if completion_ids[0] == completion_ids[1]:
                raise AssertionError("habit completion rows were not append-only")
            expected_activity.add(("habit.complete", habit_id))

            response = await client.get(f"/api/v1/habits/{habit_id}/completions")
            _expect(response, 200, "habit completion history")
            history = response.json()
            history_ids = [str(item["id"]) for item in history]
            if not set(completion_ids).issubset(set(history_ids)):
                raise AssertionError("habit completion history missing acceptance rows")
            _record("habit_append_history_persistence")

            # Template opaque payload exact round-trip.
            initial_payload = '{"z":1,"a":[3,2,1]}'
            updated_payload = ' { "b": 2, "a": [1, 2, 3] } '
            response = await client.post(
                "/api/v1/templates",
                json={
                    "name": f"{label} Template",
                    "template_type": "acceptance",
                    "payload_json": initial_payload,
                },
            )
            _expect(response, 201, "template create")
            template_id = _json(response, "template create")["id"]
            artifacts.template_ids.add(template_id)
            expected_activity.add(("template.create", template_id))

            response = await client.patch(
                f"/api/v1/templates/{template_id}",
                json={"payload_json": updated_payload},
            )
            _expect(response, 200, "template update")
            if _json(response, "template update").get("payload_json") != updated_payload:
                raise AssertionError("template update changed opaque payload string")
            expected_activity.add(("template.update", template_id))

            response = await client.get(f"/api/v1/templates/{template_id}")
            _expect(response, 200, "template reread")
            if _json(response, "template reread").get("payload_json") != updated_payload:
                raise AssertionError("template reread changed opaque payload string")
            _record("template_opaque_payload_persistence")

            # Notes have API delete; use it so delete behavior is also exercised.
            for note_id in (note_a, note_b):
                response = await client.delete(f"/api/v1/notes/{note_id}")
                _expect(response, 204, f"note delete {note_id}")
                expected_activity.add(("note.delete", note_id))

            # Shopping intentionally has no delete API. Remove only this run's exact
            # IDs before verifying Project can finally be deleted.
            await _delete_shopping_exact(artifacts)
            response = await client.delete(f"/api/v1/projects/{project_id}")
            _expect(response, 204, "project delete after linked rows removed")
            expected_activity.add(("project.delete", project_id))
            _record("project_delete_after_unlink")

            # Verify execution evidence for every mutation family using the isolated
            # acceptance identity. Direct maintenance cleanup is intentionally not audited.
            response = await client.get("/api/v1/activity?limit=200")
            _expect(response, 200, "activity read")
            activity = response.json()
            missing: list[str] = []
            for action_type, entity_id in sorted(expected_activity):
                found = any(
                    item.get("action_type") == action_type
                    and item.get("entity_id") == entity_id
                    and item.get("status") == "success"
                    for item in activity
                )
                if not found:
                    missing.append(f"{action_type}:{entity_id}")
            if missing:
                raise AssertionError(
                    "missing successful execution evidence: " + ", ".join(missing)
                )
            _record("execution_log")

    except BaseException as exc:
        primary_error = exc
    finally:
        app.dependency_overrides.pop(current_user, None)
        try:
            await cleanup_exact_artifacts(artifacts)
            print("acceptance_cleanup=PASS", flush=True)
        except BaseException as cleanup_error:
            print(
                f"acceptance_cleanup=FAIL:{type(cleanup_error).__name__}",
                file=sys.stderr,
                flush=True,
            )
            if primary_error is None:
                primary_error = cleanup_error
            else:
                primary_error = RuntimeError(
                    "acceptance failed and exact-ID cleanup also failed"
                )

    if primary_error is not None:
        raise primary_error

    print(
        json.dumps(
            {
                "acceptance": "cloud_domain_parity",
                "status": "PASS",
                "cleanup": "PASS",
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(run_acceptance())
    except BaseException as exc:
        exit_code = FAILURE_EXIT_CODES.get(LAST_PASSED_CHECK, 50)
        print(
            f"acceptance_failure_phase={LAST_PASSED_CHECK}:"
            f"{type(exc).__name__}:exit_code={exit_code}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(exit_code) from exc

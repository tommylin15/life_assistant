#!/usr/bin/env python3
"""Exercise Checklist Cloud against the real dev-test PostgreSQL database.

The runner uses the deployed FastAPI application and real database session while
replacing only the identity dependency with a synthetic acceptance user. All
business rows are tracked by exact ID and removed on failure/success paths.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import sys
import uuid

import httpx
from sqlalchemy import delete, select

from app.api.auth import current_user
from app.db.session import SessionLocal
from app.main import app
from app.models.migration_support import ChecklistItem
from app.models.task import Task


ACCEPTANCE_USER_SUB = "acceptance-checklist-cloud"
ACCEPTANCE_USER = {
    "sub": ACCEPTANCE_USER_SUB,
    "email": "checklist-cloud-acceptance@example.invalid",
    "name": "Checklist Cloud Acceptance",
}

LAST_PASSED_CHECK = "bootstrap"
FAILURE_EXIT_CODES = {
    "bootstrap": 71,
    "task_create": 72,
    "checklist_create_replay": 73,
    "checklist_order_persistence": 74,
    "checklist_update_persistence": 75,
    "cross_task_guard": 76,
    "checklist_delete_persistence": 77,
    "task_delete_child_cleanup": 78,
    "execution_log": 79,
}


@dataclass
class AcceptanceArtifacts:
    task_ids: set[str] = field(default_factory=set)
    checklist_item_ids: set[str] = field(default_factory=set)


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _expect(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: "
            f"{response.text[:500]}"
        )


def _object(response: httpx.Response, label: str) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: response was not JSON") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{label}: expected JSON object")
    return payload


def _list(response: httpx.Response, label: str) -> list[dict]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: response was not JSON") from exc
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise AssertionError(f"{label}: expected JSON object list")
    return payload


def _record(check: str) -> None:
    global LAST_PASSED_CHECK
    LAST_PASSED_CHECK = check
    print(f"acceptance_check={check}:PASS", flush=True)


async def cleanup_exact_artifacts(artifacts: AcceptanceArtifacts) -> None:
    """Delete only rows created by this acceptance run, in FK-safe order."""

    async with SessionLocal() as db:
        if artifacts.checklist_item_ids:
            await db.execute(
                delete(ChecklistItem).where(
                    ChecklistItem.id.in_(tuple(artifacts.checklist_item_ids))
                )
            )
        if artifacts.task_ids:
            await db.execute(delete(Task).where(Task.id.in_(tuple(artifacts.task_ids))))
        await db.commit()

    async with SessionLocal() as db:
        if artifacts.checklist_item_ids:
            result = await db.execute(
                select(ChecklistItem).where(
                    ChecklistItem.id.in_(tuple(artifacts.checklist_item_ids))
                )
            )
            if result.scalars().first() is not None:
                raise AssertionError("cleanup left acceptance checklist rows behind")
        if artifacts.task_ids:
            result = await db.execute(
                select(Task).where(Task.id.in_(tuple(artifacts.task_ids)))
            )
            if result.scalars().first() is not None:
                raise AssertionError("cleanup left acceptance task rows behind")


async def run_acceptance() -> None:
    artifacts = AcceptanceArtifacts()
    label = f"[ACCEPTANCE TEST] checklist-cloud {uuid.uuid4()}"
    action_a = f"checklist-create-a-{uuid.uuid4()}"
    action_b = f"checklist-create-b-{uuid.uuid4()}"
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
            response = await client.post(
                "/api/v1/tasks",
                json={"title": f"{label} Task"},
            )
            _expect(response, 201, "task create")
            task_id = str(_object(response, "task create")["id"])
            artifacts.task_ids.add(task_id)
            expected_activity.add(("task.create", task_id))
            _record("task_create")

            response = await client.post(
                f"/api/v1/tasks/{task_id}/checklist",
                headers={"X-Life-Assistant-Action-ID": action_a},
                json={"title": f"{label} First", "sort_order": 5},
            )
            _expect(response, 201, "checklist first create")
            first = _object(response, "checklist first create")
            first_id = str(first["id"])
            artifacts.checklist_item_ids.add(first_id)
            expected_activity.add(("checklist_item.create", first_id))
            if first.get("sort_order") != 5 or first.get("is_done") is not False:
                raise AssertionError("first checklist item response mismatch")

            replay = await client.post(
                f"/api/v1/tasks/{task_id}/checklist",
                headers={"X-Life-Assistant-Action-ID": action_a},
                json={"title": f"{label} First", "sort_order": 5},
            )
            _expect(replay, 201, "checklist first replay")
            if str(_object(replay, "checklist first replay").get("id")) != first_id:
                raise AssertionError("checklist action-id replay created a different item")
            _record("checklist_create_replay")

            response = await client.post(
                f"/api/v1/tasks/{task_id}/checklist",
                headers={"X-Life-Assistant-Action-ID": action_b},
                json={"title": f"{label} Second"},
            )
            _expect(response, 201, "checklist second create")
            second = _object(response, "checklist second create")
            second_id = str(second["id"])
            artifacts.checklist_item_ids.add(second_id)
            expected_activity.add(("checklist_item.create", second_id))
            if second.get("sort_order") != 6:
                raise AssertionError(
                    f"auto sort_order expected 6, got {second.get('sort_order')}"
                )

            response = await client.get(f"/api/v1/tasks/{task_id}/checklist")
            _expect(response, 200, "checklist initial reread")
            items = _list(response, "checklist initial reread")
            if [str(item.get("id")) for item in items] != [first_id, second_id]:
                raise AssertionError("checklist initial stable ordering mismatch")
            _record("checklist_order_persistence")

            response = await client.patch(
                f"/api/v1/tasks/{task_id}/checklist/{second_id}",
                json={
                    "title": f"{label} Second Updated",
                    "is_done": True,
                    "sort_order": 0,
                },
            )
            _expect(response, 200, "checklist update")
            updated = _object(response, "checklist update")
            if (
                updated.get("title") != f"{label} Second Updated"
                or updated.get("is_done") is not True
                or updated.get("sort_order") != 0
            ):
                raise AssertionError("checklist update response mismatch")
            expected_activity.add(("checklist_item.update", second_id))

            response = await client.get(f"/api/v1/tasks/{task_id}/checklist")
            _expect(response, 200, "checklist updated reread")
            items = _list(response, "checklist updated reread")
            if [str(item.get("id")) for item in items] != [second_id, first_id]:
                raise AssertionError("checklist updated ordering was not persisted")
            if items[0].get("is_done") is not True:
                raise AssertionError("checklist completion state was not persisted")
            _record("checklist_update_persistence")

            response = await client.post(
                "/api/v1/tasks",
                json={"title": f"{label} Other Task"},
            )
            _expect(response, 201, "other task create")
            other_task_id = str(_object(response, "other task create")["id"])
            artifacts.task_ids.add(other_task_id)
            expected_activity.add(("task.create", other_task_id))

            response = await client.patch(
                f"/api/v1/tasks/{other_task_id}/checklist/{first_id}",
                json={"is_done": True},
            )
            _expect(response, 404, "cross-task checklist guard")
            _record("cross_task_guard")

            response = await client.delete(
                f"/api/v1/tasks/{task_id}/checklist/{first_id}"
            )
            _expect(response, 204, "checklist item delete")
            expected_activity.add(("checklist_item.delete", first_id))

            response = await client.get(f"/api/v1/tasks/{task_id}/checklist")
            _expect(response, 200, "checklist delete reread")
            items = _list(response, "checklist delete reread")
            if [str(item.get("id")) for item in items] != [second_id]:
                raise AssertionError("deleted checklist item remained visible")
            _record("checklist_delete_persistence")

            response = await client.delete(f"/api/v1/tasks/{task_id}")
            _expect(response, 204, "task delete with checklist child")
            expected_activity.add(("task.delete", task_id))

            async with SessionLocal() as db:
                if await db.get(ChecklistItem, second_id) is not None:
                    raise AssertionError("task delete did not remove checklist child")
                if await db.get(Task, task_id) is not None:
                    raise AssertionError("task delete did not remove parent task")
            _record("task_delete_child_cleanup")

            response = await client.delete(f"/api/v1/tasks/{other_task_id}")
            _expect(response, 204, "other task delete")
            expected_activity.add(("task.delete", other_task_id))

            response = await client.get("/api/v1/activity?limit=200")
            _expect(response, 200, "activity read")
            activity = _list(response, "activity read")
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
                "acceptance": "checklist_cloud",
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
        exit_code = FAILURE_EXIT_CODES.get(LAST_PASSED_CHECK, 80)
        print(
            f"acceptance_failure_phase={LAST_PASSED_CHECK}:"
            f"{type(exc).__name__}:exit_code={exit_code}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(exit_code) from exc

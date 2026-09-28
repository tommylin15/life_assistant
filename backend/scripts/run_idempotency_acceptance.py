#!/usr/bin/env python3
"""Run action-id idempotency and destructive-policy acceptance in dev-test."""

from __future__ import annotations

import asyncio
import sys
import uuid

import httpx
from sqlalchemy import delete, select

from app.api.auth import current_user
from app.confirmation import CONFIRMATION_HEADER, explicit_confirmation_value
from app.db.session import SessionLocal
from app.main import app
from app.models.execution_log import ExecutionLog
from app.models.project import Project


RUN_ID = uuid.uuid4().hex
ACCEPTANCE_USER_SUB = f"acceptance-idempotency-{RUN_ID}"
ACCEPTANCE_USER = {
    "sub": ACCEPTANCE_USER_SUB,
    "email": "idempotency-acceptance@example.invalid",
    "name": "Idempotency Acceptance",
}
ACTION_ID = f"project-create-{RUN_ID}"
PROJECT_NAME = f"[ACCEPTANCE TEST] Idempotency Project {RUN_ID}"
POLICY_COOKIE = {"__session": "id:synthetic-acceptance-session"}


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _expect(response: httpx.Response, status: int, label: str) -> None:
    if response.status_code != status:
        raise AssertionError(
            f"{label}: expected HTTP {status}, got {response.status_code}: "
            f"{response.text[:500]}"
        )


def _expect_error(response: httpx.Response, status: int, code: str, label: str) -> None:
    _expect(response, status, label)
    payload = response.json()
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict) or error.get("code") != code:
        raise AssertionError(f"{label}: expected error code {code}, got {payload}")
    if not response.headers.get("X-Request-ID"):
        raise AssertionError(f"{label}: response missing X-Request-ID")


def _record(check: str) -> None:
    print(f"acceptance_check={check}:PASS", flush=True)


async def _verify_database(project_id: str) -> None:
    async with SessionLocal() as db:
        project_result = await db.execute(select(Project).where(Project.id == project_id))
        projects = project_result.scalars().all()
        if len(projects) != 1:
            raise AssertionError(
                f"expected exactly one Project after replay, found {len(projects)}"
            )

        log_result = await db.execute(
            select(ExecutionLog).where(
                ExecutionLog.user_sub == ACCEPTANCE_USER_SUB,
                ExecutionLog.action_type == "project.create",
                ExecutionLog.action_id == ACTION_ID,
            )
        )
        logs = log_result.scalars().all()
        if len(logs) != 1:
            raise AssertionError(
                f"expected exactly one idempotency execution row, found {len(logs)}"
            )
        log = logs[0]
        if log.status != "success" or log.result != "created":
            raise AssertionError(
                f"unexpected idempotency execution result: {log.status}/{log.result}"
            )
        if log.entity_id != project_id:
            raise AssertionError("idempotency execution entity_id mismatch")
        if not log.request_hash or len(log.request_hash) != 64:
            raise AssertionError("idempotency execution request hash missing")
    _record("action_id_single_database_write")


async def _cleanup(project_id: str | None) -> None:
    async with SessionLocal() as db:
        if project_id:
            await db.execute(delete(Project).where(Project.id == project_id))
        await db.execute(
            delete(ExecutionLog).where(ExecutionLog.user_sub == ACCEPTANCE_USER_SUB)
        )
        await db.commit()

    async with SessionLocal() as db:
        if project_id:
            project = await db.get(Project, project_id)
            if project is not None:
                raise AssertionError("cleanup left acceptance Project behind")
        result = await db.execute(
            select(ExecutionLog).where(ExecutionLog.user_sub == ACCEPTANCE_USER_SUB)
        )
        if result.scalars().first() is not None:
            raise AssertionError("cleanup left idempotency execution logs behind")
    _record("idempotency_cleanup")


async def run_acceptance() -> None:
    app.dependency_overrides[current_user] = _acceptance_user
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    project_id: str | None = None
    primary_error: BaseException | None = None

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://acceptance.local",
            timeout=30.0,
        ) as client:
            headers = {"X-Life-Assistant-Action-ID": ACTION_ID}
            payload = {
                "name": PROJECT_NAME,
                "summary": "idempotency acceptance",
                "status": "active",
            }

            first = await client.post(
                "/api/v1/projects",
                json=payload,
                headers=headers,
            )
            _expect(first, 201, "first project create")
            project_id = str(first.json()["id"])

            replay = await client.post(
                "/api/v1/projects",
                json=payload,
                headers=headers,
            )
            _expect(replay, 201, "project create replay")
            if str(replay.json().get("id")) != project_id:
                raise AssertionError("same action_id returned a different Project id")
            _record("action_id_replay_same_result")

            conflict_payload = dict(payload)
            conflict_payload["summary"] = "different request body"
            conflict = await client.post(
                "/api/v1/projects",
                json=conflict_payload,
                headers=headers,
            )
            _expect_error(
                conflict,
                409,
                "idempotency_conflict",
                "project action_id body conflict",
            )
            _record("action_id_payload_conflict")

            activity = await client.get("/api/v1/activity?limit=100")
            _expect(activity, 200, "activity read")
            matches = [
                item
                for item in activity.json()
                if item.get("action_type") == "project.create"
                and item.get("action_id") == ACTION_ID
            ]
            if len(matches) != 1:
                raise AssertionError(
                    f"expected one action_id activity row, found {len(matches)}"
                )
            if matches[0].get("status") != "success":
                raise AssertionError("idempotency activity row was not successful")
            _record("action_id_single_activity_row")

            await _verify_database(project_id)

            project_path = f"/api/v1/projects/{project_id}"
            blocked = await client.delete(project_path, cookies=POLICY_COOKIE)
            _expect_error(
                blocked,
                409,
                "confirmation_required",
                "project delete confirmation gate",
            )
            _record("project_delete_confirmation_required")

            wrong_target = await client.delete(
                project_path,
                cookies=POLICY_COOKIE,
                headers={
                    CONFIRMATION_HEADER: explicit_confirmation_value(
                        "project.delete", "different-project"
                    )
                },
            )
            _expect_error(
                wrong_target,
                409,
                "confirmation_required",
                "project delete target-bound confirmation",
            )
            _record("project_delete_confirmation_target_bound")

            confirmed = await client.delete(
                project_path,
                cookies=POLICY_COOKIE,
                headers={
                    CONFIRMATION_HEADER: explicit_confirmation_value(
                        "project.delete", project_id
                    )
                },
            )
            _expect(confirmed, 204, "confirmed project delete")
            _record("project_delete_explicit_confirmation")
            project_id = None
    except BaseException as exc:
        primary_error = exc
    finally:
        app.dependency_overrides.pop(current_user, None)
        try:
            await _cleanup(project_id)
        except BaseException as cleanup_error:
            if primary_error is None:
                primary_error = cleanup_error
            else:
                print(
                    f"cleanup_error={type(cleanup_error).__name__}:{cleanup_error}",
                    file=sys.stderr,
                    flush=True,
                )

    if primary_error is not None:
        raise primary_error
    print("idempotency_runtime_acceptance=PASS", flush=True)
    print("destructive_policy_runtime_acceptance=PASS", flush=True)


def main() -> int:
    try:
        asyncio.run(run_acceptance())
    except BaseException as exc:
        print(
            f"idempotency_runtime_acceptance=FAIL:{type(exc).__name__}:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

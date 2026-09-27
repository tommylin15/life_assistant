#!/usr/bin/env python3
"""Run deterministic Google provider failure-path acceptance in dev-test.

This runner executes the real FastAPI routes and real PostgreSQL execution log
from the deployed image. Only the outbound Google provider functions are
replaced with deterministic failures, so the job proves audit behavior without
requiring or mutating a personal Google account.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import sys
import uuid

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.api import google_integrations
from app.api.auth import current_user
from app.db.session import SessionLocal
from app.main import app
from app.models.execution_log import ExecutionLog
from app.models.task import Task


RUN_ID = uuid.uuid4().hex
ACCEPTANCE_USER_SUB = f"acceptance-google-failure-{RUN_ID}"
ACCEPTANCE_USER = {
    "sub": ACCEPTANCE_USER_SUB,
    "email": "google-failure-acceptance@example.invalid",
    "name": "Google Failure Acceptance",
}
TASK_TITLE = f"[ACCEPTANCE TEST] Google failure task {RUN_ID}"


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _record(check: str) -> None:
    print(f"acceptance_check={check}:PASS", flush=True)


def _expect_error(
    response: httpx.Response,
    expected_status: int,
    expected_code: str,
    label: str,
) -> None:
    if response.status_code != expected_status:
        raise AssertionError(
            f"{label}: expected HTTP {expected_status}, got "
            f"{response.status_code}: {response.text[:500]}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: response was not JSON") from exc
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict) or error.get("code") != expected_code:
        raise AssertionError(
            f"{label}: expected error code {expected_code}, got {payload}"
        )
    if not response.headers.get("X-Request-ID"):
        raise AssertionError(f"{label}: response missing X-Request-ID")


async def _verify_activity(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/activity?limit=100")
    if response.status_code != 200:
        raise AssertionError(
            f"activity read: expected HTTP 200, got "
            f"{response.status_code}: {response.text[:500]}"
        )
    payload = response.json()
    if not isinstance(payload, list):
        raise AssertionError("activity read: expected JSON list")

    expected = {
        "calendar.create": (
            "failure",
            "http_503",
            "Calendar create failed",
        ),
        "gmail.to_task": (
            "failure",
            "http_503",
            "Gmail to task conversion failed",
        ),
        "drive.bridge.ensure": (
            "partial_success",
            "http_503",
            "Drive Bridge ensure partially completed",
        ),
    }
    for action_type, (status, error_category, summary) in expected.items():
        matches = [
            item
            for item in payload
            if item.get("action_type") == action_type
            and item.get("provider") == "google"
        ]
        if len(matches) != 1:
            raise AssertionError(
                f"{action_type}: expected one acceptance activity row, "
                f"found {len(matches)}"
            )
        item = matches[0]
        if item.get("status") != status:
            raise AssertionError(
                f"{action_type}: expected status {status}, got {item.get('status')}"
            )
        if item.get("error_category") != error_category:
            raise AssertionError(
                f"{action_type}: expected error_category {error_category}, "
                f"got {item.get('error_category')}"
            )
        if item.get("summary") != summary:
            raise AssertionError(
                f"{action_type}: expected summary {summary!r}, "
                f"got {item.get('summary')!r}"
            )
        if item.get("result") is not None:
            raise AssertionError(f"{action_type}: failed action must not have result")
        if not item.get("request_id") or not item.get("finished_at"):
            raise AssertionError(
                f"{action_type}: activity evidence missing request/finish metadata"
            )

    _record("google_failure_activity_evidence")


async def _verify_no_task_created() -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.title == TASK_TITLE))
        if result.scalars().first() is not None:
            raise AssertionError("Gmail provider failure created an internal Task")
    _record("gmail_failure_no_internal_write")


async def _cleanup() -> None:
    async with SessionLocal() as db:
        await db.execute(
            delete(ExecutionLog).where(
                ExecutionLog.user_sub == ACCEPTANCE_USER_SUB
            )
        )
        await db.execute(delete(Task).where(Task.title == TASK_TITLE))
        await db.commit()

    async with SessionLocal() as db:
        logs = await db.execute(
            select(ExecutionLog).where(
                ExecutionLog.user_sub == ACCEPTANCE_USER_SUB
            )
        )
        task = await db.execute(select(Task).where(Task.title == TASK_TITLE))
        if logs.scalars().first() is not None:
            raise AssertionError("cleanup left Google failure execution logs behind")
        if task.scalars().first() is not None:
            raise AssertionError("cleanup left acceptance Task behind")
    _record("google_failure_cleanup")


async def run_acceptance() -> None:
    original_request_google = google_integrations._request_google
    original_ensure_drive_folder = google_integrations._ensure_drive_folder
    primary_error: BaseException | None = None

    async def fail_google_provider(*_args, **_kwargs):
        raise HTTPException(503, "Synthetic Google provider failure")

    drive_calls = 0

    async def partial_drive_provider(
        _db,
        _user_sub: str,
        name: str,
        parent_id: str | None = None,
    ):
        nonlocal drive_calls
        drive_calls += 1
        if drive_calls == 1:
            if name != "life_assistant" or parent_id is not None:
                raise AssertionError("unexpected Drive root ensure request")
            return {"id": f"acceptance-root-{RUN_ID}", "name": name}, True
        raise HTTPException(503, "Synthetic Google provider failure")

    app.dependency_overrides[current_user] = _acceptance_user
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://acceptance.local",
            timeout=30.0,
        ) as client:
            google_integrations._request_google = fail_google_provider

            start = datetime.now(timezone.utc) + timedelta(days=1)
            end = start + timedelta(minutes=30)
            response = await client.post(
                "/api/v1/integrations/google/calendar/events",
                json={
                    "summary": f"[ACCEPTANCE TEST] Calendar failure {RUN_ID}",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
            )
            _expect_error(response, 503, "http_503", "calendar provider failure")
            _record("calendar_provider_failure")

            response = await client.post(
                "/api/v1/integrations/google/gmail/messages/"
                f"acceptance-message-{RUN_ID}/task",
                json={"title": TASK_TITLE},
            )
            _expect_error(response, 503, "http_503", "gmail provider failure")
            _record("gmail_provider_failure")

            google_integrations._ensure_drive_folder = partial_drive_provider
            response = await client.post(
                "/api/v1/integrations/google/drive/bridge"
            )
            _expect_error(response, 503, "http_503", "drive partial failure")
            if drive_calls != 2:
                raise AssertionError(
                    f"drive partial failure expected two ensure calls, got {drive_calls}"
                )
            _record("drive_partial_success_failure")

            await _verify_no_task_created()
            await _verify_activity(client)
    except BaseException as exc:
        primary_error = exc
    finally:
        google_integrations._request_google = original_request_google
        google_integrations._ensure_drive_folder = original_ensure_drive_folder
        app.dependency_overrides.pop(current_user, None)
        try:
            await _cleanup()
        except BaseException as cleanup_error:
            if primary_error is None:
                primary_error = cleanup_error
            else:
                print(
                    "cleanup_error="
                    f"{type(cleanup_error).__name__}:{cleanup_error}",
                    file=sys.stderr,
                    flush=True,
                )

    if primary_error is not None:
        raise primary_error
    print("google_failure_runtime_acceptance=PASS", flush=True)


def main() -> int:
    try:
        asyncio.run(run_acceptance())
    except BaseException as exc:
        print(
            f"google_failure_runtime_acceptance=FAIL:"
            f"{type(exc).__name__}:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

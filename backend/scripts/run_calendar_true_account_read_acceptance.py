#!/usr/bin/env python3
"""Read-only live Google Calendar authorization acceptance.

Uses the deployed Cloud Run image and its existing encrypted OAuth tokens.
No event contents, user identifiers, access tokens, or refresh tokens are logged.
No Google Calendar event is created, patched, or deleted.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

from app.api.google_integrations import CALENDAR_EVENTS_URL, _request_google
from app.db.session import SessionLocal
from app.models.google_integration import GoogleConnection
from app.services.google_oauth import SERVICE_SCOPES


# Safe exit-code categories remain available when Cloud Logging cannot be read.
EXIT_CODES = {
    "not_verified": 2,
    "reauthorization": 21,
    "insufficient_scope": 22,
    "google_upstream": 23,
    "google_unavailable": 24,
    "google_other": 25,
    "invalid_output": 26,
    "unexpected_provider": 29,
    "database": 31,
    "runtime": 32,
}


async def _run() -> int:
    scope = SERVICE_SCOPES["calendar"][0]

    async with SessionLocal() as db:
        # Fail closed instead of arbitrarily choosing an owner's calendar.
        result = await db.execute(
            select(GoogleConnection.user_sub)
            .where(GoogleConnection.scopes.contains(scope))
            .limit(2)
        )
        user_ids = result.scalars().all()
        if len(user_ids) != 1:
            reason = "no_calendar_authorization" if not user_ids else "multiple_authorized_owners"
            print(f"calendar_true_account=NOT_VERIFIED reason={reason}", flush=True)
            return 2

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=7)
        try:
            response = await asyncio.wait_for(
                _request_google(
                    db,
                    user_ids[0],
                    scope,
                    "GET",
                    CALENDAR_EVENTS_URL,
                    params={
                        "timeMin": now.isoformat().replace("+00:00", "Z"),
                        "timeMax": end.isoformat().replace("+00:00", "Z"),
                        "singleEvents": "true",
                        "orderBy": "startTime",
                        "maxResults": 10,
                    },
                ),
                timeout=45,
            )
        except HTTPException as exc:
            error = {
                409: "reauthorization",
                403: "insufficient_scope",
                502: "google_upstream",
                503: "google_unavailable",
            }.get(exc.status_code, "google_other")
            print("calendar_true_account=FAIL category=" + error, flush=True)
            return EXIT_CODES[error]
        except asyncio.TimeoutError:
            print("calendar_true_account=FAIL category=google_unavailable", flush=True)
            return EXIT_CODES["google_unavailable"]
        except Exception:
            print("calendar_true_account=FAIL category=unexpected_provider", flush=True)
            return EXIT_CODES["unexpected_provider"]

        try:
            data = response.json()
        except (TypeError, ValueError):
            print("calendar_true_account=FAIL category=invalid_output", flush=True)
            return EXIT_CODES["invalid_output"]
        events = data.get("items") if isinstance(data, dict) else None
        if response.status_code != 200 or not isinstance(events, list):
            print("calendar_true_account=FAIL category=invalid_output", flush=True)
            return EXIT_CODES["invalid_output"]

        # A valid empty calendar is still a successful read/list.
        print("calendar_true_account_read_list=PASS", flush=True)
        print("calendar_true_account_returned=" + str(len(events)), flush=True)
        return 0


async def run() -> int:
    try:
        return await _run()
    except SQLAlchemyError:
        print("calendar_true_account=FAIL category=database", flush=True)
        return EXIT_CODES["database"]
    except Exception:
        print("calendar_true_account=FAIL category=runtime", flush=True)
        return EXIT_CODES["runtime"]


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

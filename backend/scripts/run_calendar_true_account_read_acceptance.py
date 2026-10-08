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

from app.api.google_integrations import CALENDAR_EVENTS_URL, _request_google
from app.db.session import SessionLocal
from app.models.google_integration import GoogleConnection
from app.services.google_oauth import SERVICE_SCOPES


async def run() -> int:
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
        except Exception as exc:
            # Type-only diagnostic: never print credentials, user-sub, or events.
            print(
                "calendar_true_account=FAIL category=" + type(exc).__name__,
                flush=True,
            )
            return 1

        data = response.json()
        events = data.get("items")
        if response.status_code != 200 or not isinstance(events, list):
            print("calendar_true_account=FAIL category=invalid_provider_output", flush=True)
            return 1

        # A valid empty calendar is still a successful read/list.
        print("calendar_true_account_read_list=PASS", flush=True)
        print("calendar_true_account_returned=" + str(len(events)), flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

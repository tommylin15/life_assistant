"""Bounded read-only gate for fixed-staging actual Google authorization.

Executed with a one-time Cloud Run Job argument override, never a web endpoint.
No session tokens or PII are printed. Failure must trigger staging-only rollback.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

EXPECTED_REVISION = "REPLACE_ME"
CANARY_START_UTC = "REPLACE_ME"
ACTION_TYPES = ("staging_google_callback", "staging_google_session")

# Exit codes propagate via Cloud Run task status even if Cloud Logging is inaccessible.
OWNER_EVIDENCE_MISSING_EXIT = 20
VERIFICATION_ERROR_EXIT = 21


class OwnerEvidenceTimeout(TimeoutError):
    """This release did not receive both genuine owner events in its canary window."""


async def verified_owner_oauth_pair() -> bool:
    revision = EXPECTED_REVISION
    start = datetime.fromisoformat(CANARY_START_UTC.replace("Z", "+00:00"))
    if not revision.startswith("life-assistant-api-") or start.tzinfo is None:
        raise ValueError("Invalid staging canary identity")
    # Only newly recorded success events for the same authenticated Google
    # owner count. Events are written AFTER code exchange and session verify.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SET TRANSACTION READ ONLY"))
            await conn.execute(text("SET LOCAL statement_timeout='15s'"))
            rows = (await conn.execute(text("""
                SELECT user_sub, count(DISTINCT action_type) AS steps
                FROM execution_logs
                WHERE provider='google'
                  AND status='success'
                  AND entity_type='cloud_run_revision'
                  AND entity_id=:revision
                  AND summary='fixed_staging_google_oauth_acceptance'
                  AND started_at>=:started
                  AND action_type IN ('staging_google_callback','staging_google_session')
                GROUP BY user_sub
                HAVING count(DISTINCT action_type)=2
                LIMIT 1
            """), {"revision": revision, "started": start})).first()
            return rows is not None
    finally:
        await engine.dispose()


async def run() -> None:
    # A bounded staging-only canary: no automatic Google sign-in simulation,
    # no production traffic changes, no recording of user_sub or credentials.
    deadline = datetime.now(timezone.utc) + timedelta(minutes=6)
    while datetime.now(timezone.utc) < deadline:
        if await verified_owner_oauth_pair():
            print("staging_true_google_callback_and_session=PASS", flush=True)
            return
        await asyncio.sleep(12)
    raise OwnerEvidenceTimeout("Owner callback/session pair not received")


def main() -> None:
    try:
        asyncio.run(run())
    except OwnerEvidenceTimeout:
        # The owner did not complete a same-revision callback/session pair.
        # Do not misclassify absence of evidence as a database outage.
        print("staging_oauth_e2e=NOT_VERIFIED reason=missing_owner_callback_session; staging_rollback_required", flush=True)
        raise SystemExit(OWNER_EVIDENCE_MISSING_EXIT) from None
    except Exception as exc:
        # Exception messages may carry connection endpoints/credentials;
        # logging the exception class only is safe and sufficient to distinguish
        # an operational failure from lack of user authorization.
        print(f"staging_oauth_e2e=FAIL reason=verification_error error_type={type(exc).__name__}; staging_rollback_required", flush=True)
        raise SystemExit(VERIFICATION_ERROR_EXIT) from None


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m scripts.verify_staging_google_e2e CANDIDATE_REVISION CANARY_START_UTC")
    EXPECTED_REVISION, CANARY_START_UTC = sys.argv[1:]
    main()

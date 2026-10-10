"""Candidate compatibility on old 0014: preserve legacy routes, fail closed elsewhere."""
import unittest
from unittest.mock import AsyncMock

from fastapi import HTTPException
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ui_policies import effective_features, feature_gate


class _PgUndefinedTable(Exception):
    sqlstate = "42P01"


def _missing(table="feature_rollouts", code="42P01"):
    origin = _PgUndefinedTable(f'relation "{table}" does not exist')
    origin.sqlstate = code
    return ProgrammingError(
        "SELECT ... FROM feature_rollouts", {}, origin,
    )


def _db(*, revision="20261009_0014", error=None):
    db = AsyncMock(spec=AsyncSession)
    db.get.side_effect = error or _missing()
    db.execute.side_effect = error or _missing()
    db.scalar.return_value = revision
    return db


class PreMigrationFeatureGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_known_0014_missing_table_preserves_existing_project_api(self):
        db = _db()
        await feature_gate("projects")(user={"email": "person@example.org"}, db=db)
        db.rollback.assert_awaited_once()
        self.assertEqual(db.scalar.await_count, 1)

    async def test_known_0014_missing_table_still_blocks_curated_events(self):
        db = _db()
        with self.assertRaises(HTTPException) as exc:
            await feature_gate("events")(user={"email": "anyone@example.org"}, db=db)
        self.assertEqual(exc.exception.status_code, 503)

    async def test_new_features_hidden_in_unmigrated_ui_catalog(self):
        db = _db()
        result = await effective_features(db, {"email": "anyone@example.org"})
        policies = {item["key"]: item for item in result}
        self.assertTrue(policies["projects"]["available"])
        self.assertFalse(policies["events"]["available"])
        self.assertEqual(policies["events"]["status"], "hidden")

    async def test_0015_missing_table_fails_closed_not_policy_bypass(self):
        db = _db(revision="20261010_0015")
        with self.assertRaises(HTTPException) as exc:
            await feature_gate("projects")(user={"email": "anyone@example.org"}, db=db)
        self.assertEqual(exc.exception.status_code, 503)

    async def test_unrelated_undefined_table_is_not_treated_as_legacy_rollout(self):
        db = _db(error=_missing("private_users"))
        with self.assertRaises(ProgrammingError):
            await feature_gate("projects")(user={"email": "anyone@example.org"}, db=db)
        db.rollback.assert_not_awaited()

    async def test_other_sqlstate_never_bypasses_policy(self):
        db = _db(error=_missing(code="42501"))
        with self.assertRaises(ProgrammingError):
            await feature_gate("projects")(user={"email": "anyone@example.org"}, db=db)
        db.rollback.assert_not_awaited()

    async def test_unknown_old_revision_cannot_bypass_policy(self):
        db = _db(revision="20261009_0012")
        with self.assertRaises(HTTPException) as exc:
            await feature_gate("projects")(user={"email": "anyone@example.org"}, db=db)
        self.assertEqual(exc.exception.status_code, 503)

    async def test_real_rollout_still_prohibits_disabled_feature(self):
        db = AsyncMock(spec=AsyncSession)
        db.get.return_value = type("Policy", (), {
            "status": "hidden", "audience": "all",
        })()
        with self.assertRaises(HTTPException) as exc:
            await feature_gate("projects")(user={"email": "anyone@example.org"}, db=db)
        self.assertEqual(exc.exception.status_code, 403)
        db.scalar.assert_not_awaited()
        db.rollback.assert_not_awaited()

    async def test_admin_enabled_activity_entries_allow_normal_account(self):
        db = AsyncMock(spec=AsyncSession)
        db.get.return_value = type("Policy", (), {"status": "enabled", "audience": "all"})()
        for key in ("events", "opportunities", "explore"):
            await feature_gate(key)(user={"sub": "ordinary", "email": "person@example.org"}, db=db)

    def test_normal_account_cannot_change_ai_management(self):
        from app.api.ui_policies import owner_only
        with self.assertRaises(HTTPException) as exc:
            owner_only({"sub": "ordinary", "email": "person@example.org"})
        self.assertEqual(exc.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()

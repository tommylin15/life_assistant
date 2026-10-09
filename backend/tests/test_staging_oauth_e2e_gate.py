"""Safety contracts for the true, owner-authenticated staging Google OAuth gate."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

from scripts import verify_staging_google_e2e as gate


class StagingOauthGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_successful_pair_for_same_owner_and_revision_counts(self):
        conn = MagicMock()
        conn.execute = AsyncMock(side_effect=[
            MagicMock(), MagicMock(), SimpleNamespace(first=lambda: ("owner-sub", 2))
        ])
        inner = MagicMock()
        inner.__aenter__ = AsyncMock(return_value=conn)
        inner.__aexit__ = AsyncMock(return_value=None)
        engine = MagicMock()
        engine.connect.return_value = inner
        engine.dispose = AsyncMock()
        with patch.object(gate, "EXPECTED_REVISION", "life-assistant-api-00212-abc"), \
             patch.object(gate, "CANARY_START_UTC", "2026-10-09T15:00:00Z"), \
             patch.object(gate, "create_async_engine", return_value=engine):
            result = await gate.verified_owner_oauth_pair()
        self.assertTrue(result)
        self.assertEqual(conn.execute.await_count, 3)
        sql = str(conn.execute.await_args_list[-1].args[0])
        values = conn.execute.await_args_list[-1].args[1]
        self.assertIn("count(DISTINCT action_type)=2", sql)
        self.assertIn("GROUP BY user_sub", sql)
        self.assertIn("status='success'", sql)
        self.assertIn("started_at>=:started", sql)
        self.assertEqual(values["revision"], "life-assistant-api-00212-abc")
        engine.dispose.assert_awaited_once()

    async def test_no_successful_pair_cannot_pass(self):
        conn = MagicMock()
        conn.execute = AsyncMock(side_effect=[
            MagicMock(), MagicMock(), SimpleNamespace(first=lambda: None)
        ])
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=conn)
        context.__aexit__ = AsyncMock(return_value=None)
        engine = MagicMock()
        engine.connect.return_value = context
        engine.dispose = AsyncMock()
        with patch.object(gate, "EXPECTED_REVISION", "life-assistant-api-00212-abc"), \
             patch.object(gate, "CANARY_START_UTC", "2026-10-09T15:00:00Z"), \
             patch.object(gate, "create_async_engine", return_value=engine):
            self.assertFalse(await gate.verified_owner_oauth_pair())

    async def test_missing_candidate_revision_fails_before_db_connection(self):
        with patch.object(gate, "EXPECTED_REVISION", "not-a-revision"), \
             patch.object(gate, "CANARY_START_UTC", "2026-10-09T15:00:00Z"), \
             patch.object(gate, "create_async_engine") as factory:
            with self.assertRaises(ValueError):
                await gate.verified_owner_oauth_pair()
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()

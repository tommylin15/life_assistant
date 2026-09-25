import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.errors import ApiError, reset_request_id, set_request_id
from app.services.execution_log import fail_execution, finish_execution, start_execution


class ExecutionLogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.add = MagicMock()
        self.db.commit = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.rollback = AsyncMock()
        self.token = set_request_id("req-test-1")

    def tearDown(self):
        reset_request_id(self.token)

    async def test_start_and_finish_execution(self):
        log = await start_execution(
            self.db,
            user_sub="user-1",
            action_type="calendar.create",
            provider="google",
            entity_type="calendar_event",
            summary="Create calendar event",
        )

        self.assertEqual(log.request_id, "req-test-1")
        self.assertEqual(log.status, "running")
        self.db.add.assert_called_once_with(log)

        await finish_execution(
            self.db,
            log,
            result="created",
            entity_id="event-1",
            summary="Calendar event created",
        )

        self.assertEqual(log.status, "success")
        self.assertEqual(log.result, "created")
        self.assertEqual(log.entity_id, "event-1")
        self.assertIsNotNone(log.finished_at)

    async def test_failure_records_safe_error_category(self):
        log = await start_execution(
            self.db,
            user_sub="user-1",
            action_type="calendar.update",
            provider="google",
        )

        await fail_execution(
            self.db,
            log,
            HTTPException(502, "provider details"),
            summary="Calendar update failed",
        )

        self.assertEqual(log.status, "failure")
        self.assertEqual(log.error_category, "http_502")
        self.assertEqual(log.summary, "Calendar update failed")
        self.assertIsNotNone(log.finished_at)

    async def test_audit_start_failure_blocks_action(self):
        self.db.commit = AsyncMock(side_effect=RuntimeError("db unavailable"))

        with self.assertRaises(ApiError) as caught:
            await start_execution(
                self.db,
                user_sub="user-1",
                action_type="task.create",
                provider="life_assistant",
            )

        self.assertEqual(caught.exception.code, "audit_unavailable")
        self.db.rollback.assert_awaited()


if __name__ == "__main__":
    unittest.main()

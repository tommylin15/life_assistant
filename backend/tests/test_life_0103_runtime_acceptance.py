"""Bounded source consistency tests for real DB acceptance."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from scripts.run_life_0103_runtime_acceptance import (
    FAILURE_CODES, inspect_handoff, insert_shopping_fixtures,
)


class Life0103ReadbackTests(unittest.TestCase):
    def test_accepts_current_valid_handoff_and_counts_missing_parent_nonfatally(self):
        row=SimpleNamespace(handoff_event_key="event:1", content_hash="b"*64,
            parent_event_key="parent:1",
            handoff_details={"event_key":"event:1",
                "handoff_updated_at_tpe":"2026-10-15T07:30:00+08:00"})
        self.assertEqual(inspect_handoff([row]), (1, 0, 1))

    def test_bad_hash_missing_details_and_key_mismatch_rejected(self):
        valid={"event_key":"event:1",
               "handoff_updated_at_tpe":"2026-10-15T07:30:00+08:00"}
        rows=[
            SimpleNamespace(handoff_event_key="event:1", content_hash="BAD",
                parent_event_key=None, handoff_details=valid),
            SimpleNamespace(handoff_event_key="event:2", content_hash="b"*64,
                parent_event_key=None, handoff_details=valid),
            SimpleNamespace(handoff_event_key="event:3", content_hash="c"*64,
                parent_event_key=None, handoff_details=None),
        ]
        self.assertEqual(inspect_handoff(rows), (3, 3, 0))

    def test_empty_pool_is_not_fake_data(self):
        self.assertEqual(inspect_handoff([]), (0, 0, 0))



class ShoppingRollbackFixtureTests(unittest.IsolatedAsyncioTestCase):
    async def test_parent_is_flushed_before_children_without_orm_relationship(self):
        db = MagicMock()
        calls = []
        db.add.side_effect = lambda _: calls.append("parent_add")
        db.add_all.side_effect = lambda _: calls.append("child_add")
        async def flush():
            calls.append("flush")
        db.flush = AsyncMock(side_effect=flush)
        await insert_shopping_fixtures(db, object(), [object(), object()])
        self.assertEqual(calls, ["parent_add", "flush", "child_add", "flush"])

    def test_failure_exit_codes_are_distinct_without_logging_access(self):
        self.assertEqual(set(FAILURE_CODES), {
            "handoff_read", "handoff_integrity", "shopping_mutation",
            "shopping_rollback",
        })
        self.assertEqual(len(set(FAILURE_CODES.values())), 4)

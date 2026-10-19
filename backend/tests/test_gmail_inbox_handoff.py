"""Gmail to Life Inbox: no auto-AI and completion requires a Life execution receipt."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Response

from app.api.gmail_radar import (
    get_item_for_life_inbox, confirm_gmail_life_inbox_link,
    _handoff_action_id, _serialize_item,
)
from app.models.execution_log import ExecutionLog
from app.api.inbox import InterpretInput, interpret


def mail(**kwargs):
    fields = dict(
        id="12345678-1234-1234-1234-123456789012",
        user_sub="account-a", title="繳費通知", summary="三天內繳費",
        gmail_thread_id="thread-1", status="pending",
        received_at=None, created_at=None, sender="bank",
        category="billing", linked_target=None, linked_entity_id=None,
    )
    fields.update(kwargs)
    return SimpleNamespace(**fields)


class GmailLifeLinkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.commit = AsyncMock()
        self.item = mail()

    async def test_owner_bound_handoff_returns_prefill_not_a_classification(self):
        self.db.scalar = AsyncMock(return_value=self.item)
        self.db.get = AsyncMock(return_value=SimpleNamespace(email="a@example.com"))
        data = await get_item_for_life_inbox(
            item_id=self.item.id, user={"sub": "account-a"}, db=self.db)
        self.assertIn("繳費通知", data["text"])
        self.assertIn("mail.google.com", data["text"])
        self.assertFalse(data["saved"])
        self.assertEqual(data["action_id"], _handoff_action_id(self.item.id))
        self.assertLessEqual(len(data["text"]), 1200)
        self.db.commit.assert_not_awaited()

    async def test_cannot_open_another_users_source(self):
        self.db.scalar = AsyncMock(return_value=None)
        with self.assertRaises(HTTPException) as ctx:
            await get_item_for_life_inbox(
                item_id=self.item.id, user={"sub": "other-user"}, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.db.commit.assert_not_awaited()

    async def test_gmail_handoff_uses_only_local_interpretation(self):
        self.db.scalar = AsyncMock(return_value=self.item)
        with patch("app.api.inbox.generate_text", new_callable=AsyncMock) as ai:
            output = await interpret(
                InterpretInput(text="Gmail 通知：繳費通知",
                               gmail_item_id=self.item.id),
                Response(), user={"sub": "account-a"}, db=self.db,
            )
        ai.assert_not_awaited()
        self.assertEqual(output["classification_source"], "gmail_local")
        self.assertEqual(output["candidates"][0]["target"], "task")
        self.assertFalse(output["candidates"][0]["select_default"])
        self.db.commit.assert_not_awaited()

    async def test_another_users_gmail_handoff_cannot_call_ai(self):
        self.db.scalar = AsyncMock(return_value=None)
        with patch("app.api.inbox.generate_text", new_callable=AsyncMock) as ai:
            with self.assertRaises(HTTPException) as raised:
                await interpret(
                    InterpretInput(text="Any content", gmail_item_id=self.item.id),
                    Response(), user={"sub": "other-user"}, db=self.db,
                )
        self.assertEqual(raised.exception.status_code, 404)
        ai.assert_not_awaited()

    async def test_no_receipt_does_not_mark_completed(self):
        self.db.scalar = AsyncMock(side_effect=[self.item, None])
        with self.assertRaises(HTTPException) as ctx:
            await confirm_gmail_life_inbox_link(
                item_id=self.item.id, user={"sub": "account-a"}, db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(self.item.status, "pending")
        self.db.commit.assert_not_awaited()

    async def test_only_verified_receipt_links_and_completes(self):
        receipt = SimpleNamespace(
            entity_type="task", entity_id="task-42", status="success")
        self.db.scalar = AsyncMock(side_effect=[self.item, receipt, self.item])
        data = await confirm_gmail_life_inbox_link(
            item_id=self.item.id, user={"sub": "account-a"}, db=self.db)
        self.assertEqual(self.item.status, "completed")
        self.assertEqual(self.item.linked_target, "task")
        self.assertEqual(self.item.linked_entity_id, "task-42")
        self.assertEqual(data["target_route"], "/tasks")
        self.db.commit.assert_awaited_once()
        self.assertIn("task", _serialize_item(self.item, "a@example.com")["linked_route"])

        # The second confirmation is a no-op, not a new Life write.
        again = await confirm_gmail_life_inbox_link(
            item_id=self.item.id, user={"sub": "account-a"}, db=self.db)
        self.assertEqual(again["entity_id"], "task-42")
        self.db.commit.assert_awaited_once()

    def test_action_id_is_stable_per_gmail_item(self):
        self.assertEqual(
            _handoff_action_id(self.item.id), _handoff_action_id(self.item.id))
        self.assertTrue(_handoff_action_id(self.item.id).startswith("gmailradar-"))

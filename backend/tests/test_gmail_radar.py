import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.gmail_radar import (
    classify_message, gmail_urls, manual_quick_scan, manual_three_day_backfill,
)
from app.models.google_integration import GoogleConnection


class GmailRadarRulesTests(unittest.TestCase):
    def test_high_precision_explicit_billing(self):
        self.assertEqual(classify_message("本期帳單繳費通知", ""), "billing")
        self.assertEqual(classify_message("Your payment due tomorrow", ""), "billing")

    def test_booking_pickup_and_deadline(self):
        self.assertEqual(classify_message("您的訂房確認", ""), "booking")
        self.assertEqual(classify_message("取貨通知：請前往門市", ""), "pickup")
        self.assertEqual(classify_message("報名截止提醒", ""), "deadline")

    def test_no_promotional_false_positive(self):
        self.assertIsNone(classify_message("限時優惠 85 折", "送您精美禮物"))
        self.assertIsNone(classify_message("我們的電子報", "新產品發表"))
        self.assertIsNone(classify_message("", "繳款通知"))

    def test_gmail_link_has_mailbox_fallback(self):
        links = gmail_urls("threadId123", "somebody@example.com")
        self.assertIn("threadId123", links["gmail_url"])
        self.assertIn("authuser=somebody%40example.com", links["gmail_url"])
        self.assertTrue(links["gmail_fallback_url"].startswith("https://mail.google.com/"))


class GmailRadarOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_locked_user_cannot_start_second_scan(self):
        db = MagicMock()
        res = MagicMock()
        res.scalar_one.return_value = False
        db.execute = AsyncMock(return_value=res)
        with self.assertRaises(HTTPException) as raised, patch(
            "app.api.gmail_radar._request_google", new_callable=AsyncMock
        ) as google:
            await manual_quick_scan(user={"sub": "user-a"}, db=db)
        self.assertEqual(raised.exception.status_code, 409)
        google.assert_not_awaited()

    async def test_missing_gmail_scope_fails_without_remote_read(self):
        db = MagicMock()
        res = MagicMock()
        res.scalar_one.return_value = True
        db.execute = AsyncMock(return_value=res)
        db.get = AsyncMock(return_value=GoogleConnection(
            user_sub="user-a", email="a@example.com", scopes="openid email"
        ))
        with self.assertRaises(HTTPException) as raised, patch(
            "app.api.gmail_radar._request_google", new_callable=AsyncMock
        ) as google:
            await manual_quick_scan(user={"sub": "user-a"}, db=db)
        self.assertEqual(raised.exception.status_code, 409)
        google.assert_not_awaited()

    @staticmethod
    def fake_list(ids):
        value = MagicMock()
        value.json.return_value = {"messages": [{"id": message_id} for message_id in ids]}
        return value

    @staticmethod
    def fake_metadata(message_id):
        response = MagicMock()
        response.json.return_value = {
            "id": message_id, "threadId": "thread-" + message_id,
            "internalDate": "1790000000000",
            "payload": {"headers": [
                {"name": "Subject", "value": "繳費通知"},
                {"name": "From", "value": "bank@example.com"},
            ]}, "snippet": "請查看帳單",
        }
        return response

    @staticmethod
    def fake_db(seen=()):
        db = MagicMock()
        locked = MagicMock()
        locked.scalar_one.return_value = True
        existing = MagicMock()
        existing.scalars.return_value.all.return_value = list(seen)
        db.execute = AsyncMock(side_effect=[locked, existing])
        db.get = AsyncMock(side_effect=[
            GoogleConnection(
                user_sub="user-a", email="a@example.com",
                scopes="https://www.googleapis.com/auth/gmail.readonly",
            ),
            None,
        ])
        db.scalar = AsyncMock(return_value=None)
        db.commit = AsyncMock()
        return db

    async def test_scan_never_accepts_or_reads_other_user(self):
        db = self.fake_db()
        with patch("app.api.gmail_radar._request_google", new_callable=AsyncMock) as google:
            google.side_effect = [
                self.fake_list(["msg1"]), self.fake_list(["msg1"]),
                self.fake_metadata("msg1"),
            ]
            result = await manual_quick_scan(user={"sub": "user-a"}, db=db)
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["three_day_count"], 1)
        self.assertEqual(result["three_day_remaining"], 0)
        self.assertTrue(result["three_day_complete"])
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(google.await_count, 3)
        for call in google.await_args_list:
            self.assertEqual(call.args[1], "user-a")
        for call in db.add.call_args_list:
            self.assertEqual(call.args[0].user_sub, "user-a")

    async def test_more_than_20_three_day_messages_warns_and_backfills(self):
        ids = [f"m{i}" for i in range(32)]
        db = self.fake_db()
        with patch("app.api.gmail_radar._request_google", new_callable=AsyncMock) as google:
            google.side_effect = [
                self.fake_list(ids), self.fake_list(ids[:20]),
                *(self.fake_metadata(msg) for msg in ids[:20]),
            ]
            result = await manual_quick_scan(user={"sub": "user-a"}, db=db)
        self.assertEqual(result["checked"], 20)
        self.assertEqual(result["three_day_count"], 32)
        self.assertEqual(result["three_day_remaining"], 12)
        self.assertFalse(result["three_day_complete"])
        self.assertEqual(google.await_count, 22)

        # The next explicit button skips previously processed IDs and
        # traverses the remaining 12, not the top 20 again.
        db2 = self.fake_db(seen=ids[:20])
        with patch("app.api.gmail_radar._request_google", new_callable=AsyncMock) as google:
            google.side_effect = [
                self.fake_list(ids),
                *(self.fake_metadata(msg) for msg in ids[20:]),
            ]
            next_result = await manual_three_day_backfill(
                user={"sub": "user-a"}, db=db2)
        self.assertEqual(next_result["checked"], 12)
        self.assertEqual(next_result["three_day_remaining"], 0)
        self.assertTrue(next_result["three_day_complete"])
        self.assertEqual(next_result["scan_kind"], "backfill")
        self.assertEqual(google.await_count, 13)
        self.assertEqual(google.await_args_list[0].kwargs["params"]["q"],
                         "newer_than:3d -in:spam -in:trash")

    async def test_repeated_quick_scan_avoids_existing_metadata_calls(self):
        ids = ["msg1", "msg2"]
        db = self.fake_db(seen=ids)
        with patch("app.api.gmail_radar._request_google", new_callable=AsyncMock) as google:
            google.side_effect = [self.fake_list(ids), self.fake_list(ids)]
            result = await manual_quick_scan(user={"sub": "user-a"}, db=db)
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["added"], 0)
        self.assertEqual(result["skipped"], 2)
        self.assertTrue(result["three_day_complete"])
        self.assertEqual(google.await_count, 2)

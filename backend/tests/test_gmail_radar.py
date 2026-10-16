import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.gmail_radar import classify_message, gmail_urls, manual_quick_scan
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

    async def test_scan_never_accepts_or_reads_other_user(self):
        db = MagicMock()
        res = MagicMock()
        res.scalar_one.return_value = True
        db.execute = AsyncMock(return_value=res)
        db.get = AsyncMock(side_effect=[
            GoogleConnection(
                user_sub="user-a", email="a@example.com",
                scopes="https://www.googleapis.com/auth/gmail.readonly"
            ),
            None,  # no prior scan summary
        ])
        db.scalar = AsyncMock(return_value=None)
        db.commit = AsyncMock()
        google_list = MagicMock()
        google_list.json.return_value = {"messages": [{"id": "msg1"}]}
        google_metadata = MagicMock()
        google_metadata.json.return_value = {
            "id": "msg1", "threadId": "thread1", "internalDate": "1790000000000",
            "payload": {"headers": [
                {"name": "Subject", "value": "繳費通知"},
                {"name": "From", "value": "bank@example.com"},
            ]}, "snippet": "請查看帳單"
        }
        with patch("app.api.gmail_radar._request_google", new_callable=AsyncMock) as google:
            google.side_effect = [google_list, google_metadata]
            result = await manual_quick_scan(user={"sub": "user-a"}, db=db)
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(google.await_count, 2)
        self.assertEqual(google.await_args_list[0].args[1], "user-a")
        self.assertEqual(google.await_args_list[1].args[1], "user-a")
        for call in db.add.call_args_list:
            entity = call.args[0]
            self.assertEqual(entity.user_sub, "user-a")

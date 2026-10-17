import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.gmail_radar import (
    classify_message, gmail_urls, manual_quick_scan, manual_three_day_backfill,
    manual_three_day_recheck,
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

    def test_new_actionable_account_security_alerts(self):
        examples = [
            ("偵測到異常登入：您的帳號", "", "security"),
            ("非本人交易警報：疑似盜刷", "", "security"),
            ("Security alert: unusual sign-in", "", "security"),
            ("您的帳號通知", "偵測到可疑活動，請至官方服務確認", "security"),
            ("Two-factor authentication disabled", "", "security"),
            ("密碼已變更", "", "security"),
            ("本期帳號通知", "Your payment was declined", "account"),
            ("訂閱即將續費：下月收取費用", "", "account"),
            ("帳號即將停用：付款失敗", "", "account"),
            ("Storage almost full", "", "account"),
            ("網路服務續訂費用調整", "", "account"),
            ("退款申請遭拒", "", "refund"),
            ("訂單付款失敗，請重新確認", "", "refund"),
            ("退款進度", "退款需要補件，請登入官方平台", "refund"),
            ("Your refund was denied", "", "refund"),
            ("政府案件待補件通知", "", "administrative"),
            ("學校請回覆：戶外教學同意書", "", "administrative"),
            ("公司待簽核：採購單", "", "administrative"),
            ("學校最新通知", "請繳交同意書", "administrative"),
            ("School action required", "", "administrative"),
        ]
        for subject, snippet, expected in examples:
            with self.subTest(subject=subject, snippet=snippet):
                self.assertEqual(classify_message(subject, snippet), expected)

    def test_real_project_freeze_notice_is_actionable(self):
        # 2026-10-17 regression from a real sender's subject, no body needed.
        actionable = (
            "Your paused Supabase project is being permanently frozen soon",
            "Your project will be permanently frozen",
            "Your project has been paused",
            "您的專案即將永久凍結",
        )
        for subject in actionable:
            with self.subTest(subject=subject):
                self.assertEqual(classify_message(subject, ""), "account")

        harmless = (
            ("Supa Update October 2026", "Everything we announced this month"),
            ("Your project report is ready", "Your team paused during a sprint"),
            ("Newsletter: Your project will be permanently frozen", "Tips and news"),
            ("您與「dynadot.com」分享了部分 Google 帳戶資料",
             "您曾使用 Google 帳戶登入，您目前不必採取任何行動"),
            ("已成功取回您的 Google 帳戶", "您已成功取回帳戶"),
            ("Google 驗證碼", "請使用此驗證碼"),
        )
        for subject, snippet in harmless:
            with self.subTest(subject=subject):
                self.assertIsNone(classify_message(subject, snippet))

    def test_ads_and_normal_account_messages_do_not_create_false_alerts(self):
        harmless = [
            ("限時優惠！升級帳號保障交易安全", "異常登入防護限時特惠"),
            ("會員優惠：付款提醒的實用攻略", "付款失敗時該怎麼辦"),
            ("電子報：安全警報與防詐技巧", "偵測到異常登入？立即買課"),
            ("優惠券：訂閱費用減半", "訂閱即將續費，領折扣碼"),
            ("Flash sale: suspicious sign-in protection", "Save 50%"),
            ("Newsletter: government action required", "read more"),
            ("特賣：帳單繳費通知優惠", "請參閱活動"),
            ("本週優惠", "您的退款失敗？教你領優惠碼"),
            ("重要通知", "您是否擔心異常登入？優惠方案立即購買"),
            ("Service update", "Unusual sign-in detected? Special offer this week"),
            ("登入驗證碼：123456", "這是您的驗證碼"),
            ("新的登入通知", "您剛剛已登入"),
            ("訂單成立通知", "訂單已付款成功"),
            ("退款成功通知", "退費已完成"),
            ("學校活動公告", "活動照片與課程回顧"),
            ("政府最新政策公告", "本期電子報內容"),
            ("帳號安全小提醒", "定期更新密碼以保護帳號"),
            ("訂閱成功", "歡迎使用我們的服務"),
        ]
        for subject, snippet in harmless:
            with self.subTest(subject=subject, snippet=snippet):
                self.assertIsNone(classify_message(subject, snippet))

    def test_strong_security_subject_survives_generic_promo_footer(self):
        self.assertEqual(
            classify_message("Security alert: unusual sign-in", "unsubscribe from updates"),
            "security",
        )

    def test_fraud_or_fee_alert_is_not_downgraded_to_generic_notice(self):
        self.assertEqual(
            classify_message("付款失敗：請更新您的帳號付款方式", ""),
            "account",
        )
        self.assertEqual(
            classify_message("信用卡異常交易：非本人交易", ""),
            "security",
        )
        self.assertEqual(
            classify_message("訂單取消：退款失敗", ""),
            "refund",
        )

    def test_third_party_access_or_changed_permissions_are_review_items(self):
        examples = (
            "第三方應用程式已取得您帳號的存取權限",
            "新的第三方應用程式授權通知",
            "您的應用程式權限已變更",
            "New app has access to your Google account",
            "App permissions changed",
            "Third-party app access granted",
        )
        for subject in examples:
            with self.subTest(subject=subject):
                self.assertEqual(classify_message(subject, ""), "authorization")

    def test_normal_authorization_and_ads_do_not_escalate(self):
        examples = (
            ("您的 Gmail 授權已完成", "登入正常"),
            ("登入驗證碼 123456", "請勿提供驗證碼"),
            ("您已成功登入", "Google 帳號登入成功"),
            ("Google 官方應用服務電子報", "新的第三方應用程式授權通知"),
            ("會員優惠：第三方應用程式存取安全服務", "現正促銷"),
            ("本週好康", "New app has access to your Google account! Save 30%"),
        )
        for subject, snippet in examples:
            with self.subTest(subject=subject):
                self.assertIsNone(classify_message(subject, snippet))

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

    async def test_explicit_recheck_reclassifies_seen_ids_without_deleting_cache(self):
        db = self.fake_db(seen=["msg1"])
        with patch("app.api.gmail_radar._request_google", new_callable=AsyncMock) as google:
            google.side_effect = [
                self.fake_list(["msg1"]), self.fake_metadata("msg1"),
            ]
            result = await manual_three_day_recheck(
                user={"sub": "user-a"}, db=db)
        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["scan_kind"], "recheck")
        self.assertEqual(result["three_day_remaining"], 0)
        self.assertEqual(google.await_count, 2)
        self.assertFalse(any(
            isinstance(call.args[0], __import__("app.models.gmail_radar", fromlist=["GmailRadarSeen"]).GmailRadarSeen)
            for call in db.add.call_args_list
        ))
        db.commit.assert_awaited_once()

    async def test_recheck_keeps_existing_life_item_and_status(self):
        db = self.fake_db(seen=["msg1"])
        existing = object()
        db.scalar = AsyncMock(return_value=existing)
        with patch("app.api.gmail_radar._request_google", new_callable=AsyncMock) as google:
            google.side_effect = [self.fake_list(["msg1"])]
            result = await manual_three_day_recheck(
                user={"sub": "user-a"}, db=db)
        self.assertEqual(result["added"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(google.await_count, 1)
        from app.models.gmail_radar import GmailRadarItem, GmailRadarSeen
        self.assertFalse(any(
            isinstance(call.args[0], (GmailRadarItem, GmailRadarSeen))
            for call in db.add.call_args_list
        ))

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

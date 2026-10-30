"""Offline LINE-V2-03 daily chat contract tests."""
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from app.services import line_v2 as v2
from app.services import line_v2_daily as daily

CFG = {"channel_secret":"test-secret","namespace":"stage","origin":"https://life.example.test","liff_id":"123-test"}
USER = {"sub":"owner","email":"owner@example.test","name":"owner"}
IDENTITY = "U" + "a" * 32


async def handle(name, command=None):
    return await daily.handle_daily(name, command or {"a":name}, IDENTITY, CFG, USER,
        object(), v2.make_token, v2.postback_action, v2._text_reply, v2.quick_reply)


class DailyMenuContract(IsolatedAsyncioTestCase):
    async def test_capture_is_chat_first_and_requires_confirmation(self):
        with patch.object(daily, "feature_gate", return_value=AsyncMock()):
            messages = await handle("capture.start")
        self.assertIn("在 LINE", messages[0]["text"])
        self.assertIn("確認才會真正寫入", messages[0]["text"])
        self.assertEqual(messages[0]["quickReply"]["items"][0]["action"]["uri"], "https://life.example.test/capture")

    async def test_search_choices_are_signed_owner_scoped(self):
        messages = await handle("search.start")
        actions = [x["action"] for x in messages[0]["quickReply"]["items"]]
        self.assertEqual([a["label"] for a in actions], ["筆記", "待辦", "購物", "進階搜尋"])
        claims = v2.read_token(actions[0]["data"], CFG, USER, IDENTITY)
        self.assertEqual((claims["a"], claims["k"]), ("search.kind", "notes"))

    async def test_tasks_render_explicit_complete_action(self):
        fake = {"items":[{"id":"t-1","title":"繳帳單","detail":"","date":None}],"has_more":False}
        with patch("app.api.line.lookup", new=AsyncMock(return_value=fake)):
            msg = await handle("tasks.list")
        self.assertEqual(msg[0]["type"], "flex")
        action = msg[0]["contents"]["contents"][0]["footer"]["contents"][0]["action"]
        self.assertEqual(v2.read_token(action["data"], CFG, USER, IDENTITY)["i"], "t-1")

    async def test_task_completion_reuses_domain_owner_checks(self):
        with patch.object(daily,"feature_gate",return_value=AsyncMock()),patch(
            "app.api.tasks.complete_task",new=AsyncMock()) as save:
            msg=await handle("tasks.complete",{"a":"tasks.complete","i":"t-1"})
        save.assert_awaited_once()
        self.assertIn("完成",msg[0]["text"])

    async def test_shopping_done_requires_explicit_true(self):
        with patch.object(daily,"feature_gate",return_value=AsyncMock()),patch(
            "app.api.shopping.update_shopping_item",new=AsyncMock()) as save:
            msg=await handle("shopping.set",{"a":"shopping.set","i":"i-1","b":True})
        save.assert_awaited_once()
        self.assertIn("購買",msg[0]["text"])
        with patch.object(daily,"feature_gate",return_value=AsyncMock()),patch(
            "app.api.shopping.update_shopping_item",new=AsyncMock()) as denied:
            msg=await handle("shopping.set",{"a":"shopping.set","i":"i-1","b":False})
        self.assertIn("無效",msg[0]["text"])
        denied.assert_not_awaited()

    async def test_calendar_failure_does_not_claim_empty(self):
        with patch("app.api.line.lookup",new=AsyncMock(return_value={"items":[],"has_more":False})),patch(
            "app.services.line_v2_daily._calendar_for",new=AsyncMock(side_effect=RuntimeError("down"))):
            msg=await handle("today.view")
        self.assertIn("暫時無法查詢",str(msg))
        self.assertNotIn("今日沒有行程",str(msg))

    async def test_calendar_reuses_google_adapter_and_user(self):
        with patch.object(daily,"feature_gate",return_value=AsyncMock()),patch(
            "app.api.google_integrations.list_calendar_events",
            new=AsyncMock(return_value={"events":[]})) as adapter:
            await daily._calendar_for(USER,object(),7)
        self.assertEqual(adapter.await_args.kwargs["limit"],5)
        self.assertEqual(adapter.await_args.kwargs["user"],USER)

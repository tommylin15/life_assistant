"""Bounded SQLite contract tests for LINE native capture and Life commit delegation."""
import uuid
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.db.session import Base
from app.models.line_capture import LineCapture
from app.models.shopping import ShoppingList
from app.services import line_capture as capture, line_v2 as v2

CFG = {"channel_secret": "local-test-key", "namespace": "stage",
       "origin": "https://life.example.test", "liff_id": "fake-liff"}
USER = {"sub": "owner", "name": "Owner", "email": "owner@example.test"}
IDENTITY = "U" + "a" * 32


class CaptureFlow(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.maker = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: Base.metadata.create_all(
                c, tables=[LineCapture.__table__, ShoppingList.__table__]))
        self.db = self.maker()
        self.counter = 0
        self.gate = patch.object(capture, "feature_gate", return_value=AsyncMock())
        self.gate.start()

    async def asyncTearDown(self):
        self.gate.stop()
        await self.db.close()
        await self.engine.dispose()

    async def message(self, content):
        self.counter += 1
        event = SimpleNamespace(id=uuid.uuid4().hex * 2, created_at=datetime.now(timezone.utc))
        return await capture.begin_capture(content, event, IDENTITY, CFG, USER, self.db)

    async def session(self):
        return (await self.db.scalars(select(LineCapture).order_by(
            LineCapture.created_at.desc()).limit(1))).first()

    async def post(self, cmd, extra=None, actor=IDENTITY, usr=USER, cfg=CFG, params=None):
        s = await self.session()
        token = v2.make_token(CFG, USER, IDENTITY, cmd, i=s.id, r=s.revision, **(extra or {}))
        return await v2.handle_postback({"type":"postback", "postback":{
            "data": token, **({"params": params} if params else {})}},
            actor, cfg, usr, self.db)

    async def test_noun_yields_choices_not_immediate_write(self):
        with patch.object(capture.inbox, "commit", new=AsyncMock()) as write:
            msgs = await self.message("牛奶")
            s = await self.session()
        self.assertEqual(msgs[0]["type"], "flex")
        controls = [x["action"] for x in msgs[0]["quickReply"]["items"]]
        self.assertIn("購物（建議）", [x["label"] for x in controls])
        self.assertEqual(s.source_text, "牛奶")
        self.assertIsNone(s.target)
        write.assert_not_awaited()

    async def test_selection_requires_owned_list_then_confirm_once(self):
        await self.message("牛奶")
        await self.post("capture.kind", {"k": "shopping"})
        incomplete = await self.post("capture.confirm")
        self.assertIn("先選擇", str(incomplete))
        self.db.add(ShoppingList(id="list-1", name="採買", user_sub="owner"))
        await self.db.commit()
        choices = await self.post("capture.list")
        self.assertIn("採買", str(choices))
        await self.post("capture.pick_list", {"k":"list-1"})
        with patch.object(capture.inbox, "commit", new=AsyncMock(return_value={
            "status":"COMPLETE", "results":[{"status":"CREATED","entity_id":"list-1"}]})) as write:
            confirmed=await self.post("capture.confirm")
            repeated=await self.post("capture.confirm")
        self.assertIn("已確認新增", str(confirmed))
        self.assertIn("已確認新增", str(repeated))
        write.assert_awaited_once()
        item=write.await_args.args[0].items[0]
        self.assertEqual(item.fields["shopping_list_id"], "list-1")
        self.assertEqual(item.fields["items"][0]["name"], "牛奶")
        self.assertNotIn("list_name", item.fields)

    async def test_cross_actor_namespace_and_expired_rejected(self):
        await self.message("重要筆記")
        s=await self.session()
        for actor, usr, cfg in [
            ("U" + "b"*32, USER, CFG),
            (IDENTITY, {"sub":"other"}, CFG),
            (IDENTITY, USER, {**CFG,"namespace":"prod"})
        ]:
            out=await self.post("capture.kind", {"k":"note"}, actor=actor, usr=usr, cfg=cfg)
            self.assertIn("失效", str(out))
        s.expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)
        await self.db.commit()
        out=await self.post("capture.kind", {"k":"note"})
        self.assertIn("過期", str(out))

    async def test_title_edit_consumes_message_without_creating_second_session(self):
        await self.message("繳水費")
        await self.post("capture.kind", {"k":"task"})
        await self.post("capture.edit", {"k":"title"})
        await self.message("繳管理費")
        sessions=(await self.db.scalars(select(LineCapture))).all()
        self.assertEqual(len(sessions),1)
        self.assertEqual(sessions[0].fields["title"],"繳管理費")
        self.assertIsNone(sessions[0].awaiting)

    async def test_calendar_requires_both_dates_and_valid_order(self):
        await self.message("看牙醫")
        await self.post("capture.kind", {"k":"calendar"})
        premature=await self.post("capture.confirm")
        self.assertIn("開始與結束",str(premature))
        await self.post("capture.start_at",params={"datetime":"2026-11-02T15:00"})
        await self.post("capture.end_at",params={"datetime":"2026-11-02T14:00"})
        invalid=await self.post("capture.confirm")
        self.assertIn("有效",str(invalid))
        await self.post("capture.end_at",params={"datetime":"2026-11-02T16:00"})
        s=await self.session()
        self.assertTrue(s.fields["start"].endswith("+08:00"))
        self.assertTrue(s.fields["end"].endswith("+08:00"))

    async def test_cancel_never_creates_formal_data(self):
        await self.message("牛奶")
        with patch.object(capture.inbox, "commit", new=AsyncMock()) as write:
            await self.post("capture.cancel")
            after=await self.post("capture.confirm")
        self.assertIn("已取消",str(after))
        write.assert_not_awaited()

    async def test_unknown_status_uses_fixed_receipt_not_retry(self):
        await self.message("水電")
        await self.post("capture.kind", {"k":"note"})
        with patch.object(capture.inbox, "commit", new=AsyncMock(return_value={
            "status":"PARTIAL","results":[{"status":"UNKNOWN"}]})) as write:
            first=await self.post("capture.confirm")
            another=await self.post("capture.confirm")
        self.assertIn("待確認",str(first))
        self.assertIn("待確認",str(another))
        write.assert_awaited_once()

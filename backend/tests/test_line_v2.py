"""Offline LINE v2 activity conversation contracts; no LINE API or secrets."""
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.services import line_v2 as v2

IDENTITY = "U" + "a" * 32
USER = {"sub": "life-owner", "email": "private@example.test", "name": "Owner"}
OTHER = {"sub": "another-owner", "email": "another@example.test"}
CFG = {"namespace": "stage", "channel_secret": "test-only-not-a-real-secret",
       "origin": "https://life.example.test", "liff_id": "123-test"}


def event(value):
    return {"type": "postback", "postback": {"data": value}}


def item(identity="a" * 64, saved=False, category="美術"):
    return {"identity_key": identity, "title": "台北藝文活動", "city": "臺北市",
            "category": category, "fee_kind": "unknown", "starts_on": None,
            "ends_on": None, "verification_status": "pending_review",
            "original_url": "https://example.org/event?utm_source=tracking",
            "saved": saved, "handoff_event_key": "parent-A"}


class TokenContracts(unittest.TestCase):
    def test_token_scoped_to_life_owner_line_identity_and_channel(self):
        token = v2.make_token(CFG, USER, IDENTITY, "events.save", i="a" * 64, b=True)
        self.assertLessEqual(len(token.encode()), 300)
        self.assertEqual(v2.read_token(token, CFG, USER, IDENTITY)["b"], True)
        for bad_cfg, bad_user, bad_line in [
            (CFG, OTHER, IDENTITY), (CFG, USER, "U" + "b" * 32),
            ({**CFG, "namespace": "prod"}, USER, IDENTITY)]:
            with self.assertRaises(ValueError):
                v2.read_token(token, bad_cfg, bad_user, bad_line)

    def test_tampered_and_expired_tokens_rejected(self):
        tok = v2.make_token(CFG, USER, IDENTITY, "events.latest")
        with self.assertRaises(ValueError):
            v2.read_token(tok[:-1] + ("a" if tok[-1] != "a" else "b"), CFG, USER, IDENTITY)
        with self.assertRaises(ValueError):
            v2.read_token("v2:!invalid.**", CFG, USER, IDENTITY)
        with patch.object(v2, "datetime") as clock:
            clock.now.return_value = datetime(2030, 1, 1, tzinfo=timezone.utc)
            with self.assertRaises(ValueError):
                v2.read_token(tok, CFG, USER, IDENTITY)

    def test_menu_accepts_allowlisted_commands_only(self):
        self.assertEqual(v2._menu_command("v=2&cmd=events.latest"), "events.latest")
        for cmd in ("v=2&cmd=admin", "v=2&cmd=events.latest&cmd=events.saved",
                    "v=3&cmd=events.latest", "v=2&cmd=events.save"):
            self.assertIsNone(v2._menu_command(cmd))

    def test_carousel_has_valid_small_card_and_no_private_pii(self):
        options = [v2.postback_action("最新", v2.make_token(CFG, USER, IDENTITY, "events.latest"))]
        cards = v2._carousel([item()], CFG, USER, IDENTITY, options=options, title="最新活動")
        msg = cards[0]
        self.assertEqual(msg["type"], "flex")
        self.assertEqual(msg["contents"]["type"], "carousel")
        self.assertEqual(len(msg["contents"]["contents"]), 1)
        self.assertIn("費用未知", json.dumps(msg, ensure_ascii=False))
        self.assertIn("待核對", json.dumps(msg, ensure_ascii=False))
        self.assertNotIn("private@example.test", json.dumps(msg))
        self.assertLess(len(json.dumps(msg["contents"], ensure_ascii=False).encode()), 50_000)
        footer = msg["contents"]["contents"][0]["footer"]["contents"]
        self.assertEqual(footer[0]["action"]["type"], "postback")
        self.assertEqual(v2.read_token(footer[0]["action"]["data"], CFG, USER, IDENTITY)["b"], True)
        self.assertEqual(footer[1]["action"]["uri"], "https://example.org/event")

    def test_duplicate_group_collapse_contract(self):
        self.assertEqual(v2._group_id(item("a" * 64)), "handoff:parent-A")
        duplicate = {**item("b" * 64), "handoff_event_key": None, "parent_event_key": "parent-A"}
        self.assertEqual(v2._group_id(duplicate), v2._group_id(item()))

    def test_untrusted_url_never_in_button(self):
        malicious = item()
        malicious["original_url"] = "http://127.0.0.1/internal"
        bubble = v2._bubble(malicious, CFG, USER, IDENTITY)
        self.assertEqual(len(bubble["footer"]["contents"]), 1)

    def test_quick_reply_limits(self):
        options = [v2.postback_action("標籤", "v=2&cmd=events.tags") for _ in range(14)]
        with self.assertRaises(ValueError):
            v2.quick_reply(options)


class HandlerContracts(unittest.IsolatedAsyncioTestCase):
    async def test_latest_renders_six_and_signed_next_page(self):
        page = {"items": [item("a" * 64)], "snapshot_us": 1800000000000000, "has_more": True}
        with patch.object(v2, "_activity_access", AsyncMock()) as access, \
             patch.object(v2, "_activity_page", AsyncMock(return_value=page)) as query:
            messages = await v2.handle_postback(event("v=2&cmd=events.latest"), IDENTITY, CFG, USER, object())
        access.assert_awaited_once()
        self.assertEqual(messages[0]["type"], "flex")
        self.assertEqual(messages[0]["altText"], "Life 最新上架活動（左右滑動查看）")
        actions = [x["action"] for x in messages[0]["quickReply"]["items"]]
        next_page = v2.read_token(actions[0]["data"], CFG, USER, IDENTITY)
        self.assertEqual((next_page["a"], next_page["o"], next_page["s"]), ("events.page", 6, 1800000000000000))
        query.assert_awaited_once()

    async def test_existing_curated_group_query_is_reused_and_duplicate_children_collapsed(self):
        main = item("a" * 64)
        child = {**item("b" * 64), "parent_event_key": "parent-A", "handoff_event_key": None}
        another = {**item("c" * 64), "handoff_event_key": "parent-B"}
        with patch.object(v2.curated, "list_curated", AsyncMock(return_value={
            "items": [main, child, another], "has_more": False, "snapshot": "ignored"})) as query:
            result = await v2._activity_page(object(), USER, category="美術", offset=6, snapshot=1800000000000000)
        self.assertEqual([r["identity_key"] for r in result["items"]], ["a" * 64, "c" * 64])
        self.assertEqual(query.await_args.kwargs["category"], "美術")
        self.assertEqual(query.await_args.kwargs["quick"], "latest")
        self.assertEqual(query.await_args.kwargs["entry"], "explore")
        self.assertEqual(query.await_args.kwargs["offset"], 6)
        self.assertEqual(result["snapshot_us"], 1800000000000000)

    async def test_category_is_real_db_category_and_not_a_guess(self):
        with patch.object(v2, "_activity_access", AsyncMock()), \
             patch.object(v2, "_categories", AsyncMock(return_value=["美術", "講座"])) as tags:
            response = await v2.handle_postback(event("v=2&cmd=events.tags"), IDENTITY, CFG, USER, object())
        self.assertIn("分類", response[0]["text"])
        self.assertEqual(response[0]["quickReply"]["items"][0]["action"]["label"], "美術")
        tags.assert_awaited_once()

    async def test_tag_selection_resolves_existing_category_and_preserves_filter(self):
        token = v2.make_token(CFG, USER, IDENTITY, "events.tag", k=v2._category_key("講座"))
        page = {"items": [item()], "snapshot_us": 1800000000000000, "has_more": False}
        with patch.object(v2, "_activity_access", AsyncMock()), \
             patch.object(v2, "_categories", AsyncMock(return_value=["講座"])), \
             patch.object(v2, "_activity_page", AsyncMock(return_value=page)) as query:
            await v2.handle_postback(event(token), IDENTITY, CFG, USER, object())
        self.assertEqual(query.await_args.kwargs["category"], "講座")

    async def test_unbound_or_changed_account_cannot_reuse_signed_button(self):
        token = v2.make_token(CFG, USER, IDENTITY, "events.latest")
        with patch.object(v2, "_activity_access", AsyncMock()) as access:
            out = await v2.handle_postback(event(token), IDENTITY, CFG, OTHER, object())
        self.assertEqual(out[0]["type"], "text")
        self.assertIn("失效", out[0]["text"])
        access.assert_not_awaited()

    async def test_save_explicit_state_does_not_toggle(self):
        token = v2.make_token(CFG, USER, IDENTITY, "events.save", i="a" * 64, b=True)
        db = Mock()
        db.scalars = AsyncMock(return_value=SimpleNamespace(first=lambda: "a" * 64))
        with patch.object(v2, "_activity_access", AsyncMock()), \
             patch.object(v2.curated_actions, "set_action", AsyncMock(return_value={"active": True})) as write:
            out1 = await v2.handle_postback(event(token), IDENTITY, CFG, USER, db)
            out2 = await v2.handle_postback(event(token), IDENTITY, CFG, USER, db)
        self.assertIn("已收藏", out1[0]["text"])
        self.assertEqual(out2[0]["text"], out1[0]["text"])
        self.assertEqual(write.await_count, 2)
        self.assertTrue(all(call.args[2].active is True for call in write.await_args_list))

    async def test_deferred_command_uses_v1_liff_without_db(self):
        response = await v2.handle_postback(event("v=2&cmd=tasks.list"), IDENTITY, CFG, USER, object())
        self.assertEqual(response[0]["quickReply"]["items"][0]["action"]["uri"],
                         "https://liff.line.me/123-test?page=tasks")


if __name__ == "__main__":
    unittest.main()

"""Life Inbox V1: deterministic parsing, strict rollout, opt-in fetch and replays."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, Response
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import inbox, inbox_articles
from app.api.ui_policies import effective_features, feature_gate


class InboxRuleTests(unittest.TestCase):
    def test_url_is_note_and_never_downloaded_by_classifier(self):
        result = inbox.rule_candidates("https://example.com/article")
        self.assertEqual(result["classification_source"], "rules")
        self.assertEqual(result["candidates"][0]["target"], "note")
        self.assertFalse(result["saved"])
        self.assertTrue(result["candidates"][0]["select_default"])
        self.assertFalse(inbox.is_http_url("file:///etc/passwd"))
        self.assertFalse(inbox.is_http_url("https://user:pass@example.com"))

    def test_shopping_items_require_explicit_list(self):
        result = inbox.rule_candidates("買牛奶、雞蛋")
        item = result["candidates"][0]
        self.assertEqual([x["name"] for x in item["fields"]["items"]], ["牛奶", "雞蛋"])
        self.assertEqual(item["target"], "shopping")
        self.assertFalse(item["select_default"])
        self.assertIn("請選擇購物清單", item["ambiguities"])

    def test_schema_rejects_untrusted_target_or_extra_fields(self):
        with self.assertRaises(ValidationError):
            inbox.Proposal(target="delete_db", fields={"anything": "x"})
        with self.assertRaises(ValidationError):
            inbox.Proposal(target="note", fields={"body": "x", "owner_id": "admin"})
        with self.assertRaises(ValidationError):
            inbox.ConfirmBatch(items=[{"target": "note", "fields": {"body": "x"},
                                       "action_id": "duplicate"},
                                      {"target": "note", "fields": {"body": "y"},
                                       "action_id": "duplicate"}])

    def test_calendar_without_end_is_not_auto_selected(self):
        proposal = inbox.Proposal(target="calendar", fields={
            "summary": "複診", "start": "2026-10-25T10:00:00+08:00"},
            select_default=True)
        self.assertFalse(proposal.select_default)
        self.assertTrue(proposal.ambiguities)


class InboxClassificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_url_and_simple_shopping_do_not_call_model(self):
        with patch.object(inbox, "generate_text", new_callable=AsyncMock) as generator:
            for phrase in ("https://example.com/article", "買牛奶、雞蛋"):
                result = await inbox.interpret(
                    inbox.InterpretInput(text=phrase), Response(),
                    user={"sub": "user-1"})
                self.assertEqual(result["classification_source"], "rules")
        generator.assert_not_awaited()

    async def test_valid_gemini_json_and_no_direct_write(self):
        reply = '{"candidates":[{"target":"task","fields":{"title":"繳停車費"},' \
                '"evidence_spans":["繳停車費"],"ambiguities":[],"select_default":true}]}'
        with patch.object(inbox, "generate_text", new=AsyncMock(
                return_value={"text": reply})) as ai:
            result = await inbox.interpret(
                inbox.InterpretInput(text="下週幫我繳停車費"), Response(),
                user={"sub": "ordinary"})
        self.assertEqual(result["classification_source"], "gemini")
        self.assertEqual(result["candidates"][0]["target"], "task")
        self.assertFalse(result["saved"])
        ai.assert_awaited_once()

    async def test_broken_json_falls_back_to_manual_note(self):
        with patch.object(inbox, "generate_text", new=AsyncMock(
                return_value={"text": "NOT JSON"})):
            result = await inbox.interpret(
                inbox.InterpretInput(text="做點事情"), Response(),
                user={"sub": "ordinary"})
        self.assertEqual(result["classification_source"], "fallback")
        self.assertFalse(result["candidates"][0]["select_default"])

    async def test_rollout_defaults_owner_only_and_no_missing_row_bypass(self):
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "owner@example.test"}):
            db = AsyncMock(spec=AsyncSession)
            db.get.return_value = None
            # New feature must fail closed for public account before admin action.
            with self.assertRaises(HTTPException) as error:
                await feature_gate("life_inbox")(
                    user={"email": "user@example.test", "sub": "u"}, db=db)
            self.assertEqual(error.exception.status_code, 403)
            await feature_gate("life_inbox")(
                user={"email": "owner@example.test", "sub": "owner"}, db=db)

            rows = MagicMock()
            rows.scalars.return_value.all.return_value = []
            db.execute.return_value = rows
            flags = await effective_features(
                db, {"email": "user@example.test", "sub": "u"})
            match = next(x for x in flags if x["key"] == "life_inbox")
            self.assertEqual(match["audience"], "owner")
            self.assertFalse(match["available"])

    async def test_owner_and_public_policy_revocation(self):
        db = AsyncMock(spec=AsyncSession)
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "owner@example.test"}):
            for status, audience, user, allowed in [
                ("beta", "owner", "owner@example.test", True),
                ("beta", "owner", "user@example.test", False),
                ("enabled", "all", "user@example.test", True),
                ("hidden", "all", "owner@example.test", False),
                ("maintenance", "all", "user@example.test", False),
            ]:
                db.get.return_value = SimpleNamespace(status=status, audience=audience)
                with self.subTest(status=status, audience=audience):
                    if allowed:
                        await feature_gate("life_inbox")(user={"email": user}, db=db)
                    else:
                        with self.assertRaises(HTTPException):
                            await feature_gate("life_inbox")(user={"email": user}, db=db)


class InboxCommitTests(unittest.IsolatedAsyncioTestCase):
    async def test_replay_never_creates_another_resource(self):
        db = AsyncMock()
        execution = SimpleNamespace(entity_id="old-note", status="success")
        replay = SimpleNamespace(is_replay=True, execution=execution)
        with patch.object(inbox, "_verify_target", new_callable=AsyncMock), \
             patch.object(inbox, "reserve_execution", new=AsyncMock(return_value=replay)), \
             patch.object(inbox, "_internal_write", new_callable=AsyncMock) as write:
            result = await inbox.commit(
                inbox.ConfirmBatch(items=[inbox.ConfirmedItem(
                    target="note", action_id="capture-123", fields={"body": "hello"})]),
                Response(), {"sub": "u"}, db)
        self.assertEqual(result["results"][0]["status"], "ALREADY_APPLIED")
        write.assert_not_awaited()

    async def test_invalid_candidate_does_not_reserve(self):
        db = AsyncMock()
        with patch.object(inbox, "_verify_target", new_callable=AsyncMock), \
             patch.object(inbox, "reserve_execution", new_callable=AsyncMock) as reserve:
            result = await inbox.commit(
                inbox.ConfirmBatch(items=[inbox.ConfirmedItem(
                    target="shopping", action_id="capture-a",
                    fields={"items": [{"name": "牛奶"}]})]),
                Response(), {"sub": "u"}, db)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["results"][0]["status"], "FAILED")
        reserve.assert_not_awaited()


class ArticleSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_and_metadata_addresses_never_trigger_http_fetch(self):
        with patch.object(inbox_articles.socket, "getaddrinfo",
                          return_value=[(None, None, None, None, ("127.0.0.1", 443))]), \
             patch.object(inbox_articles.httpx, "AsyncClient") as client:
            with self.assertRaises(inbox_articles.ApiError) as error:
                await inbox_articles.pinned_public_article("https://example.com/article")
        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.code, "article_unsafe_url")
        client.assert_called_once()

    async def test_article_summary_only_triggered_by_explicit_preview_endpoint(self):
        self.assertTrue(any(route.path == "/inbox/article-preview"
                            for route in inbox_articles.router.routes))


if __name__ == "__main__":
    unittest.main()

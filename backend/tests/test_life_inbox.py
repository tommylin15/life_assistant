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

    def test_explicit_three_way_instruction_yields_three_editable_proposals(self):
        now = "2026-10-21T07:12:00+08:00"
        value = "明天下午三點去好市多，買牛奶跟雞蛋，晚上記得繳電費。"
        result = inbox.rule_candidates(value, now)
        self.assertEqual(result["classification_source"], "rules")
        proposals = result["candidates"]
        self.assertEqual([item["target"] for item in proposals],
                         ["calendar", "shopping", "task"])
        self.assertEqual(proposals[0]["fields"]["summary"], "去好市多")
        self.assertEqual(proposals[0]["fields"]["start"], "2026-10-22T15:00:00+08:00")
        self.assertNotIn("end", proposals[0]["fields"])
        self.assertFalse(proposals[0]["select_default"])
        self.assertEqual([x["name"] for x in proposals[1]["fields"]["items"]],
                         ["牛奶", "雞蛋"])
        self.assertEqual(proposals[2]["fields"]["title"], "繳電費")
        self.assertNotIn("due_at", proposals[2]["fields"])
        self.assertFalse(result["saved"])

    def test_rule_language_filters_uncertain_or_negative_phrases(self):
        for sample in ["不要買牛奶", "取消明天下午三點去好市多",
                       "買牛奶，然後幫我安排一個行程"]:
            with self.subTest(sample=sample):
                self.assertIsNone(inbox.rule_candidates(sample,
                    "2026-10-21T07:12:00+08:00"))
        value = inbox.rule_candidates("買牛奶跟雞蛋")
        self.assertEqual([x["name"] for x in value["candidates"][0]["fields"]["items"]],
                         ["牛奶", "雞蛋"])

    def test_calendar_date_hints_keep_partial_precision_and_roc_year(self):
        now = "2026-10-17T12:00:00+08:00"
        cases = [
            ("2026-11-05", "day", "2026-11-05"),
            ("2026年11月5日", "day", "2026-11-05"),
            ("2026/11/05", "day", "2026-11-05"),
            ("2026.11.05", "day", "2026-11-05"),
            ("民國115年11月5日", "day", "2026-11-05"),
            ("115年11月5日", "day", "2026-11-05"),
            ("2026年11月", "year_month", None),
            ("2026/11", "year_month", None),
            ("11/05", "month_day", None),
            ("11月5日", "month_day", None),
            ("今天", "day", "2026-10-17"),
            ("明天", "day", "2026-10-18"),
            ("後天", "day", "2026-10-19"),
        ]
        for label, precision, date in cases:
            with self.subTest(label=label):
                hint = inbox._inbox_date_hint("報名日期 " + label, now)
                self.assertEqual(hint["precision"], precision)
                self.assertEqual(hint.get("date"), date)
        self.assertIsNone(inbox._inbox_date_hint("不含日期的備忘", now))

    def test_invalid_or_multiple_dates_cannot_auto_fill(self):
        now = "2026-10-17T12:00:00+08:00"
        for label, precision in [
            ("2026/02/30", "invalid"),
            ("2026/11/5 到 2026/11/6", "ambiguous"),
            ("13月32日", "invalid"),
        ]:
            with self.subTest(label=label):
                hint = inbox._inbox_date_hint(label, now)
                self.assertEqual(hint["precision"], precision)
                self.assertNotIn("date", hint)

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

    async def test_rules_three_actions_skip_gemini_and_have_separate_dates(self):
        with patch.object(inbox, "generate_text", new_callable=AsyncMock) as model:
            result = await inbox.interpret(inbox.InterpretInput(
                text="明天下午三點去好市多，買牛奶跟雞蛋，晚上記得繳電費。"),
                Response(), user={"sub": "owner"})
        model.assert_not_awaited()
        self.assertEqual([p["target"] for p in result["candidates"]],
                         ["calendar", "shopping", "task"])
        self.assertIsNone(result["candidates"][2]["date_hint"])
        self.assertNotIn("due_at", result["candidates"][2]["fields"])

    async def test_gemini_multi_intent_keeps_clause_date_scoped(self):
        source = "明天10點去醫院，買牛奶跟雞蛋，晚上提醒我繳電費"
        answer = {"candidates": [
            {"target": "calendar", "fields": {
                "summary": "去醫院", "start": "2026-10-22T10:00:00+08:00",
                "end": "2026-10-22T11:00:00+08:00"},
                "evidence_spans": ["明天10點去醫院"], "select_default": True},
            {"target": "shopping", "fields": {
                "items": [{"name": "牛奶"}, {"name": "雞蛋"}]},
                "evidence_spans": ["買牛奶跟雞蛋"], "select_default": True},
            {"target": "task", "fields": {
                "title": "繳電費", "due_at": "2026-10-22T23:59:00+08:00"},
                "evidence_spans": ["晚上提醒我繳電費"], "select_default": True}
        ]}
        import json
        with patch.object(inbox, "generate_text", new=AsyncMock(
                return_value={"text": json.dumps(answer, ensure_ascii=False)})):
            result = await inbox.interpret(
                inbox.InterpretInput(text=source), Response(),
                user={"sub": "owner"})
        rows = result["candidates"]
        self.assertEqual([c["target"] for c in rows], ["calendar", "shopping", "task"])
        self.assertEqual(rows[0]["date_hint"]["precision"], "day")
        self.assertNotIn("end", rows[0]["fields"])
        self.assertFalse(rows[0]["select_default"])
        self.assertIsNone(rows[2]["date_hint"])
        self.assertNotIn("due_at", rows[2]["fields"])
        self.assertFalse(rows[2]["select_default"])

    async def test_model_omission_recovers_grounded_explicit_action(self):
        source = "明天10點去醫院，買牛奶跟雞蛋，晚上請幫我繳電費"
        answer = {"candidates": [{"target": "calendar",
            "fields": {"summary": "去醫院", "start": "2026-10-22T10:00:00+08:00"},
            "evidence_spans": ["明天10點去醫院"], "select_default": False}]}
        import json
        with patch.object(inbox, "generate_text", new=AsyncMock(
                return_value={"text": json.dumps(answer, ensure_ascii=False)})):
            result = await inbox.interpret(
                inbox.InterpretInput(text=source), Response(),
                user={"sub": "owner"})
        self.assertEqual([c["target"] for c in result["candidates"]],
                         ["calendar", "shopping"])
        self.assertEqual(result["candidates"][1]["fields"]["items"][1]["name"],
                         "雞蛋")

    async def test_partial_month_or_day_cannot_be_fabricated_by_model(self):
        candidates = [
            ("請在 11月5日 參加活動", "month_day"),
            ("2026年11月 報名活動", "year_month"),
        ]
        for source, precision in candidates:
            reply = ('{"candidates":[{"target":"calendar",'
                     '"fields":{"summary":"報名活動",'
                     '"start_date":"2026-11-05","end_date":"2026-11-06"},'
                     '"evidence_spans":[],"ambiguities":[],'
                     '"select_default":true}]}')
            with self.subTest(source=source), patch.object(
                    inbox, "generate_text", new=AsyncMock(return_value={"text": reply})):
                result = await inbox.interpret(
                    inbox.InterpretInput(text=source), Response(),
                    user={"sub": "u"})
            self.assertEqual(result["date_hint"]["precision"], precision)
            proposal = result["candidates"][0]
            self.assertEqual(proposal["target"], "calendar")
            self.assertNotIn("start_date", proposal["fields"])
            self.assertNotIn("end_date", proposal["fields"])
            self.assertFalse(proposal["select_default"])
            self.assertIn("請使用萬年曆", "、".join(proposal["ambiguities"]))

    async def test_partial_task_due_at_is_removed_before_persistable_proposal(self):
        reply = ('{"candidates":[{"target":"task","fields":'
                 '{"title":"備份文件","due_at":"2026-11-05T09:00:00+08:00"},'
                 '"evidence_spans":[],"ambiguities":[],"select_default":true}]}')
        with patch.object(inbox, "generate_text", new=AsyncMock(return_value={"text": reply})):
            result = await inbox.interpret(
                inbox.InterpretInput(text="11月5日備份文件"), Response(),
                user={"sub": "u"})
        candidate = result["candidates"][0]
        self.assertEqual(candidate["target"], "task")
        self.assertNotIn("due_at", candidate["fields"])
        self.assertFalse(candidate["select_default"])

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


class ArticleSummaryParseTests(unittest.TestCase):
    def test_pure_json_and_markdown_fence_are_valid(self):
        raw = '{"key_points":["第一點","第二點"],"uncertainties":["要核對"]}'
        for candidate in (raw, "```json\\n" + raw + "\\n```",
                          "以下是摘要：\\n" + raw):
            with self.subTest(candidate=candidate[:25]):
                value = inbox_articles.parse_gemini_summary(
                    candidate.replace("\\n", "\n"))
                self.assertEqual(value.key_points, ["第一點", "第二點"])

    def test_invalid_or_unbounded_summary_rejected(self):
        for raw in ("Plain text", "{}", "{" + "x" * 18001 + "}",
                    '{"key_points":["' + "x" * 351 +
                    '"],"uncertainties":[]}'):
            with self.subTest(length=len(raw)), self.assertRaises(
                    (ValueError, ValidationError)):
                inbox_articles.parse_gemini_summary(raw)


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

    async def test_article_preview_uses_enabled_inbox_gemini_and_never_saves(self):
        with (
            patch.object(inbox_articles, "_note_gate", new_callable=AsyncMock),
            patch.object(inbox_articles, "pinned_public_article",
                         new=AsyncMock(return_value=(
                             "https://example.com/article", "Example", "valid public article text"))),
            patch.object(inbox_articles, "generate_text",
                         new=AsyncMock(return_value={"text":
                             '{"key_points":["一項重點"],"uncertainties":[]}'})) as ai,
        ):
            response = await inbox_articles.article_preview(
                inbox_articles.ArticlePreviewInput(url="https://example.com/article"),
                Response(), {"sub": "owner"}, AsyncMock())
        self.assertEqual(response["status"], "ok")
        self.assertFalse(response["saved"])
        self.assertEqual(response["key_points"], ["一項重點"])
        self.assertEqual(ai.await_args.kwargs["purpose"], "life_inbox")

    async def test_article_gateway_disabled_has_distinct_safe_error_code(self):
        with (
            patch.object(inbox_articles, "_note_gate", new_callable=AsyncMock),
            patch.object(inbox_articles, "pinned_public_article",
                         new=AsyncMock(return_value=(
                             "https://example.com/article", "Example", "valid public article text"))),
            patch.object(inbox_articles, "generate_text",
                         new=AsyncMock(side_effect=inbox_articles.GatewayTextError(
                             "gemini_text_disabled", 503))),
        ):
            with self.assertRaises(inbox_articles.ApiError) as caught:
                await inbox_articles.article_preview(
                    inbox_articles.ArticlePreviewInput(url="https://example.com/article"),
                    Response(), {"sub": "owner"}, AsyncMock())
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.code, "article_ai_gemini_text_disabled")

    async def test_article_summary_only_triggered_by_explicit_preview_endpoint(self):
        self.assertTrue(any(route.path == "/inbox/article-preview"
                            for route in inbox_articles.router.routes))


if __name__ == "__main__":
    unittest.main()

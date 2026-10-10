import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.api.curated_actions import ActionWrite, calendar_payload, set_action
from app.api.tasks import _require_task, list_tasks
from app.models.curated_actions import CuratedPersonalAction
from app.models.task import Task


class ActivityActionTests(unittest.IsolatedAsyncioTestCase):
    def item(self):
        return SimpleNamespace(identity_key="a"*64, title="活動", original_url="https://example.org/e",
            starts_on=date(2026, 10, 12), ends_on=date(2026, 10, 15), registration_deadline=None,
            handoff_event_key="main:e", parent_event_key=None, handoff_details={})

    def test_calendar_information_is_transparent_and_date_range_exclusive(self):
        payload = calendar_payload(self.item(), "calendar_info", ActionWrite(active=True))
        self.assertEqual(payload["transparency"], "transparent")
        self.assertEqual(payload["end"], {"date":"2026-10-16"})
        self.assertEqual(payload["reminders"]["overrides"], [])

    def test_unknown_registration_time_cannot_schedule_reminders(self):
        with self.assertRaises(HTTPException) as ctx:
            calendar_payload(self.item(), "reminder", ActionWrite(active=True))
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_owned_tasks_are_hidden_from_other_account(self):
        db = AsyncMock()
        db.get.return_value = Task(id="x", title="私人活動", user_sub="owner")
        with self.assertRaises(HTTPException) as ctx:
            await _require_task(db, "x", {"sub":"other"})
        self.assertEqual(ctx.exception.status_code, 404)
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result
        await list_tasks({"sub":"other"}, db)
        sql = str(db.execute.call_args.args[0])
        self.assertIn("tasks.user_sub IS NULL OR tasks.user_sub =", sql)

    async def test_task_retry_does_not_create_another_task(self):
        db = AsyncMock()
        db.add = MagicMock()
        item = self.item()
        body = ActionWrite(active=True)
        previous = CuratedPersonalAction(user_sub="u", activity_id=item.identity_key, kind="task",
            active=True, payload=body.model_dump(mode="json"), entity_id="existing")
        db.get.side_effect = [item, previous]
        result = await set_action(item.identity_key, "task", body, {"sub":"u"}, db)
        self.assertTrue(result["unchanged"])
        db.add.assert_not_called()

    async def test_google_failure_never_marks_action_successful(self):
        db = AsyncMock()
        db.add = MagicMock()
        item = self.item()
        db.get.side_effect = [item, None]
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result
        with patch("app.api.curated_actions._request_google", AsyncMock(side_effect=HTTPException(409, "Reconnect"))):
            with self.assertRaises(HTTPException):
                await set_action(item.identity_key, "calendar_info", ActionWrite(active=True), {"sub":"u"}, db)
        db.commit.assert_not_awaited()

    async def test_cancel_retains_calendar_group_for_reactivation(self):
        db = AsyncMock()
        db.add = MagicMock()
        item = self.item()
        previous = CuratedPersonalAction(user_sub="u", activity_id=item.identity_key,
            kind="calendar_info", active=True, payload={"calendar_group": "group"},
            entity_id="old", updated_at=datetime.now(timezone.utc))
        db.get.side_effect = [item, previous]
        db.scalar.return_value = None
        with patch("app.api.curated_actions._request_google", AsyncMock()) as request:
            await set_action(item.identity_key, "calendar_info", ActionWrite(active=False), {"sub":"u"}, db)
        self.assertEqual(previous.payload["calendar_group"], "group")
        self.assertFalse(previous.active)
        self.assertEqual(request.call_args.args[3], "DELETE")

    async def test_calendar_reactivation_gets_new_id_after_cancel(self):
        db = AsyncMock()
        item = self.item()
        actions = []
        db.add = MagicMock(side_effect=lambda value: actions.append(value) if isinstance(value, CuratedPersonalAction) else None)
        db.get.side_effect = lambda model, key: item if model.__name__ == "CuratedActivity" else (actions[0] if actions else None)
        def query(statement, *args):
            result = MagicMock()
            result.scalars.return_value.all.return_value = actions if "curated_personal_actions" in str(statement) else []
            return result
        db.execute.side_effect = query
        db.scalar.return_value = None
        async def google(*args, **kwargs):
            return SimpleNamespace(status_code=404 if args[3] == "GET" else 200)
        with patch("app.api.curated_actions._request_google", AsyncMock(side_effect=google)):
            first = await set_action(item.identity_key, "calendar_info", ActionWrite(active=True), {"sub":"u"}, db)
            await set_action(item.identity_key, "calendar_info", ActionWrite(active=False), {"sub":"u"}, db)
            second = await set_action(item.identity_key, "calendar_info", ActionWrite(active=True), {"sub":"u"}, db)
        self.assertNotEqual(first["entity_id"], second["entity_id"])

import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api.curated import (
    CuratedActivity, _activity_filters, _group_key_value,
    _group_key, REGIONS, TAIPEI,
)
from app.api.curated_actions import ActionWrite, _task_due, calendar_payload, calendar_unchanged


class CuratedV3UnitTest(unittest.TestCase):
    def test_parent_key_and_legacy_fallback(self):
        child = SimpleNamespace(parent_event_key="p-1", handoff_event_key="c-1", identity_key="a")
        main = SimpleNamespace(parent_event_key=None, handoff_event_key="p-1", identity_key="b")
        legacy = SimpleNamespace(parent_event_key=None, handoff_event_key=None, identity_key="c")
        self.assertEqual(_group_key_value(child), _group_key_value(main))
        self.assertEqual(_group_key_value(legacy), "legacy:c")

    def test_group_query_is_database_side(self):
        sql = str(select(_group_key()).compile(dialect=postgresql.dialect()))
        self.assertIn("parent_event_key", sql)
        self.assertIn("handoff_event_key", sql)

    def test_keyword_organizer_location_summary_and_region_are_db_filters(self):
        stmt = _activity_filters(
            select(CuratedActivity), entry="explore", quick="next_30",
            keyword="藝術", region="north", city=None, district=None,
            category=None, fee_kind=None, starts_from=None,
            today=date(2026, 10, 11), saved_only=False, user_sub="owner",
        )
        compiled = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
        self.assertIn("ILIKE", compiled.upper())
        self.assertIn("organizer", compiled)
        self.assertIn("venue", compiled)
        self.assertIn("summary", compiled)
        self.assertIn("city IN", compiled)
        self.assertIn("starts_on", compiled)
        self.assertIn("臺北市", REGIONS["north"])

    def test_event_period_overlap_uses_end_date(self):
        stmt = _activity_filters(
            select(CuratedActivity), entry="explore", quick="weekend",
            keyword=None, region=None, city=None, district=None,
            category=None, fee_kind=None, starts_from=None,
            today=date(2026, 10, 11), saved_only=False, user_sub="owner",
        )
        sql = str(stmt.compile(dialect=postgresql.dialect()))
        self.assertIn("ends_on", sql)
        self.assertIn("starts_on", sql)

    def test_next_7_and_30_include_ongoing_cross_day_events(self):
        for quick in ("next_7", "next_30"):
            with self.subTest(quick=quick):
                stmt = _activity_filters(
                    select(CuratedActivity), entry="explore", quick=quick,
                    keyword=None, region=None, city=None, district=None,
                    category=None, fee_kind=None, starts_from=None,
                    today=date(2026, 10, 14), saved_only=False, user_sub="owner",
                )
                sql = str(stmt.whereclause.compile(dialect=postgresql.dialect()))
                self.assertIn("starts_on", sql)
                self.assertIn("ends_on", sql)
                self.assertIn(" BETWEEN ", sql)
                self.assertIn(" AND ", sql)
                self.assertIn(" OR ", sql)

    def test_default_opportunities_exclude_expired_deadlines_and_cancellations(self):
        base = dict(
            entry="opportunities", quick="latest", keyword=None, region=None,
            city=None, district=None, category=None, fee_kind=None,
            starts_from=None, today=date(2026, 10, 11), user_sub="owner",
        )
        ordinary_query = _activity_filters(
            select(CuratedActivity), saved_only=False, **base,
        )
        saved_query = _activity_filters(
            select(CuratedActivity), saved_only=True, **base,
        )
        # Inspect predicates only, not SELECT columns (which include these
        # fields even when the saved-only filters correctly omit them).
        ordinary = str(ordinary_query.whereclause.compile(dialect=postgresql.dialect()))
        saved = str(saved_query.whereclause.compile(dialect=postgresql.dialect()))
        # Normal opportunities respect a known deadline and cancellation;
        # saved history remains accessible after its action window expires.
        self.assertIn("registration_deadline", ordinary)
        self.assertIn("registration_status", ordinary)
        self.assertNotIn("registration_deadline", saved)
        self.assertNotIn("registration_status", saved)

    def test_calendar_source_url_and_transparent_exclusive_end(self):
        item = SimpleNamespace(
            title="測試活動",
            original_url="https://events.example.com/info",
            starts_on=date(2026, 11, 10), ends_on=date(2026, 11, 12),
            handoff_details={"registration_url": "https://events.example.com/register",
                             "venue": "台北市"},
        )
        result = calendar_payload(item, "calendar_info", ActionWrite(active=True))
        self.assertEqual(result["start"], {"date": "2026-11-10"})
        self.assertEqual(result["end"], {"date": "2026-11-13"})
        self.assertEqual(result["transparency"], "transparent")
        self.assertEqual(result["reminders"], {"useDefault": False, "overrides": []})
        self.assertEqual(result["location"], "台北市")
        self.assertTrue(result["description"].startswith("活動網址：https://events.example.com/register"))

    def test_calendar_edit_protection_checks_user_editable_fields(self):
        baseline = {
            "summary": "活動日期參考：測試",
            "description": "活動網址：https://events.example.com",
            "location": "台北",
            "start": {"date": "2026-11-10"},
            "end": {"date": "2026-11-11"},
        }
        self.assertTrue(calendar_unchanged(
            {**baseline, "start": {"date": "2026-11-10", "timeZone": "Asia/Taipei"}},
            baseline,
        ))
        self.assertFalse(calendar_unchanged({**baseline, "summary": "我的編輯"}, baseline))
        self.assertFalse(calendar_unchanged({**baseline, "location": "另一個地址"}, baseline))
        self.assertFalse(calendar_unchanged(
            {**baseline, "start": {"date": "2026-11-12"}}, baseline
        ))

    def test_task_due_requires_user_choice(self):
        item = SimpleNamespace(registration_deadline=datetime(2026, 12, 1, tzinfo=timezone.utc),
                               handoff_details={})
        self.assertIsNone(_task_due(item, ActionWrite(active=True)))
        chosen = ActionWrite(active=True, task_due_choice="deadline")
        self.assertEqual(_task_due(item, chosen), item.registration_deadline)


if __name__ == "__main__":
    unittest.main()

"""Culture Ministry public JSON adapter contracts; never fetch the live endpoint."""
from datetime import date
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo

from app.services.free_events_moc_adapter import normalize_moc_record


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/free_events_moc_offline.py"


class FreeEventMoCAdapterTests(unittest.TestCase):
    def sample(self):
        return {
            "UID": "record-123",
            "title": "免費演講（活動標題，不代表免票）",
            "masterUnit": ["市立文化館"],
            "sourceWebPromote": "https://culture.example.tw/show/123",
            "webSales": "https://tickets.example.tw/show/123",
            "showinfo": [
                {
                    "time": "2026/10/25 14:30:00",
                    "endTime": "2026/10/25 16:30:00",
                    "locationName": "市立文化館",
                    "onSales": "N",
                    "price": "免費",
                },
                {
                    "time": "2026/10/26 14:30:00",
                    "endTime": "2026/10/26 16:30:00",
                    "locationName": "市立文化館",
                    "onSales": "Y",
                    "price": "早鳥100",
                },
            ],
        }

    def test_all_sessions_remain_distinct_and_local_clock_explicit(self):
        item = normalize_moc_record(self.sample())
        self.assertEqual(len(item.sessions), 2)
        self.assertNotEqual(item.sessions[0].session_key, item.sessions[1].session_key)
        self.assertEqual(item.sessions[0].starts_at.hour, 14)
        self.assertEqual(item.sessions[0].starts_at.tzinfo, ZoneInfo("Asia/Taipei"))
        self.assertEqual(item.sessions[0].ends_at.hour, 16)
        self.assertEqual(item.organizer_name, "市立文化館")

    def test_moc_free_price_words_do_not_claim_free_or_open(self):
        item = normalize_moc_record(self.sample())
        for session in item.sessions:
            opportunity = session.opportunities[0]
            self.assertEqual(opportunity.fee_kind, "unknown")
            self.assertEqual(opportunity.registration_status, "unannounced")
            self.assertIsNone(opportunity.opens_at)
            self.assertIsNone(opportunity.closes_at)
            self.assertFalse(opportunity.official_verified)
            self.assertFalse(item.official_verified)

    def test_unknown_and_date_only_times_do_not_infer_hours(self):
        data = self.sample()
        data["showinfo"] = [{
            "time": "2026/10/25",
            "endTime": "2026/10/26",
            "onSales": False, "price": "免費",
        }]
        item = normalize_moc_record(data)
        session = item.sessions[0]
        self.assertEqual(session.starts_on, date(2026, 10, 25))
        self.assertIsNone(session.ends_on_exclusive)
        self.assertIsNone(session.starts_at)
        self.assertIsNone(session.ends_at)

    def test_invalid_or_non_https_source_links_are_not_upgraded(self):
        data = self.sample()
        data["sourceWebPromote"] = "http://culture.example.tw"
        data["webSales"] = "http://tickets.example.tw"
        item = normalize_moc_record(data)
        self.assertEqual(item.source_url, "https://data.gov.tw/dataset/6478")
        self.assertIsNone(item.sessions[0].opportunities[0].registration_url)

    def test_missing_uid_title_and_invalid_time_rejected(self):
        for change in [
            {"UID": ""},
            {"title": ""},
            {"showinfo": [{"time": "tomorrow 9AM"}]},
            {"showinfo": "not a list"},
        ]:
            data = self.sample()
            data.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                normalize_moc_record(data)

    def test_duplicate_identical_sessions_collapse_without_fabrication(self):
        data = self.sample()
        data["showinfo"] = [data["showinfo"][0], data["showinfo"][0]]
        self.assertEqual(len(normalize_moc_record(data).sessions), 1)

    def test_cli_emits_only_quarantined_manifest_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "moc.json"
            path.write_text(json.dumps([self.sample()], ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CLI), str(path)],
                cwd=ROOT, capture_output=True, text=True, timeout=15, check=True,
            )
        report = json.loads(result.stdout)
        self.assertEqual(report["rejected_by_adapter"], 0)
        self.assertEqual(report["status_counts"], {"needs_official_review": 1})
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["database_writes"], 0)
        self.assertEqual(report["ai_calls"], 0)


if __name__ == "__main__":
    unittest.main()

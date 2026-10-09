"""Bounded, official-only live source contracts; all HTTP mocked for CI."""
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import AsyncMock, patch

from app.services.free_events_moc_adapter import normalize_moc_record
from scripts.run_free_events_moc_batch import (
    DATASET_ENDPOINT, MAX_ADMISSION, MAX_RESPONSE_BYTES, SourceBatchError,
    choose_bounded_sample, fetch_moc_dataset, parse_moc_response,
)


class FreeEventsLiveBatchTests(unittest.TestCase):
    def test_only_published_json_source_is_hard_coded(self):
        self.assertEqual(DATASET_ENDPOINT,
            "https://cloud.culture.tw/frontsite/trans/SearchShowAction.do"
            "?method=doFindTypeJ&category=all")

    def test_actual_official_camelcase_show_info_parses_sessions(self):
        item = {
            "UID": "published-sample",
            "title": "藝文展覽",
            "masterUnit": ["文化館"],
            "showInfo": [{
                "time": "2026/10/11 14:00:00",
                "endTime": "2026/10/11 17:00:00",
                "locationName": "國家文化館",
                "onSales": "N",
                "price": "免費",
            }],
        }
        candidate = normalize_moc_record(item)
        self.assertEqual(len(candidate.sessions), 1)
        self.assertEqual(candidate.sessions[0].venue, "國家文化館")
        opp = candidate.sessions[0].opportunities[0]
        self.assertEqual(opp.fee_kind, "unknown")
        self.assertIsNone(opp.opens_at)
        self.assertFalse(opp.official_verified)

    def test_reject_html_and_oversized_unbounded_payload(self):
        for data in [b"<!doctype html>", b'{"not":"a list"}', b'[[123]]',
                     b"x" * (MAX_RESPONSE_BYTES + 1)]:
            with self.subTest(first=data[:20]), self.assertRaises(SourceBatchError):
                parse_moc_response(data)

    def test_rotating_sample_is_bounded_and_repeatable(self):
        rows = [{"UID": str(i)} for i in range(MAX_ADMISSION * 3 + 2)]
        date = datetime(2026, 10, 9, 4, tzinfo=timezone.utc)
        a = choose_bounded_sample(rows, date)
        b = choose_bounded_sample(rows, date)
        self.assertEqual(a, b)
        self.assertEqual(len(a), MAX_ADMISSION)
        self.assertEqual(len({r["UID"] for r in a}), MAX_ADMISSION)
        self.assertNotEqual(a, choose_bounded_sample(
            rows, datetime(2026, 10, 10, 4, tzinfo=timezone.utc)
        ))

    def test_empty_payload_is_valid_json_but_not_valid_source_observation(self):
        self.assertEqual(parse_moc_response(b"[]"), [])
        self.assertEqual(
            parse_moc_response(json.dumps([{"UID": "1"}]).encode()),
            [{"UID": "1"}],
        )


if __name__ == "__main__":
    unittest.main()

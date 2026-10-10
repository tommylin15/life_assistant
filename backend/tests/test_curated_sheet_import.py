"""Pure Sheet -> curated contract tests; never reads real Drive or production DB."""
import unittest
from app.api.curated import identity
from scripts.import_curated_from_sheet import parse_rows


HEADERS = [
    "event_key", "活動名稱", "pool狀態", "主辦官方活動網址", "報名網址",
    "縣市", "分類", "重要性星等", "開始時間(台北)", "結束時間(台北)",
    "不可退實付C(NTD)", "可驗證福利V(NTD)", "主會場入場費狀態", "精選理由",
    "報名需求", "報名狀態", "限量優惠狀態",
]


def row(**fields):
    return [fields.get(header, "") for header in HEADERS]


class CuratedSheetImportTests(unittest.TestCase):
    def test_approved_records_map_to_stable_identity_and_preserve_unknowns(self):
        sheet = [HEADERS, row(**{
            "event_key": "organizer:2026:event:day1", "活動名稱": "選定活動",
            "pool狀態": "selected", "主辦官方活動網址": "https://example.org/e?utm_source=ad&n=1",
            "重要性星等": "5", "縣市": "臺南市",
            "開始時間(台北)": "2026-10-12 09:00", "不可退實付C(NTD)": "0",
            "主會場入場費狀態": "免費入場", "可驗證福利V(NTD)": "500",
        }), row(**{"event_key": "old", "活動名稱": "過期草稿",
                  "pool狀態": "expired", "主辦官方活動網址": "https://example.org/old"})]
        items, invalid, filtered = parse_rows(sheet)
        self.assertEqual((len(items), invalid, filtered), (1, [], 1))
        self.assertEqual(items[0].fee_kind, "free")
        self.assertEqual(items[0].original_url, "https://example.org/e?n=1")
        self.assertEqual(items[0].starts_on.isoformat(), "2026-10-12")
        self.assertEqual(identity(items[0]), identity(parse_rows(sheet)[0][0]))
        self.assertNotIn("registration_required", items[0].model_fields_set)

    def test_missing_official_and_registration_link_is_not_published(self):
        sheet = [HEADERS, row(**{"event_key":"ok","活動名稱":"已核選",
                    "pool狀態":"selected","主辦官方活動網址":"https://example.org/a",
                    "重要性星等":"3"}),
                 row(**{"event_key":"missing","活動名稱":"缺少網址",
                    "pool狀態":"selected","重要性星等":"5"})]
        items, invalid, filtered = parse_rows(sheet)
        self.assertEqual((len(items), invalid, filtered), (1, [3], 0))

    def test_duplicate_source_keys_fail_closed(self):
        common = {"event_key":"repeat","活動名稱":"重複活動",
                  "pool狀態":"selected","重要性星等":"5",
                  "主辦官方活動網址":"https://example.org/a"}
        with self.assertRaisesRegex(ValueError, "duplicate_approved_event_key"):
            parse_rows([HEADERS,row(**common),row(**common)])

    def test_unverified_dates_stay_unknown_but_non_numeric_fees_are_rejected(self):
        invalid = {"event_key":"bad","活動名稱":"活動",
                  "pool狀態":"selected","重要性星等":"5",
                  "主辦官方活動網址":"https://example.org/a"}
        with self.subTest(kind="unverified_fee"):
            self.assertEqual(parse_rows([HEADERS, row(**(invalid | {"不可退實付C(NTD)":"價格待核"}))])[1], [2])
        with self.subTest(kind="unverified_activity_date"):
            items, rejected, _ = parse_rows([HEADERS, row(**(invalid | {
                "開始時間(台北)": "報名2026-10-14 12:00；活動場次待核",
                "結束時間(台北)": "2026-10-15（場次結束日待核）",
            }))])
            self.assertEqual(rejected, [])
            self.assertEqual(len(items), 1)
            self.assertIsNone(items[0].starts_on)
            self.assertIsNone(items[0].ends_on)


if __name__ == "__main__":
    unittest.main()

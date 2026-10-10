"""Fixed handoff contract and receipt version fencing; no real Drive writes."""
import os
import hashlib
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from scripts.import_curated_from_sheet import parse_rows, validate_record, SheetClient, run_import, SHEET_ID
from app.services.curated_handoff import HEADERS


def record(**updates):
    value = {k: "" for k in HEADERS}
    value.update(event_key="official:show:2026", record_type="main", title="活動測試",
                 parent_event_key="official:theme:2026", organizer="測試主辦", opportunity_type="一般活動", evidence_summary="官方核證",
                 official_url="https://example.org/event", importance_star="5",
                 verified_at_tpe="2026-10-10T09:00:00+08:00", handoff_status="READY",
                 handoff_updated_at_tpe="2026-10-10T09:00:00+08:00")
    value.update(updates)
    value["content_hash"] = hashlib.sha256(value["title"].encode()).hexdigest()
    return value


def sheet(*records):
    return [list(HEADERS), *[[r[k] for k in HEADERS] for r in records]]


class HandoffContractTests(unittest.TestCase):
    def test_sheet_hash_is_producer_owned_and_zero_is_not_unknown(self):
        value = record(nonrefundable_cost_ntd="0")
        self.assertEqual(validate_record(value).nonrefundable_cost_ntd, 0)
        self.assertIsNone(validate_record(record()).nonrefundable_cost_ntd)

    def test_strict_header_duplicate_keys_and_hash(self):
        value = record()
        self.assertEqual(parse_rows(sheet(value)), [value])
        with self.assertRaisesRegex(ValueError, "duplicate_event_key"):
            parse_rows(sheet(value, value))
        with self.assertRaisesRegex(ValueError, "header_contract"):
            parse_rows([["old 精選活動"]])
        value["content_hash"] = "not a SHA256"
        with self.assertRaisesRegex(ValueError, "invalid_content_hash"):
            validate_record(value)

    def test_unknowns_and_date_only_are_not_midnight_or_zero(self):
        item = validate_record(record(start_at_tpe="2026-10-12"))
        self.assertEqual(item.curated().starts_on.isoformat(), "2026-10-12")
        self.assertIsNone(item.nonrefundable_cost_ntd)
        self.assertIsNone(item.registration_open_at_tpe)
        self.assertEqual(item.curated().fee_kind, "unknown")
        self.assertNotIn("T", item.model_dump(mode="json")["start_at_tpe"])

    def test_reject_unsafe_links_times_and_missing_parent(self):
        for updates in ({"official_url": "http://example.org/event"},
                        {"registration_open_at_tpe": "2026-10-12T10:00:00"},
                        {"parent_event_key": ""}, {"organizer": ""}, {"opportunity_type": "未知"},
                        {"importance_star": "2"}, {"nonrefundable_cost_ntd": "unknown"}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                validate_record(record(**updates))

    def test_general_activity_and_date_only_registration_follow_sheet(self):
        item = validate_record(record(parent_event_key="official:show:2026",
            registration_open_at_tpe="2026-10-12", registration_deadline_at_tpe="2026-10-14"))
        self.assertFalse(item.curated().limited_offer)
        self.assertIsNone(item.curated().registration_deadline)
        self.assertEqual(item.model_dump(mode="json")["registration_deadline_at_tpe"], "2026-10-14")


class ReceiptTests(unittest.IsolatedAsyncioTestCase):
    async def test_changed_or_moved_rows_do_not_receive_stale_ack(self):
        original = record()
        changed = record(title="新版活動")
        client = SheetClient()
        client.read = AsyncMock(return_value=sheet(changed))
        client.request = AsyncMock()
        self.assertFalse(await client.receipt(original, "CREATED"))
        client.request.assert_not_awaited()
        other = record(event_key="other:show")
        acked = dict(original, handoff_status="ACKED", life_import_result="CREATED", life_ack_at_tpe="2026-10-10T09:00:00+08:00")
        client.read = AsyncMock(side_effect=[sheet(other, original), sheet(other, acked)])
        self.assertTrue(await client.receipt(original, "CREATED"))
        ranges = client.request.call_args.kwargs["json"]["data"]
        self.assertEqual(ranges[0]["range"], "'交接資料'!Z3")
        self.assertEqual(ranges[1]["range"], "'交接資料'!AB3:AD3")
        self.assertEqual(ranges[1]["values"][0][1], "CREATED")

    async def test_acked_row_is_verified_again_in_database(self):
        newer = record(title="更新後的活動")
        newer.update(handoff_status="ACKED", life_import_result="CREATED")
        client = AsyncMock()
        client.read.return_value = sheet(newer)
        client.receipt.return_value = True
        sessions = MagicMock()
        sessions.return_value.__aenter__.return_value = AsyncMock()
        with patch.dict(os.environ, {"LIFE_CURATED_SHEET_ID": SHEET_ID, "LIFE_CURATED_IMPORT_APPLY": "1"}), patch(
                "scripts.import_curated_from_sheet.upsert_handoff", AsyncMock(return_value="UPDATED")) as upsert:
            result = await run_import(client, sessions)
        upsert.assert_awaited_once()
        self.assertEqual(result["updated"], 1)
        client.receipt.assert_awaited_once_with(newer, "UPDATED")

    async def test_error_receipt_leaves_success_result_empty(self):
        original = record(handoff_status="ACKED", life_import_result="CREATED", life_ack_at_tpe="2026-10-10T09:00:00+08:00")
        failed = dict(original, handoff_status="ERROR", life_ack_at_tpe="", life_import_result="", life_error="invalid_handoff_record")
        client = SheetClient()
        client.read = AsyncMock(side_effect=[sheet(original), sheet(failed)])
        client.request = AsyncMock()
        self.assertTrue(await client.receipt(original, "INVALID", "invalid_handoff_record"))
        data = client.request.call_args.kwargs["json"]["data"][1]["values"]
        self.assertEqual(data, [["", "", "invalid_handoff_record"]])

    async def test_committed_replay_repairs_failed_ack(self):
        value = record()
        client = AsyncMock()
        client.read.return_value = sheet(value)
        client.receipt.return_value = True
        sessions = MagicMock()
        sessions.return_value.__aenter__.return_value = AsyncMock()
        with patch.dict(os.environ, {"LIFE_CURATED_SHEET_ID": SHEET_ID, "LIFE_CURATED_IMPORT_APPLY": "1"}), patch(
                "scripts.import_curated_from_sheet.upsert_handoff", AsyncMock(return_value="UNCHANGED")):
            result = await run_import(client, sessions)
        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["status"], "PASS")
        client.receipt.assert_awaited_once_with(value, "UNCHANGED")

"""Fixed handoff contract and receipt version fencing; no real Drive writes."""
import os
import hashlib
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
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

    def test_unknown_verification_time_is_optional_and_not_fabricated(self):
        row = record(verified_at_tpe="", evidence_summary="來源索引待核；未取得核證時間")
        item = validate_record(row)
        self.assertIsNone(item.verified_at_tpe)
        self.assertIsNone(item.model_dump(mode="json")["verified_at_tpe"])
        self.assertIn("待核", item.evidence_summary)
        # A supplied verification timestamp must still be genuinely Taipei offset-aware.
        with self.assertRaisesRegex(ValueError, "handoff_time_requires_taipei_offset"):
            validate_record(record(verified_at_tpe="2026-10-12T10:00:00Z"))

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
        with patch("scripts.import_curated_from_sheet.datetime") as clock:
            clock.now.return_value.isoformat.return_value = "2026-10-10T09:00:00+08:00"
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
        client.receipts.return_value = [True]
        sessions = MagicMock()
        sessions.return_value.__aenter__.return_value = AsyncMock()
        with patch.dict(os.environ, {"LIFE_CURATED_SHEET_ID": SHEET_ID, "LIFE_CURATED_IMPORT_APPLY": "1"}), patch(
                "scripts.import_curated_from_sheet.upsert_handoff", AsyncMock(return_value="UPDATED")) as upsert:
            result = await run_import(client, sessions)
        upsert.assert_awaited_once()
        self.assertEqual(result["updated"], 1)
        client.receipts.assert_awaited_once_with([(newer, "UPDATED", "")])

    async def test_error_receipt_leaves_success_result_empty(self):
        original = record(handoff_status="ACKED", life_import_result="CREATED", life_ack_at_tpe="2026-10-10T09:00:00+08:00")
        failed = dict(original, handoff_status="ERROR", life_ack_at_tpe="", life_import_result="", life_error="invalid_handoff_record")
        client = SheetClient()
        client.read = AsyncMock(side_effect=[sheet(original), sheet(failed)])
        client.request = AsyncMock()
        self.assertTrue(await client.receipt(original, "INVALID", "invalid_handoff_record"))
        data = client.request.call_args.kwargs["json"]["data"][1]["values"]
        self.assertEqual(data, [["", "", "invalid_handoff_record"]])

    async def test_blank_verification_time_reaches_db_and_success_receipt(self):
        value = record(verified_at_tpe="", evidence_summary="待核；活動日期有來源")
        client = AsyncMock()
        client.read.return_value = sheet(value)
        client.receipts.return_value = [True]
        sessions = MagicMock()
        sessions.return_value.__aenter__.return_value = AsyncMock()
        with patch.dict(os.environ, {"LIFE_CURATED_SHEET_ID": SHEET_ID, "LIFE_CURATED_IMPORT_APPLY": "1"}), patch(
                "scripts.import_curated_from_sheet.upsert_handoff", AsyncMock(return_value="CREATED")) as upsert:
            result = await run_import(client, sessions)
        upsert.assert_awaited_once()
        self.assertIsNone(upsert.await_args.args[1].verified_at_tpe)
        client.receipts.assert_awaited_once_with([(value, "CREATED", "")])
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["invalid"], 0)
        self.assertEqual(result["status"], "PASS")

    async def test_committed_replay_repairs_failed_ack(self):
        value = record()
        client = AsyncMock()
        client.read.return_value = sheet(value)
        client.receipts.return_value = [True]
        sessions = MagicMock()
        sessions.return_value.__aenter__.return_value = AsyncMock()
        with patch.dict(os.environ, {"LIFE_CURATED_SHEET_ID": SHEET_ID, "LIFE_CURATED_IMPORT_APPLY": "1"}), patch(
                "scripts.import_curated_from_sheet.upsert_handoff", AsyncMock(return_value="UNCHANGED")):
            result = await run_import(client, sessions)
        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["status"], "PASS")
        client.receipts.assert_awaited_once_with([(value, "UNCHANGED", "")])


    async def test_bulk_receipts_only_two_reads_and_one_batch_write(self):
        first = record()
        second = record(event_key="official:two:2026", title="第二個活動")
        fixed_now = "2026-10-12T17:30:00+08:00"
        first_ack = dict(first, handoff_status="ACKED",
                         life_ack_at_tpe=fixed_now, life_import_result="CREATED")
        second_error = dict(second, handoff_status="ERROR", life_error="invalid_handoff_record")
        client = SheetClient()
        client.read = AsyncMock(side_effect=[sheet(first, second), sheet(first_ack, second_error)])
        client.request = AsyncMock()
        with patch("scripts.import_curated_from_sheet.datetime") as clock:
            clock.now.return_value.isoformat.return_value = fixed_now
            outcomes = await client.receipts([
                (first, "CREATED", ""), (second, "INVALID", "invalid_handoff_record")
            ])
        self.assertEqual(outcomes, [True, True])
        self.assertEqual(client.read.await_count, 2)
        client.request.assert_awaited_once()
        data = client.request.await_args.kwargs["json"]["data"]
        self.assertEqual(len(data), 4)
        self.assertEqual(data[0]["range"], "'交接資料'!Z2")
        self.assertEqual(data[2]["range"], "'交接資料'!Z3")

    async def test_batch_skips_changed_version_and_keeps_correct_ack(self):
        updated = record(title="活動已由探索端改動")
        stale = record()
        already_acked = record(event_key="official:acked:2026", title="已回執",
                               handoff_status="ACKED",
                               life_ack_at_tpe="2026-10-10T09:00:00+08:00",
                               life_import_result="CREATED")
        client = SheetClient()
        client.read = AsyncMock(return_value=sheet(updated, already_acked))
        client.request = AsyncMock()
        self.assertEqual(
            await client.receipts([(stale, "CREATED", ""), (already_acked, "UNCHANGED", "")]),
            [False, True],
        )
        client.request.assert_not_awaited()
        client.read.assert_awaited_once()

    async def test_many_invalid_rows_have_one_bulk_receipt_call(self):
        records = [record(event_key=f"official:bad:{i}", title="有效活動",
                          importance_star="2") for i in range(30)]
        records.append(record(event_key="official:good", title="有效活動"))
        client = AsyncMock()
        client.read.return_value = sheet(*records)
        client.receipts.return_value = [True] * len(records)
        sessions = MagicMock()
        sessions.return_value.__aenter__.return_value = AsyncMock()
        with patch.dict(os.environ, {"LIFE_CURATED_SHEET_ID": SHEET_ID,
                                      "LIFE_CURATED_IMPORT_APPLY": "1"}), patch(
                "scripts.import_curated_from_sheet.upsert_handoff",
                AsyncMock(return_value="CREATED")) as upsert:
            result = await run_import(client, sessions)
        self.assertEqual(result["invalid"], 30)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["status"], "PARTIAL")
        upsert.assert_awaited_once()
        client.receipts.assert_awaited_once()
        pending = client.receipts.await_args.args[0]
        self.assertEqual(len(pending), 31)
        self.assertEqual(pending[0][2], "invalid_handoff_record")
        self.assertEqual(pending[-1][1], "CREATED")

    async def test_sheets_429_retry_succeeds_without_exposing_content(self):
        hits = []
        def handler(request):
            hits.append(request)
            if len(hits) <= 2:
                return httpx.Response(429, headers={"Retry-After": "1"},
                                      json={"error": {"message": "private source data"}})
            return httpx.Response(200, json={"values": [["ok"]]})
        transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = SheetClient()
        with patch.object(client, "_access_token", AsyncMock(return_value="fake-token")), patch(
                "scripts.import_curated_from_sheet.httpx.AsyncClient",
                return_value=transport_client), patch(
                "scripts.import_curated_from_sheet.asyncio.sleep", new_callable=AsyncMock) as sleeping:
            response = await client.request("GET", "values%2Ftest")
        self.assertEqual(response, {"values": [["ok"]]})
        self.assertEqual(len(hits), 3)
        self.assertEqual(sleeping.await_count, 2)

    async def test_sheets_429_exhaustion_is_visible_and_fails_closed(self):
        hits = []
        def handler(request):
            hits.append(request)
            return httpx.Response(429, json={"error": {"message": "private source data"}})
        transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = SheetClient()
        with patch.object(client, "_access_token", AsyncMock(return_value="fake-token")), patch(
                "scripts.import_curated_from_sheet.httpx.AsyncClient",
                return_value=transport_client), patch(
                "scripts.import_curated_from_sheet.asyncio.sleep", new_callable=AsyncMock) as sleeping:
            with self.assertRaisesRegex(RuntimeError, "sheets_http_429"):
                await client.request("POST", "values:batchUpdate", json={"data": []})
        self.assertEqual(len(hits), 6)
        self.assertEqual(sleeping.await_count, 5)

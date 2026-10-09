"""Offline-only event manifest; source spoofing and duplicate admission barriers."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from app.services.free_events_manifest import prepare_manifest


ROOT = Path(__file__).resolve().parents[2]


class FreeEventManifestTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(
            (ROOT / "data/free_events_m0_sources.json").read_text(encoding="utf-8")
        )
        self.candidate = {
            "source_id": "moc_events_all",
            "external_event_key": "moc-123",
            "title": "免費藝文活動",
            "source_url": "https://example.tw/event/123",
            "official_url": "https://organizer.example.tw/event/123",
            "official_verified": True,
            "sessions": [{
                "session_key": "session-1",
                "starts_on": "2026-10-10",
                "ends_on_exclusive": "2026-10-11",
                "opportunities": [
                    {"opportunity_key": "registration-a", "fee_kind": "unknown"}
                ],
            }],
        }

    def test_default_source_cannot_be_published(self):
        report = prepare_manifest([self.candidate], self.registry)
        self.assertEqual(report["m1_status"], "PARTIAL")
        self.assertEqual(report["status_counts"], {"eligible_for_manual_review": 1})
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["database_writes"], 0)
        self.assertEqual(report["ai_calls"], 0)
        self.assertFalse(report["candidates"][0]["publishable"])
        self.assertEqual(report["candidates"][0]["unknown_registration_start_count"], 1)

    def test_official_flag_does_not_bypass_source_access_review(self):
        fake = deepcopy(self.candidate)
        fake["official_verified"] = True
        fake["source_id"] = "eventgo"
        fake["title"] = "官方聲稱"
        report = prepare_manifest([fake], self.registry)
        self.assertEqual(report["candidates"][0]["status"], "quarantined_source_permission")

    def test_provenance_review_enables_manual_review_not_auto_publish(self):
        approved = deepcopy(self.registry)
        source = next(s for s in approved["sources"] if s["id"] == "moc_events_all")
        source["service_access_review"] = "reviewed_with_evidence"
        source["enabled_for_fetch"] = True
        report = prepare_manifest([self.candidate], approved)
        self.assertEqual(report["status_counts"], {"eligible_for_manual_review": 1})
        self.assertFalse(report["candidates"][0]["publishable"])
        self.assertFalse(report["candidates"][0]["registration_open_verified"])

    def test_verified_same_official_content_from_two_sources_deduplicates(self):
        a = deepcopy(self.candidate)
        b = deepcopy(a)
        b["source_id"] = "eventgo"
        b["external_event_key"] = "eventgo-other"
        b["source_url"] = "https://eventgo.tw/events/other"
        report = prepare_manifest([a, b], self.registry)
        self.assertEqual(report["deduplicated_count"], 1)
        self.assertEqual(len(report["candidates"]), 1)
        self.assertFalse(report["candidates"][0]["content_conflict"])
        self.assertEqual(report["candidates"][0]["status"], "eligible_for_manual_review")
        self.assertFalse(report["candidates"][0]["publishable"])

    def test_deterministic_dedup_and_conflict_quarantine(self):
        a = deepcopy(self.candidate)
        b = deepcopy(self.candidate)
        conflict = deepcopy(self.candidate)
        conflict["title"] = "相同官方 URL 卻不同文案"
        report = prepare_manifest([a, b], self.registry)
        self.assertEqual(report["deduplicated_count"], 1)
        self.assertEqual(len(report["candidates"]), 1)
        report = prepare_manifest([a, conflict], self.registry)
        self.assertEqual(report["status_counts"], {"conflict_requires_review": 1})

    def test_cancelled_discovery_sources_are_rejected(self):
        from copy import deepcopy
        candidates = []
        for source_id in ("citytalk", "accupass", "kktix", "beclass"):
            row = deepcopy(self.candidate)
            row["source_id"] = source_id
            candidates.append(row)
        report = prepare_manifest(candidates, self.registry)
        self.assertEqual(report["input_count"], 4)
        self.assertEqual(report["rejected"], {"unknown_source": 4})
        self.assertEqual(report["candidates"], [])

    def test_bad_row_or_unknown_source_is_rejected_without_echo(self):
        bad = deepcopy(self.candidate)
        bad["source_id"] = "unknown"
        invalid = deepcopy(self.candidate)
        invalid["source_url"] = "http://localhost/event"
        report = prepare_manifest([bad, invalid], self.registry)
        self.assertEqual(report["rejected"], {
            "invalid_candidate": 1, "unknown_source": 1
        })
        self.assertEqual(len(report["candidates"]), 0)
        self.assertNotIn("localhost", json.dumps(report))

    def test_source_scoped_unverified_duplicates_are_not_merged(self):
        a = deepcopy(self.candidate)
        a["official_verified"] = False
        b = deepcopy(a)
        b["source_id"] = "eventgo"
        report = prepare_manifest([a, b], self.registry)
        self.assertEqual(len(report["candidates"]), 2)

    def test_previous_fingerprint_does_not_create_ai_calls(self):
        first = prepare_manifest([self.candidate], self.registry)
        record = first["candidates"][0]
        second = prepare_manifest(
            [self.candidate], self.registry,
            previous_fingerprints={record["event_key"]: record["fingerprint"]},
        )
        self.assertTrue(second["candidates"][0]["unchanged_from_previous"])
        self.assertEqual(second["ai_calls"], 0)

    def test_batch_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "bounded maximum"):
            prepare_manifest([self.candidate, self.candidate], self.registry, max_rows=1)


if __name__ == "__main__":
    unittest.main()

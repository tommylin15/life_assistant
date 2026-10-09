"""M0 source legality/provenance and 14-day measurement safety contracts."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts/free_events_m0_baseline.py"
SPEC = importlib.util.spec_from_file_location("free_events_m0_baseline", TOOL)
m0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m0)


class FreeEventsM0Tests(unittest.TestCase):
    def setUp(self):
        self.registry = m0.load_registry()
        self.now = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)

    def sample(self, day, **values):
        obs = {
            "source_id": "moc_events_all", "event_key": f"opaque-{day}",
            "observed_at": (self.now - timedelta(days=day)).isoformat(),
            "is_free": None, "official_verified": False,
            "registration_opens_at": None, "published_at": None,
        }
        obs.update(values)
        return obs

    def test_only_approved_official_source_is_enabled(self):
        self.assertEqual(len(self.registry["sources"]), 9)
        self.assertNotIn("beclass", {s["id"] for s in self.registry["sources"]})
        self.assertFalse(next(s for s in self.registry["sources"] if s["id"] == "eventgo")["enabled_for_fetch"])
        self.assertEqual([s["id"] for s in self.registry["sources"] if s["enabled_for_fetch"]], ["moc_events_all"])
        source = next(s for s in self.registry["sources"] if s["id"] == "moc_events_all")
        self.assertEqual(source["tier"], "official_dataset")
        self.assertIn("data.gov.tw", source["data_license_evidence"])
        self.assertEqual(source["service_access_review"], "reviewed_with_evidence")
        self.assertTrue(next(s for s in self.registry["sources"] if s["id"] == "tdx_tourism_events")["requires_api_key"])

    def test_pending_aggregator_must_not_be_enabled(self):
        from copy import deepcopy
        import json
        import tempfile
        data = deepcopy(self.registry)
        data["sources"][-1]["enabled_for_fetch"] = True
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "registry.json"
            f.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                m0.load_registry(f)

    def test_no_observations_cannot_claim_14_day_baseline(self):
        result = m0.evaluate(self.registry, [], as_of=self.now)
        self.assertEqual(result["m0_status"], "NOT_VERIFIED")
        self.assertEqual(result["automated_fetch_enabled_count"], 1)
        self.assertEqual(result["sources"]["moc_events_all"]["sample_count"], 0)
        self.assertFalse(result["sources"]["moc_events_all"]["fourteen_day_window_observed"])

    def test_contiguous_14_day_observations_are_coverage_only_not_m0_pass(self):
        result = m0.evaluate(self.registry, [self.sample(i) for i in range(14)], as_of=self.now)
        row = result["sources"]["moc_events_all"]
        self.assertEqual(row["observation_days"], 14)
        self.assertEqual(row["max_consecutive_days"], 14)
        self.assertTrue(row["fourteen_day_window_observed"])
        self.assertEqual(row["registration_open_unknown"], 14)
        self.assertEqual(row["free_confirmed"], 0)
        self.assertEqual(row["fee_unknown"], 14)
        self.assertEqual(result["m0_status"], "NOT_VERIFIED")

    def test_missing_day_breaks_coverage(self):
        result = m0.evaluate(self.registry, [self.sample(i) for i in range(15) if i != 6], as_of=self.now)
        self.assertFalse(result["sources"]["moc_events_all"]["fourteen_day_window_observed"])

    def test_unverified_free_is_not_verified_free(self):
        row = m0.evaluate(self.registry, [
            self.sample(0, is_free=True, official_verified=False),
            self.sample(1, is_free=True, official_verified=True),
        ], as_of=self.now)["sources"]["moc_events_all"]
        self.assertEqual(row["free_confirmed"], 1)
        self.assertEqual(row["free_unverified"], 1)
        self.assertEqual(row["official_page_unverified"], 1)

    def test_rejects_future_or_naive_and_impossible_publication(self):
        cases = [
            self.sample(-1),
            self.sample(0, observed_at="2026-10-22T12:00:00"),
            self.sample(0, published_at="2026-10-24T00:00:00+00:00"),
            self.sample(0, source_id="unknown"),
            self.sample(0, is_free="free"),
        ]
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                m0.evaluate(self.registry, [bad], as_of=self.now)

    def test_publication_latency_is_only_measured_when_supplied(self):
        row = m0.evaluate(self.registry, [
            self.sample(0, published_at=(self.now-timedelta(hours=3)).isoformat()),
            self.sample(1),
        ], as_of=self.now)["sources"]["moc_events_all"]
        self.assertEqual(row["publication_latency_samples"], 1)
        self.assertEqual(row["mean_publication_latency_hours"], 3.0)


if __name__ == "__main__":
    unittest.main()

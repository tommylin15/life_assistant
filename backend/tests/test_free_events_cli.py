"""Execute M1 JSONL preview as a user would; ensure fail-closed output."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/free_events_m1_dry_run.py"


class FreeEventCliAcceptanceTests(unittest.TestCase):
    def test_offline_jsonl_can_be_checked_without_source_access(self):
        fixture = {
            "source_id": "moc_events_all",
            "external_event_key": "offline-fixture-not-a-real-event",
            "title": "測試藝文活動",
            "source_url": "https://example.tw/event/test",
            "sessions": [{
                "session_key": "demo",
                "opportunities": [{"opportunity_key": "ticket", "fee_kind": "unknown"}],
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.jsonl"
            path.write_text(json.dumps(fixture, ensure_ascii=False) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CLI), str(path)],
                cwd=ROOT, capture_output=True, text=True, timeout=15, check=True,
            )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["input_count"], 1)
        self.assertEqual(payload["database_writes"], 0)
        self.assertEqual(payload["network_requests"], 0)
        self.assertEqual(payload["ai_calls"], 0)
        self.assertEqual(payload["status_counts"], {
            "needs_official_review": 1,
        })
        self.assertFalse(payload["candidates"][0]["publishable"])
        self.assertEqual(payload["candidates"][0]["unknown_fee_count"], 1)

    def test_malformed_json_fails_closed_without_partial_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.jsonl"
            path.write_text("{invalid_json}\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CLI), str(path)],
                cwd=ROOT, capture_output=True, text=True, timeout=15,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()

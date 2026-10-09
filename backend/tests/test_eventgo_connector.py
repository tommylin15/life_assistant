"""EventGo standalone parser, provenance, duplicate and permission gates (offline)."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import eventgo_connector as eg  # noqa: E402

EVENT1 = "19749864-309b-4f33-9f8a-1317075169dc"
EVENT2 = "a0000000-0000-4000-8000-000000000002"
EVENT3 = "a0000000-0000-4000-8000-000000000003"
U1 = f"https://eventgo.tw/event/{EVENT1}"
U2 = f"https://eventgo.tw/event/{EVENT2}"
U3 = f"https://eventgo.tw/event/{EVENT3}"
LISTING = f"""
<html><body><main>
 <section>
  <div class="unknown-css">
   <a href="/event/{EVENT1}"><span>免費</span>
     <h3>紙風車劇團 《寶莉回家》</h3><span>親子</span>
   </a>
  </div>
  <div>
   <a href="/event/{EVENT2}"><img src="https://www.beclass.com/photo.jpg">
     <h3>來源圖片為 BeClass 的活動</h3>
   </a>
  </div>
  <div><a href="/event/{EVENT3}"><h3>原站為 BeClass 的活動</h3></a></div>
 </section>
 <nav><a href="/search?isFree=true&page=1">1</a>
 <a href="/search?isFree=true&page=2">2</a>
 <a href="/search?category=music&page=2">不相關</a>
 <a href="https://evil.invalid/search?isFree=true&page=2">外站</a></nav>
</main></body></html>
"""
DETAIL1 = """<main><h1>紙風車劇團《寶莉回家》</h1>
  <p>2026/10/9 19:00 實際須官網查證</p>
  <a href="https://www.cultural.pthg.gov.tw/page?id=42">前往活動</a>
</main>"""
DETAIL3 = """<main><h1>BeClass 報名連結須保留</h1>
  <a href="https://www.beclass.com/rid=100">前往活動</a>
</main>"""


class EventGoTests(unittest.TestCase):
    def test_actual_seed_shapes(self):
        self.assertEqual(eg.SEEDS["free"], "https://eventgo.tw/search?isFree=true")
        self.assertEqual(eg.SEEDS["taipei"], "https://eventgo.tw/explore/cities/taipei")
        self.assertEqual(eg.SEEDS["family"], "https://eventgo.tw/search?category=family")
        self.assertEqual(len(eg.SEEDS), 10)

    def test_listing_and_page_discovery(self):
        items, pages = eg.parse_listing(LISTING, eg.SEEDS["free"])
        self.assertEqual({i["eventgo_id"] for i in items}, {EVENT1, EVENT2, EVENT3})
        first = next(i for i in items if i["eventgo_id"] == EVENT1)
        self.assertTrue(first["free_badge_hint"])
        self.assertEqual(first["title"], "紙風車劇團 《寶莉回家》")
        self.assertEqual(pages, [
            "https://eventgo.tw/search?isFree=true&page=1",
            "https://eventgo.tw/search?isFree=true&page=2",
        ])
        self.assertEqual(eg._next_page(pages, 1, eg.SEEDS["free"]), pages[1])
        self.assertIsNone(eg._next_page(pages, 2, eg.SEEDS["free"]))

    def test_detail_provenance_keeps_beclass_referral(self):
        items, _ = eg.parse_listing(LISTING, eg.SEEDS["free"])
        rows = eg.normalize(items, {U1: DETAIL1, U3: DETAIL3},
                            "2026-10-09T10:00:00+00:00")
        self.assertEqual(len(rows), 2)
        by_id = {row["eventgo_id"]: row for row in rows}
        self.assertEqual(by_id[EVENT1]["original_url"],
                         "https://www.cultural.pthg.gov.tw/page?id=42")
        self.assertEqual(by_id[EVENT3]["original_url"], "https://www.beclass.com/rid=100")
        self.assertEqual(by_id[EVENT3]["detail_url"], U3)
        for row in rows:
            self.assertFalse(row["official_verified"])
            self.assertEqual(row["fee_status"], "unverified")
            self.assertEqual(row["registration_status"], "unverified")
            self.assertEqual(len(row["content_fingerprint"]), 64)

    def test_duplicate_seed_and_unknown_original_skip(self):
        items, _ = eg.parse_listing(LISTING, eg.SEEDS["free"])
        self.assertEqual(eg.normalize(items + items, {U1: DETAIL1},
                                      "2026-10-09T00:00:00+00:00")[0]["eventgo_id"], EVENT1)
        self.assertEqual(len(eg.normalize(items + items, {U1: DETAIL1},
                                         "2026-10-09T00:00:00+00:00")), 1)
        self.assertEqual(eg.normalize(items, {}, "2026-10-09T00:00:00+00:00"), [])

    def test_strict_urls(self):
        self.assertIsNone(eg._event_url("https://evil.invalid/event/" + EVENT1))
        self.assertIsNone(eg._event_url("http://eventgo.tw/event/" + EVENT1))
        self.assertIsNone(eg._event_url("https://eventgo.tw.evil.invalid/event/" + EVENT1))
        self.assertIsNone(eg._event_url("https://eventgo.tw@evil.invalid/event/" + EVENT1))
        self.assertIsNone(eg._source_url("https://eventgo.tw:8080/search"))
        self.assertIsNone(eg._external_url("file:///etc/passwd"))
        self.assertIsNone(eg._external_url("http://www.beclass.com/x"))
        self.assertIsNone(eg._source_url("https://www.beclass.com/rid=100"))
        self.assertEqual(eg._external_url("https://www.beclass.com/rid=100"),
                         "https://www.beclass.com/rid=100")

    def test_registry_denies_network_by_default(self):
        with self.assertRaises(PermissionError):
            eg.check_approved()
        with self.assertRaises(PermissionError), patch.object(
            eg, "load_robots", side_effect=AssertionError("network attempted")
        ):
            import asyncio
            asyncio.run(eg.crawl_live(["free"], max_pages=1, max_events=20,
                                      delay_seconds=2.0))

    def test_offline_cli_jsonl_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixtures.json"
            output = Path(tmp) / "candidates.jsonl"
            fixture.write_text(json.dumps({
                "listings": {"free": LISTING, "taipei": LISTING},
                "details": {U1: DETAIL1, U3: DETAIL3},
                "observed_at": "2026-10-09T00:00:00+00:00",
            }, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(eg.main(["--offline-fixture", str(fixture),
                                      "--output", str(output)]), 0)
            objs = [json.loads(x) for x in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(objs), 2)
            self.assertTrue(all(not obj["official_verified"] for obj in objs))
            self.assertTrue(all(obj["source"] == "eventgo" for obj in objs))
            self.assertIn("https://www.beclass.com/rid=100",
                          {obj["original_url"] for obj in objs})

    def test_bounded_html(self):
        with self.assertRaises(ValueError):
            eg.parse_detail("x" * (eg.MAX_HTML_CHARS + 1))


if __name__ == "__main__":
    unittest.main()

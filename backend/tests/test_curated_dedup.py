"""Unit tests for curated activity entity deduplication and title normalization."""
import unittest
from datetime import date
from app.services.curated_dedup import (
    normalize_title,
    calculate_date_overlap_ratio,
    is_entity_match,
    find_canonical_parent,
)


class TestCuratedDedup(unittest.TestCase):
    def test_normalize_title_strips_years_and_subtitles(self):
        cases = [
            (
                "2026–2027屏東四重溪溫泉季（四重溪溫泉公園浪漫光影燈海、溫泉市集與足湯體驗）",
                "屏東四重溪溫泉季",
            ),
            (
                "2026-2027屏東四重溪溫泉季（溫泉公園沉浸式藝術燈區）",
                "屏東四重溪溫泉季",
            ),
            (
                "2026臺灣國際衝浪公開賽（東河金樽漁港沙灘衝浪賽事、海洋市集與浪人草地音樂會）",
                "臺灣國際衝浪公開賽",
            ),
            (
                "2026金門老兵召集令「榮耀歸隊・番號集結」",
                "金門老兵召集令",
            ),
            (
                "2026士林官邸菊展《菊映方圓》（15大菊花主題展區、園藝藝術與戶外花海漫步）",
                "士林官邸菊展",
            ),
            (
                "2026冬戀蘭陽溫泉季（祈水感恩禮、踩街嘉年華、溫泉美食市集與蘭陽越夜越美麗光影展）",
                "冬戀蘭陽溫泉季",
            ),
            (
                "【免費報名】臺北市政府工務局永續發展生態微旅行—「山湖漫遊，莓香好食光。」",
                "臺北市政府工務局永續發展生態微旅行",
            ),
            (
                "第34屆嘉義市國際管樂節（全城踩街嘉年華、中正公園與文化公園戶外大型音樂會）",
                "嘉義市國際管樂節",
            ),
        ]
        for raw, expected in cases:
            self.assertEqual(normalize_title(raw), expected)

    def test_date_overlap_ratio(self):
        # Full overlap
        r = calculate_date_overlap_ratio(
            date(2026, 11, 1), date(2026, 11, 30),
            date(2026, 11, 1), date(2026, 11, 30),
        )
        self.assertAlmostEqual(r, 1.0)

        # Partial overlap
        r = calculate_date_overlap_ratio(
            date(2026, 11, 1), date(2026, 11, 20),
            date(2026, 11, 11), date(2026, 11, 30),
        )
        self.assertAlmostEqual(r, 10 / 20)

        # No overlap
        r = calculate_date_overlap_ratio(
            date(2026, 10, 1), date(2026, 10, 15),
            date(2026, 11, 1), date(2026, 11, 15),
        )
        self.assertAlmostEqual(r, 0.0)

    def test_is_entity_match_positive(self):
        matched, reason = is_entity_match(
            title1="2026臺灣國際衝浪公開賽（WSL QS 6000・東河金樽海域國際賽）",
            city1="臺東縣",
            start1=date(2026, 11, 6),
            end1=date(2026, 11, 22),
            title2="2026臺灣國際衝浪公開賽（東河金樽漁港沙灘衝浪賽事、海洋市集與浪人草地音樂會）",
            city2="臺東縣",
            start2=date(2026, 11, 8),
            end2=date(2026, 11, 16),
        )
        self.assertTrue(matched)

    def test_is_entity_match_city_mismatch(self):
        matched, reason = is_entity_match(
            title1="2026花海節慶",
            city1="臺中市",
            start1=date(2026, 11, 1),
            end1=date(2026, 11, 30),
            title2="2026花海節慶",
            city2="桃園市",
            start2=date(2026, 11, 1),
            end2=date(2026, 11, 30),
        )
        self.assertFalse(matched)
        self.assertEqual(reason, "city_mismatch")

    def test_generic_token_does_not_false_positive(self):
        matched, reason = is_entity_match(
            title1="講座《台灣歷史》",
            city1="臺北市",
            start1=date(2026, 11, 1),
            end1=date(2026, 11, 1),
            title2="講座《宇宙奧秘》",
            city2="臺北市",
            start2=date(2026, 11, 1),
            end2=date(2026, 11, 1),
        )
        self.assertFalse(matched)

    def test_find_canonical_parent(self):
        existing = [
            {
                "event_key": "tour.taitung.gov.tw:2026:taiwan-open-surfing",
                "parent_event_key": "tour.taitung.gov.tw:2026:taiwan-open-surfing",
                "title": "2026臺灣國際衝浪公開賽",
                "city": "臺東縣",
                "starts_on": date(2026, 11, 6),
                "ends_on": date(2026, 11, 22),
            }
        ]
        candidate = {
            "title": "2026臺灣國際衝浪公開賽（東河金樽漁港沙灘衝浪賽事、海洋市集）",
            "city": "臺東縣",
            "start_at_tpe": "2026-11-08T09:00:00+08:00",
            "end_at_tpe": "2026-11-16T17:00:00+08:00",
        }
        parent = find_canonical_parent(existing, candidate)
        self.assertIsNotNone(parent)
        self.assertEqual(parent["event_key"], "tour.taitung.gov.tw:2026:taiwan-open-surfing")


if __name__ == "__main__":
    unittest.main()

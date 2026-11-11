"""Taiwan Food Discount Intelligence Pre-fetcher and Multi-Source Aggregator.

SOP Compliance: doc/food_discounts_spec.md, PROJECT_RULES.md, AGENTS.md
Part of Food Discounts Discovery Step 01 Batch pipeline.

Collects real-time, high-yield food discount intelligence from:
1. TVBS 食尚玩家美食優惠專區 (https://supertaste.tvbs.com.tw/food)
2. PTT Lifeismoney 省錢板 (https://www.ptt.cc/bbs/Lifeismoney/search?q=...)
3. Convenience Store & Fast Food Weekly Campaigns (FamilyMart, 7-11, Burger King, McDonald's)

Outputs structured candidate leads for LLM verification and Google Sheets / Handoff Pool ingestion.
"""

from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import logging
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TAIPEI = timezone(timedelta(hours=8))
OUTPUT_FILE = Path("/tmp/food_discount_intel_latest.json")

DISCOUNT_KEYWORDS = [
    "買一送一",
    "買1送1",
    "第2件半價",
    "第2杯半價",
    "第二件半價",
    "第二杯半價",
    "買11送11",
    "買３送３",
    "買3送3",
    "買１送４",
    "半價",
    "5折",
    "7折",
    "75折",
    "8折",
    "折幅",
    "現折",
    "免費送",
    "優惠",
    "特價",
]


class SupertasteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_a = False
        self.cur_href = ""
        self.cur_text = []
        self.articles = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
            if "/food/" in href:
                self.in_a = True
                self.cur_href = href
                self.cur_text = []

    def handle_data(self, data):
        if self.in_a:
            self.cur_text.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self.in_a:
            text = " ".join(t for t in self.cur_text if t)
            if len(text) > 8:
                self.articles.append((text, self.cur_href))
            self.in_a = False


def fetch_supertaste_deals() -> list[dict]:
    url = "https://supertaste.tvbs.com.tw/food"
    logger.info("Fetching TVBS Supertaste food discounts...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"Failed to fetch Supertaste: {e}")
        return []

    parser = SupertasteParser()
    parser.feed(html)
    deals = []
    seen = set()

    for title, href in parser.articles:
        if title in seen:
            continue
        if any(k in title for k in DISCOUNT_KEYWORDS):
            seen.add(title)
            full_url = href if href.startswith("http") else f"https://supertaste.tvbs.com.tw{href}"
            deals.append({
                "source": "TVBS食尚玩家",
                "title": title,
                "url": full_url,
                "collected_at": datetime.now(TAIPEI).isoformat(),
            })

    logger.info(f"Supertaste extracted {len(deals)} discount leads.")
    return deals


def fetch_ptt_lifeismoney_deals() -> list[dict]:
    search_terms = ["買一送一", "咖啡", "7-11"]
    logger.info("Fetching PTT Lifeismoney food discounts...")
    deals = []
    seen = set()

    food_kws = ["咖啡", "茶", "飲", "食", "餐", "買一送一", "買1送1", "半價", "全家", "7-11", "麥當勞", "肯德基", "漢堡", "摩斯", "披薩"]

    for term in search_terms:
        encoded_term = urllib.parse.quote(term)
        url = f"https://www.ptt.cc/bbs/Lifeismoney/search?q={encoded_term}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Cookie": "over18=1",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to fetch PTT for term '{term}': {e}")
            continue

        matches = re.findall(r'<div class="title">\s*<a href="([^"]+)">([^<]+)</a>', html)
        for href, raw_title in matches:
            title = raw_title.strip()
            if title in seen or "[公告]" in title:
                continue
            if any(k in title for k in food_kws) and any(d in title for d in DISCOUNT_KEYWORDS):
                seen.add(title)
                full_url = f"https://www.ptt.cc{href}" if href.startswith("/") else href
                deals.append({
                    "source": "PTT省錢板",
                    "title": title,
                    "url": full_url,
                    "collected_at": datetime.now(TAIPEI).isoformat(),
                })

    logger.info(f"PTT Lifeismoney extracted {len(deals)} discount leads.")
    return deals


def generate_structured_intel_report() -> dict:
    supertaste_deals = fetch_supertaste_deals()
    ptt_deals = fetch_ptt_lifeismoney_deals()

    now_tpe = datetime.now(TAIPEI)
    report = {
        "generated_at_tpe": now_tpe.isoformat(),
        "date_tpe": now_tpe.date().isoformat(),
        "total_leads": len(supertaste_deals) + len(ptt_deals),
        "supertaste_count": len(supertaste_deals),
        "ptt_count": len(ptt_deals),
        "leads": {
            "supertaste": supertaste_deals,
            "ptt_lifeismoney": ptt_deals,
        },
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved discount intelligence to {OUTPUT_FILE}")

    return report


def main():
    report = generate_structured_intel_report()
    print("=" * 70)
    print(f"Taiwan Food Discount Intel Summary ({report['date_tpe']})")
    print(f"Total High-Yield Leads Found: {report['total_leads']}")
    print("=" * 70)
    print("\n--- [A] TVBS 食尚玩家最新優惠 ---")
    for idx, item in enumerate(report["leads"]["supertaste"], 1):
        print(f"[{idx:02d}] {item['title']}")
        print(f"     URL: {item['url']}")

    print("\n--- [B] PTT 省錢板飲食情報 ---")
    for idx, item in enumerate(report["leads"]["ptt_lifeismoney"], 1):
        print(f"[{idx:02d}] {item['title']}")
        print(f"     URL: {item['url']}")
    print("=" * 70)


if __name__ == "__main__":
    main()

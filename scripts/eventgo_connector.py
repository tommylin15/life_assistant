#!/usr/bin/env python3
"""Isolated EventGo -> unverified candidate JSONL connector.

No PostgreSQL, FastAPI, Scheduler or personal actions. Network is denied until
source registry approval and a separate explicit --live opt-in.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
from html.parser import HTMLParser
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/free_events_m0_sources.json"
HOST = "eventgo.tw"
BASE = "https://eventgo.tw"
ROBOTS = BASE + "/robots.txt"
USER_AGENT = "LifeAssistantEventDiscovery/0.1"
SEEDS = {
    "free": BASE + "/search?isFree=true",
    "music": BASE + "/search?category=music",
    "exhibition": BASE + "/search?category=exhibition",
    "lecture": BASE + "/search?category=lecture",
    "outdoor": BASE + "/search?category=outdoor",
    "family": BASE + "/search?category=family",
    "taipei": BASE + "/explore/cities/taipei",
    "taichung": BASE + "/explore/cities/taichung",
    "kaohsiung": BASE + "/explore/cities/kaohsiung",
    "tainan": BASE + "/explore/cities/tainan",
}
EVENT_ID = re.compile(r"^/event/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/?$")
MAX_HTML_CHARS = 2_000_000
MAX_ROBOTS_BYTES = 256 * 1024
MAX_OUTPUT_ROWS = 100
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


def _text(s: str) -> str:
    return " ".join(s.split())


def _source_url(url: str) -> str | None:
    """Only permitted EventGo HTTPS URLs can be fetched by the crawler."""
    u = urlsplit(url)
    if u.scheme != "https" or u.hostname != HOST or u.port is not None or u.username or u.password:
        return None
    if u.fragment or not (u.path == "/search" or u.path.startswith("/explore/cities/")
                          or EVENT_ID.fullmatch(u.path)):
        return None
    return urlunsplit(("https", HOST, u.path.rstrip("/") or "/", u.query, ""))


def _event_url(href: str, base: str = BASE) -> tuple[str, str] | None:
    url = _source_url(urljoin(base, href))
    if not url:
        return None
    match = EVENT_ID.fullmatch(urlsplit(url).path)
    if not match:
        return None
    return BASE + "/event/" + match.group(1).lower(), match.group(1).lower()


def _external_url(href: str) -> str | None:
    u = urlsplit(href)
    if (u.scheme != "https" or not u.hostname or u.username or u.password
            or u.port is not None or u.hostname == HOST or u.fragment):
        return None
    return urlunsplit((u.scheme, u.netloc.lower(), u.path, u.query, ""))


def _is_beclass(url_or_text: str) -> bool:
    value = url_or_text.lower()
    if "beclass" in value:
        return True
    host = urlsplit(value).hostname
    return host == "beclass.com" or bool(host and host.endswith(".beclass.com"))


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: Node | None = field(default=None, repr=False)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self) -> str:
        return _text(" ".join(
            child.text() if isinstance(child, Node) else child
            for child in self.children
        ))

    def find(self, tag: str):
        return next((n for n in self.walk() if n.tag == tag), None)


class Tree(HTMLParser):
    def __init__(self, html: str):
        if len(html) > MAX_HTML_CHARS:
            raise ValueError("HTML response exceeds connector cap")
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs), parent=self.stack[-1]))

    def handle_endtag(self, tag):
        for pos in range(len(self.stack) - 1, 0, -1):
            if self.stack[pos].tag == tag:
                del self.stack[pos:]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].children.append(data)


def _card_for(heading: Node) -> Node:
    """Smallest parent containing heading plus nearby badges, not a whole list."""
    best = heading
    cur = heading
    while cur.parent and cur.parent.tag not in {"body", "main", "root"}:
        parent = cur.parent
        if sum(n.tag == "h3" for n in parent.walk()) != 1:
            break
        best = parent
        if parent.tag in {"article", "li"}:
            break
        cur = parent
    return best


def parse_listing(html: str, seed: str) -> tuple[list[dict], list[str]]:
    """Extract title + event link + indicative labels; never assert free/verified."""
    root = Tree(html).root
    found: dict[str, dict] = {}
    for h3 in (n for n in root.walk() if n.tag == "h3"):
        title = h3.text()
        if not title:
            continue
        card = _card_for(h3)
        anchors = [n for n in card.walk() if n.tag == "a" and n.attrs.get("href")]
        event = next((e for a in anchors if (e := _event_url(a.attrs["href"]))), None)
        if not event:
            # Some templates wrap an h3 in an anchor without extra card content.
            cur = h3.parent
            while cur and not event:
                if cur.tag == "a":
                    event = _event_url(cur.attrs.get("href", ""))
                cur = cur.parent
        if not event:
            continue
        url, eid = event
        if any(_is_beclass(n.attrs.get("src", "")) for n in card.walk() if n.tag == "img"):
            continue
        if any(n.tag == "a" and _is_beclass(n.attrs.get("href", "")) for n in card.walk()):
            continue
        if any(n.text().lower() == "beclass" for n in card.walk() if n.tag in {"a", "span"}):
            continue
        spans = {n.text() for n in card.walk() if n.tag in {"span", "small"}}
        labels = sorted(s for s in spans if s and len(s) <= 16 and s not in {"今天", "明天"})
        badge = any(n.text() == "免費" for n in card.walk()
                    if n.tag in {"span", "small", "div", "p"})
        if "免費" in labels:
            badge = True
        found.setdefault(url, {
            "eventgo_id": eid, "detail_url": url, "title": title[:300],
            "labels": labels[:12], "free_badge_hint": badge,
            "listing_seed": seed,
        })
    pages = set()
    seed_parsed = urlsplit(seed)
    for a in (n for n in root.walk() if n.tag == "a"):
        href = a.attrs.get("href", "")
        possible = _source_url(urljoin(seed, href))
        if not possible:
            continue
        p = urlsplit(possible)
        if p.path != seed_parsed.path:
            continue
        query = parse_qs(p.query)
        seed_q = parse_qs(seed_parsed.query)
        if any(query.get(k) != v for k, v in seed_q.items()):
            continue
        if "page" in query and len(query["page"]) == 1 and query["page"][0].isdigit():
            pages.add(possible)
    return list(found.values()), sorted(pages, key=lambda s: int(parse_qs(urlsplit(s).query)["page"][0]))


def parse_detail(html: str) -> dict:
    """Keep only a short fact reference; do not copy descriptions or full HTML."""
    root = Tree(html).root
    heading = root.find("h1")
    title = heading.text()[:300] if heading else None
    original = None
    for link in (n for n in root.walk() if n.tag == "a"):
        label = link.text()
        href = link.attrs.get("href", "")
        if any(value in label for value in ("前往活動", "官方網站", "活動官網", "立即報名")):
            original = _external_url(urljoin(BASE, href))
            if original:
                break
    return {"detail_title": title, "original_url": original}


def normalize(rows: list[dict], details: dict[str, str], observed_at: str) -> list[dict]:
    """Deduplicate by EventGo UUID, exclude BeClass, retain unverified hints."""
    unique: dict[str, dict] = {}
    for row in rows:
        url = row["detail_url"]
        if not _event_url(url):
            continue
        detail = parse_detail(details[url]) if url in details else {
            "detail_title": None, "original_url": None}
        original = detail["original_url"]
        if original and _is_beclass(original):
            continue
        # For a production candidate feed, do not admit unverifiable provenance.
        if not original:
            continue
        item = {
            "schema_version": 1, "source": "eventgo", "source_tier": "aggregator",
            "eventgo_id": row["eventgo_id"], "detail_url": url,
            "title": detail["detail_title"] or row["title"],
            "labels": row["labels"], "free_badge_hint": row["free_badge_hint"],
            "original_url": original, "listing_seed": row["listing_seed"],
            "observed_at": observed_at, "official_verified": False,
            "fee_status": "unverified", "registration_status": "unverified",
        }
        change = json.dumps({k: v for k, v in item.items() if k not in {
            "observed_at", "listing_seed"}}, ensure_ascii=False, sort_keys=True)
        item["content_fingerprint"] = hashlib.sha256(change.encode()).hexdigest()
        unique.setdefault(item["eventgo_id"], item)
    return list(unique.values())


def check_approved(registry: Path = REGISTRY) -> None:
    """Fail closed: CLI flags never override approved source access policy."""
    srcs = json.loads(registry.read_text(encoding="utf-8"))["sources"]
    eventgo = next((s for s in srcs if s.get("id") == "eventgo"), None)
    if not eventgo or not (
        eventgo.get("enabled_for_fetch") is True
        and eventgo.get("service_access_review") == "reviewed_with_evidence"
        and eventgo.get("endpoint_documentation_url")
        and eventgo.get("data_license_evidence")
    ):
        raise PermissionError(
            "EventGo automated access is not approved in M0 registry. "
            "Site terms restrict bulk automated access; acquire written permission first."
        )


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_robots() -> RobotFileParser:
    # No redirects, bounded bytes and timeout; missing/failed robots => no crawl.
    req = Request(ROBOTS, headers={"User-Agent": USER_AGENT})
    with build_opener(NoRedirect()).open(req, timeout=10) as resp:
        if resp.status != 200:
            raise PermissionError("Cannot establish robots policy")
        body = resp.read(MAX_ROBOTS_BYTES + 1)
        if len(body) > MAX_ROBOTS_BYTES:
            raise ValueError("robots.txt too large")
    robot = RobotFileParser()
    robot.parse(body.decode("utf-8", errors="replace").splitlines())
    return robot


def _next_page(candidates: list[str], page: int, seed: str) -> str | None:
    for candidate in candidates:
        p = urlsplit(candidate)
        if p.path == urlsplit(seed).path and parse_qs(p.query).get("page") == [str(page + 1)]:
            return candidate
    return None


async def crawl_live(
    seeds: list[str], *, max_pages: int, max_events: int, delay_seconds: float,
    registry: Path = REGISTRY,
) -> list[dict]:
    check_approved(registry)
    if not (1 <= max_pages <= 3 and 1 <= max_events <= MAX_OUTPUT_ROWS
            and delay_seconds >= 2):
        raise ValueError("Crawl limits exceeded")
    if not seeds or any(seed not in SEEDS for seed in seeds):
        raise ValueError("Unknown seed")
    robots = await asyncio.to_thread(load_robots)
    # Optional dependency: never pulled into API's production requirements.
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=20000,\n                               delay_before_return_html=1.0)
    results, details = {}, {}
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, text_mode=True)) as crawler:
        requests = 0

        async def read(url: str) -> str:
            nonlocal requests
            if not _source_url(url) or not robots.can_fetch(USER_AGENT, url):
                raise PermissionError("URL rejected by scope/robots")
            if requests:
                await asyncio.sleep(delay_seconds)
            result = await crawler.arun(url=url, config=run_cfg)
            requests += 1
            if not result.success or not result.html:
                raise RuntimeError("EventGo request unsuccessful")
            if _source_url(result.url) != _source_url(url):
                raise PermissionError("Crawl redirected outside exact authorized URL")
            if len(result.html) > MAX_HTML_CHARS:
                raise ValueError("HTML response exceeds cap")
            return result.html

        for name in seeds:
            seed = SEEDS[name]
            page_url = seed
            for page in range(1, max_pages + 1):
                if len(results) >= max_events or not page_url:
                    break
                items, pagination = parse_listing(await read(page_url), seed)
                for item in items:
                    results.setdefault(item["eventgo_id"], item)
                    if len(results) >= max_events:
                        break
                page_url = _next_page(pagination, page, seed)

        # Always fetch detail provenance; BeClass indirect results will be excluded.
        for item in list(results.values())[:max_events]:
            details[item["detail_url"]] = await read(item["detail_url"])

    return normalize(list(results.values()), details, datetime.now(timezone.utc).isoformat())


def run_offline(fixture: Path) -> list[dict]:
    obj = json.loads(fixture.read_text(encoding="utf-8"))
    if not isinstance(obj.get("listings"), dict) or not isinstance(obj.get("details"), dict):
        raise ValueError("fixture requires listings and details")
    rows = []
    for name, html in obj["listings"].items():
        if name not in SEEDS or not isinstance(html, str):
            raise ValueError("invalid fixture seed")
        parsed, _ = parse_listing(html, SEEDS[name])
        rows.extend(parsed)
    return normalize(rows, obj["details"], obj.get("observed_at", "2026-10-09T00:00:00+00:00"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated EventGo discovery; JSONL only")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--offline-fixture", type=Path, help="local fixture JSON; zero network")
    group.add_argument("--live", action="store_true", help="requires reviewed registry authorization")
    parser.add_argument("--seed", action="append", choices=sorted(SEEDS), default=None)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--max-events", type=int, default=20)
    parser.add_argument("--delay-seconds", type=float, default=2)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.live:
        rows = asyncio.run(crawl_live(args.seed or ["free"], max_pages=args.max_pages,
            max_events=args.max_events, delay_seconds=args.delay_seconds,
            registry=args.registry))
    else:
        rows = run_offline(args.offline_fixture)
    # Atomic replacement; no partial success file.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        temp.replace(args.output)
    finally:
        temp.unlink(missing_ok=True)
    print(json.dumps({"source": "eventgo", "candidates": len(rows),
                      "output": str(args.output), "verified": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

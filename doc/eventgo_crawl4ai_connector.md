# EventGo — independent Crawl4AI connector

Updated 2026-10-09. **Development checkpoint PARTIAL: live crawl, CI and 14-day acceptance NOT VERIFIED**. This connector intentionally does not join the production Event/Session/Registration schema or API and does not write to PostgreSQL, Flutter, Google, or personal tasks.

## Confirmed site routes

- Free: https://eventgo.tw/search?isFree=true
- Themes: /search?category=music, exhibition, lecture, outdoor, family
- Cities: /explore/cities/taipei, taichung, kaohsiung, tainan
- Detail: /event/{UUID}
- Pagination: query parameter page=2, etc.

EventGo homepage and actual page links were checked 2026-10-09. Date and free badges are *discovery hints*, never official validation of price, eligibility or registration windows. Details link out to an organizer/registration page.

**Permissions:** https://eventgo.tw/terms §2 (last updated 2026-04-23) says not to access the service at scale with automated tools. Public robots.txt access could not be verified. Do not run a live automated crawl without written website permission and robots/egress review. The M0 source registry sets EventGo enabled_for_fetch=false, and the script requires an approved registry state before it even imports Crawl4AI. This work has **not** granted permission. BeClass is **not a direct discovery/crawl source**. However, events discovered on EventGo or other approved sources that link to BeClass **must be retained** with the BeClass URL as `original_url`. The connector does not navigate to BeClass and does not treat its existence as proof of fee/registration validity.

## Files

- scripts/eventgo_connector.py — stdlib offline HTML parser, optional Crawl4AI headless browser, bounded seed/pagination/detail scanning, canonical UUID dedup, outbound referral retention (including BeClass), atomic JSONL.
- scripts/eventgo-requirements.txt — separately pinned Crawl4AI 0.9.4 (September 2026 security fixes). Do **not** install it in the production FastAPI requirements.
- backend/tests/test_eventgo_connector.py — offline permissions, URL scope, listing/detail, pagination, dedup and misleading free badge tests.
- data/free_events_m0_sources.json — EventGo remains disabled/pending source permission; BeClass is omitted as a **direct crawl source**, while inbound registration referrals are retained.

## Offline validation

Run:

~~~bash
python -m unittest discover -s backend/tests -p 'test_eventgo_connector.py'
python scripts/eventgo_connector.py --offline-fixture /path/to/eventgo-fixture.json --output /tmp/eventgo-candidates.jsonl
~~~

Fixture JSON must contain a listings object mapping configured seed names to HTML and a details object mapping canonical EventGo detail URLs to HTML. Optional observed_at should be an ISO8601 timestamp. If the original activity URL is absent, the item is dropped. A BeClass registration URL is retained as unverified provenance; never auto-fetch its content. No network dependency is needed for offline tests.

## Live command (currently **DENIED**, do not run before permission)

~~~bash
python -m venv .venv-eventgo
. .venv-eventgo/bin/activate
pip install -r scripts/eventgo-requirements.txt
crawl4ai-setup
python scripts/eventgo_connector.py --live --seed free --max-pages 1 --max-events 20 --delay-seconds 2 --output /tmp/eventgo-candidates.jsonl
~~~

Even with --live, the unapproved registry causes PermissionError before browser/network use. After a documented authorized source review, live code will require robots.txt readback (timeout, 256-KiB limit, no redirect), enforce robots can_fetch per URL, fixed HTTPS EventGo-only navigation, sequential requests, >=2s pacing, max three pages per seed, max 100 events, and bounded HTML. There is no login, anti-bot bypass, external HTTP follow, or AI extraction. A separate browser egress security assessment is still required before cloud use.

## JSONL contract — *temporary connector-level structure*

Each output record includes schema_version=1, source=eventgo, source_tier=aggregator, eventgo_id, detail_url, title, labels, free_badge_hint, original_url, listing_seed, observed_at, content_fingerprint, official_verified=false, fee_status=unverified, registration_status=unverified.

- Only HTTPS external original URLs from detail actions qualify. BeClass URLs are permitted as outbound `original_url` references but are not crawled or verified.
- Same EventGo UUID yields one candidate across seeds. Cross-platform duplicates and multiple sessions are **not** automatically merged.
- A free badge is not a verified zero-price claim. Fee/benefit ratio requires official original-site confirmation, including nonrefundable fees.
- The original page's long article text, source HTML, images, tokens and PII are not persisted.
- No DB/API/canonical-format integration, deployment or schedule is part of this checkpoint. Further mapping, reviewer signoff, live parse/robots, CI, runtime and 14-day evidence remain separate gates.

## Evidence table

| Gate | Status |
| --- | --- |
| Standalone code | Implemented on main; runtime NOT VERIFIED |
| Offline tests | To be verified from CI/test run |
| CI | NOT VERIFIED pending latest workflow readback |
| EventGo site authorization / robots | NOT VERIFIED; live disabled |
| Live listing / detail / pagination / outbound BeClass URL retention | NOT VERIFIED |
| PostgreSQL / API / UI / scheduler integration | NOT IMPLEMENTED by request |

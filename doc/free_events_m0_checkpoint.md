# Taiwan Free Events — M0 Source & Freshness Baseline Checkpoint

Date: 2026-10-09. Status: **PARTIAL** (source registry, offline evaluator, 8 regression tests and full CI = **PASS**; 14-day actual observations / service authorization / ingestion runtime = **NOT VERIFIED**). Calendar #8 DONE; M0 is the next approved priority.

## Explicit evidence and access decisions

| Source | Official evidence | Licensing / access boundary | Operational state |
|---|---|---|---|
| Ministry of Culture all-category arts events | https://data.gov.tw/dataset/6478 | Listing states Government Open Data License v1 and daily updates; API endpoint behavior, service rate/robots still must be reviewed separately | CATALOGUED / FETCH DISABLED |
| Ministry of Culture per-event detail | https://opendata.culture.tw/frontsite/openData/detail?datasetId=311 | Official licensed dataset; do not conflate permission for dataset use with unlimited site requests | CATALOGUED / FETCH DISABLED |
| TDX tourism events | https://tdx.transportdata.tw/api-service/swagger/tourism/0aed433a-9e95-404d-974c-4e70e29ae460 | Official Tourism V2 API; API credentials, quota and access terms required | CATALOGUED / FETCH DISABLED |
| data.gov.tw directory | https://data.gov.tw/ | Dataset discovery only; individual dataset terms must be checked | CATALOGUED / FETCH DISABLED |
| EventGo / yii.tw | Retained in Drive `life_assistantGPT/各官網連結方式.txt` | robots, ToS and site access **NOT VERIFIED**; may supply candidates only after lawful access, never sole proof that registration is open | CANDIDATES / FETCH DISABLED |

The Government Open Data License listing is verified as metadata, but no request quota or repeated automated fetch authorization is inferred. No runtime ingestion or Cloud Scheduler has been enabled by this checkpoint.

## Minimal implementation for M0

- `data/free_events_m0_sources.json`: versioned registry with provenance, license-evidence URL, endpoint-doc URL, manual access review, API-key requirement, expected interval and fail-closed `enabled_for_fetch=false`.
- `scripts/free_events_m0_baseline.py`: offline-only JSONL observation evaluator; HTTPS/provenance validation; rejects future or naive timestamps, impossible publication lag, unknown source, missing free-status truth. Computes per-source day coverage, consecutive-day span, unknown fee and registration starts, official-verified vs unverified free counts, publication-lag sample means only when publish timestamps exist.
- `backend/tests/test_free_events_m0_baseline.py`: no-fetch default, 14-day fixture not faked as production PASS, missing-day failure, source/license authorization guard, unknown values, temporal and pricing rules.
- Example invocation after acquiring independent authorized observations: `python scripts/free_events_m0_baseline.py --observations path/to/reviewed_observations.jsonl --as-of 2026-10-23T00:00:00+00:00`. No network I/O.

## Still required before M0 PASS

1. Human/source-specific robots/ToS, API terms, quotas and attribution review; only turn on fetch adapters for explicitly approved endpoints, starting with official datasets. Keep source proof and expiry.
2. Record **at least 14 contiguous actual observation days** (not mocked fixtures), sources and official organizer/registration proof, and publication→discovery latency. These observations are currently **NOT VERIFIED**; no source freshness, availability or discovery-rate numbers exist yet.
3. Curate verified FREE, CONDITIONAL FREE, PAID and UNKNOWN counterexamples across multiple sessions and separate registration opportunities. Unknown times remain null; never infer open time or fees.
4. Review Organizer/Event/Session/Registration Opportunity minimal schema and migration plan **before** M1 PostgreSQL mutation. M0 audit does not create production tables.
5. Accept explicit cost/precision/freshness thresholds using real baseline; decide Phase 1 final-gate scope freeze explicitly. Existing temporary ChatGPT scans are not the app ingestion pipeline.

The M0 script never publishes an overall `PASS`; operator acceptance is mandatory after 14-day evidence and source reviews. Implementation + tests alone = **PARTIAL**. Date 2026-10-09 is the registry creation day, not a fabricated observation day.

## GitHub verification on 2026-10-09

- Source commit [`ea8264562e3f260bb56f52500d3d917104e86a69`](https://github.com/tommylin15/life_assistant/commit/ea8264562e3f260bb56f52500d3d917104e86a69): source registry, offline M0 audit tool, 8 deterministic Python tests, this checkpoint.
- [CI run 37892185617](https://github.com/tommylin15/life_assistant/actions/runs/37892185617): **PASS** backend (428 tests including 8 M0-specific tests), Flutter Web, deployment-scripts. No M0 runtime deployment, scheduled network fetch or actual 14-day evidence was part of this CI.
- Current closure count for the original Phase 1 11 packages remains **8/11 (72.7%)**, with Calendar #8 closed. M0 is an additional approved priority, not a redefinition of that denominator.


## 并行 M1 說明（2026-10-09）

使用者要求不等待 14 天觀測結束，先開發後面需要的 M1，並保留修正追蹤。已新增 additive 0011 六表與離線 MoC Adapter / JSONL 去重，請見 `free_events_m1_checkpoint.md`；**M0 14 天真實連續來源觀測尚未驗收，不因 M1 程式存在而視作完成**。

## 2026-10-09 — Drive source selection supersedes earlier broader M0 inventory

- User narrowed prospective discovery sources to **five groups / six registry IDs**: Ministry of Culture all events and detail datasets, data.gov.tw catalog, TDX tourism API, EventGo, and yii.tw. Three previous source IDs (`citytalk`, `accupass`, `kktix`) are **removed from the active source allowlist**. BeClass was never a direct source; outbound BeClass registration links found elsewhere remain stored as unverified referrals and must not be fetched.
- Only `moc_events_all` remains enabled for network fetching; no API/robots/terms permission is inferred for TDX, data.gov.tw discovery, EventGo, yii.tw or MoC detail. No production DB rows, prior observations, or source evidence are deleted by this source-registry change.
- TDX credentials exposed in the private Drive TXT are not to be copied to source code, test fixtures or logs. Secret-storage migration and credential rotation remain separate, not executed by this change.
- Existing checkpoints above are historical evidence and may list superseded source counts; this section and the current registry determine the latest scope.

## 2026-10-09 — data.gov.tw catalog put on hold

- The user deferred the **general data.gov.tw directory** (`data_gov_catalog`) because dataset update labels do not demonstrate actual event publication/registration freshness. Registry access review becomes `deferred`; `enabled_for_fetch=false`, no catalog crawler/scheduler/dataset auto-enrollment. This is distinct from the independently reviewed MoC official data endpoint, which remains the one permitted fetch source.
- Reopen only after dataset-specific official authorization and at least 14 days of actual observations, with field-level evidence for first-seen lag, registration validity, unknown publication date, duplicates and stale events. No synthetic timestamps or numerical PASS claims. TDX remains pending credentials/terms and its own source-specific evidence.
- Shared candidate queue and source normalization remain an **implementation target**, not a production-verified replacement for the current MoC direct ingestion job. Structured MoC/TDX processing defaults to deterministic rules and zero AI; fuzzy text may be escalated later, without bypassing verified-only publication.

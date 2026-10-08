# CI/CD V3 cutover and destructive cleanup register — 2026-10-08

**Status: implementation committed only when evidenced by SHA; runtime cleanup NOT VERIFIED.**  This document is a control register, **not** proof that any Cloud Build trigger was disabled or any GCS/AR resource deleted.

## Hard dependencies and execution order

1. Pass main SHA mandatory CI gates, publish the public GHCR manifest digest, and verify anonymous retrieval.
2. Prove same-digest Cloud Run service candidate and existing acceptance Jobs, Firebase pinned Preview, approved real integration fixture, explicit promotion, stable live Service URL and production traffic readback.
3. Verify rollback policy/controlled drill and ten-revision cleanup dry-run/readback; fail closed if traffic, tags, rollback baselines or in-flight revisions are not protected.
4. Disable only verified legacy life_assistant Cloud Build triggers after actual **successful promoted** V3 GitHub Actions release. Preserve the trigger definitions and historical build logs. Read back `disabled=true`; don't delete triggers.
5. Run a **fresh read-only full inventory** of all GCS buckets, object manifests, GCP services/jobs and revision image dependencies, scheduled jobs, other projects and AR repositories. Classify each candidate as `CI_CD_ONLY_CONFIRMED`, `SHARED`, `BACKUP_OR_APP_DATA` or `NOT_VERIFIED`.
6. Only a positively proven `CI_CD_ONLY_CONFIRMED` item with no remaining direct/indirect dependencies may be deleted; save before/after object count, sizes, checksums/generations where applicable, exact resource IDs, owner, approval context and post-delete readback. Any ambiguity = leave in place.

## Resource-specific cleanup scope

| Resource | Cleanup allowed only when | Always protected |
| --- | --- | --- |
| Old GCS CI/CD objects | Exact object IDs/generations identify legacy Cloud Build source/logs, all build and rollback dependencies retired, no application references; delete only those exact objects | Any PostgreSQL/DB backups, ledger dumps, user files, application data or unclassified objects |
| Old CI/CD-only GCS bucket | Entire recursive listing/metadata reviewed, bucket is not shared, contains no backups/app data, all CI/CD users migrated and bucket no longer referenced, no retention/legal hold | Shared buckets, backups, application or Firebase-managed storage, unknown contents |
| AR Docker tags/images/digests | All Cloud Run service **and job** active/retained Revision dependencies (including historical 10 + protected rollback) use GHCR; affected image is not referenced by any other consumer | Referenced digest, tags pointing to protected digest, cross-service/shared images |
| Entire AR repository | Complete inventory shows no remaining image, revision, job, deployment, roll-back or other project dependency; repository exclusively retired CI/CD | Any repository that also serves unrelated projects, Jobs, or products |
| Cloud Run revisions | Per life_assistant-owned Service, newest 10 + any extra protected traffic/tag/rollback candidates; only after a full successful promoted live release | Live/receiving traffic, latest/only, previous rollback, tagged Preview candidate, Jobs |

The named existing container repository `cloud-run-source-deploy` may be shared; **never equate it with CI/CD-only** just because its name looks like a deployment repository. The previous `pilot-ledger-backups` GCS bucket (if present in actual inventory) must remain protected as backup data. Do not run recursive bucket deletion as a substitute for object-level classification.

## Pre-cutover constraints

- The old `.github/workflows/deploy-cloud-run.yml` still calls `gcloud builds submit` and the legacy `cloudbuild.yaml`/Cloud Build triggers still exist until actual cutover succeeds. V3 must not dispatch them.
- The new Actions release workflow is **manual full main SHA**, by deliberate governance policy. Having a workflow file on `main` does not prove a GHCR publish, Cloud Run 0% rollout or cutover occurred.
- Cloud Run Service supports public GHCR images. Cloud Run **Jobs** consuming the public GHCR digest still require actual readback. A failed job deployment blocks production promotion; no silent AR fallback.
- GHCR visibility is independently checked: a public GitHub repository does not prove public container package visibility. Anonymous pull failing is a blocked release.
- GCP WIF policy, GHCR package visibility, successful Actions logs, Cloud Run traffic, Firebase Preview and OAuth fixture must be observed; unverified conditions remain NOT VERIFIED.
- No CI/CD change authorizes deleting business records, PostgreSQL database or its backups. Explicit approval and proven dependency evidence are required for high-impact deletions.

## Runtime inventory data contract

The read-only `.github/workflows/v3-gcp-inventory.yml` inventories all relevant resource families and emits `PASS` vs `NOT_VERIFIED`, candidate names only for CI/CD-looking GCS buckets. Naming is not dependency proof; missing permissions do not mean resources do not exist.

The manual `.github/workflows/v3-cutover-disable-triggers.yml` verifies a **successful real promoted release Actions run**, confirms production serves a GHCR digest, disables only two exact known trigger IDs and reads back their status. It never deletes GCP buckets or image repositories.

**Final deletion status for every GCS/AR item at initial commit: NOT VERIFIED, NONE DELETED.**

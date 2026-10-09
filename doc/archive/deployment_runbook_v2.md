# CI/CD V2 — Historical Deployment Runbook

Archived 2026-10-10; do **not** execute. Use [V3 runbook](../deployment_runbook.md) and [V3 policy](../ci_cd_ghcr_release_policy.md).

# Life Assistant CI/CD V2 Deployment Runbook

Status: **RESUMED / OPEN / NOT CLOSED** (2026-10-08). This replaces the deployment
runtime release only after all V2 live gates pass. Existing product completion evidence
and existing provider FAIL records remain authoritative.

Policy is exclusively `PROJECT_RULES.md` → CI/CD V2 集中發布政策. main Push
runs CI only. Ready packages use the manual Release operations below.

## Trigger operations

- Push CI: `life-assistant-v2-main`, ID `70ca60f2-8519-40c4-9422-5ac78f1b355f`.
- Manual Release: `life-assistant-v2-release`, ID `892a893e-173f-49b2-9055-d5a9adc21496`.
- Both use the same 2nd Gen repository and `cloudbuild.yaml`; `_PIPELINE=ci`
  cannot enter Docker/deployment steps. Release requires exact-SHA Push CI PASS.

After Ready review/tests/contracts and successful Push CI, invoke:

```sh
gcloud builds triggers run life-assistant-v2-release \
  --project gen-lang-client-0593591102 --region us-central1 \
  --sha FULL_40_CHARACTER_SHA --substitutions _PIPELINE=release,_PROMOTE=false
```

Read candidate/Preview evidence and measured cost first. For the final
centralized release invoke the same exact SHA with `_PROMOTE=true`; it must
still match current main. Keep all provider gates. Do not use `[skip ci]` for
intermediate commits by default.

## Scope and identities

- Repository `tommylin15/life_assistant`, push branch regex `^main$` only.
- Existing second-generation connection `tommy-github`, repository
  `tommylin15-life_assistant`, region `us-central1`.
- `cloudbuild.yaml`, full `COMMIT_SHA`, `CLOUD_LOGGING_ONLY`; no nested source
  builds and no new legacy/multiregion bucket.
- Reuse `life-assistant-github-deployer`; no service account key.
- FastAPI remains Cloud Run; Flutter remains Firebase Hosting. Shared Codex
  remains the existing OmniAgent service. No OmniAgent/Janus code changes.
- Runtime identity: existing `omniagent-codex-life-client`; deployer has
  Service Account User only on it, caller has Secret Accessor only on
  `life-assistant-bundle`. Shared Codex uses metadata email/identity directly;
  no default Compute token-minting grant.
- Never mutate Scheduler configuration or execute scheduled business jobs.
  Only the three existing Life Assistant migration/acceptance jobs are updated.

## Release sequence

1. Check full SHA and current main; compare paths against deployed `release.txt`,
   covering every batched commit. Missing baseline fails toward complete testing.
2. Python import, backend tests, Alembic offline SQL, branding source checks;
   Flutter 3.47.3 analyze/tests/web build and branding equality.
3. Single Docker build/push, full SHA tag, resolve immutable digest.
4. Serialize mutable deployment operations by Cloud Build creation order;
   refuse a superseded main SHA and skip successful duplicate SHA/phase builds.
5. Existing migration job executes the release module, then no-traffic tagged
   candidate. Set the approved dedicated caller identity on API and the three
   existing jobs; preserve VPC, secrets and other existing settings.
6. Candidate health/readiness/401/OAuth; six existing core gates; actual HTTPS
   authenticated Google session, PostgreSQL persistence and owner-bound audit.
7. All existing post-deploy/Drive/Calendar/provider gates run against the release
   image. Gemini/OpenRouter diagnostics preserve aggregate failure.
8. Every backend-changing release gets an isolated Firebase Preview with Cloud
   Run `pinTag`, even when Flutter source is unchanged; this preview-only
   Flutter build is a deliberate safety cost and must never clone to Hosting
   live for a backend-only release. This avoids misrepresenting a browser test
   against the old live API as candidate compatibility. Stamp full candidate
   SHA and verify branding,
   cache, manifest, auth, API and all eight existing UI scripts. Their intercepted
   API tests are explicitly UI contracts, not proof of live integration.
9. Additional live browser reads use a real Google session and observe actual
   API responses without route interception, desktop and mobile.
10. `_PROMOTE=false` stops after candidate/preview. Only `_PROMOTE=true` may
    promote traffic and clone the exact verified preview to live.
11. Live exact SHA, true HTTPS/DB/browser gates, all UI and provider gates;
    Scheduler readback unchanged, job image readback, image cleanup dry-run.
12. Read back legacy Actions entrypoints: deployment and acceptance workflows
    expose `workflow_dispatch` only, preserving manual diagnosis/recovery.
    They retire automatically triggered deployment per the latest user policy.
    V2 is still not CLOSED until all live evidence passes.

## Recovery

- Before promotion failure: existing live traffic and live Hosting stay serving.
  Candidate and migration failure are failures, never CLOSED. Additive migration
  may have already run; no automatic downgrade or data deletion.
- After promotion failure: restore saved exact Cloud Run revision percentages.
  Use Firebase Console Hosting release history to roll back to the recorded
  previous version, then verify `release.txt`, `/auth/login`, `/api/v1/tasks`
  401, authenticated runtime and UI. Never restore DB by dropping tables.
- If Cloud Build is interrupted during promotion, inspect actual traffic and
  Hosting release before another deployment; use recorded previous revisions.
- A superseded build must not promote. Push latest work through CI and explicitly
  invoke the Ready manual Release SHA again.
- Evidence: Cloud Logging structured `gate/status/release_sha` lines; copy
  non-sensitive closure evidence and exact Build/revision/digest IDs into this
  repository. No GCS evidence write or staging/log bucket is required by V2.

## Artifact safety

Existing latest-only asynchronous policy can delete runtime/rollback images.
Keep it in **dry-run** during V2 validation. `cleanup_plan()` inventories all
Cloud Run revisions/jobs, protects their image references, checks SHA256 digest
syntax and only considers the three exact Life Assistant package names. Mutable
runtime references protect their entire package. A cleanup plan is evidence,
not deletion authorization or proof of physical deletion. Before any deletion,
refresh references and check the plan again; never delete another package.

## Cost comparison before cutover

The repository is public. Standard GitHub-hosted runners are free for public
repositories ([GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)).
The old pipeline also incurs GCP Docker build, Cloud Run acceptance and storage
cost; migration to Cloud Build does not remove these.

Default Cloud Build e2-standard-2 in us-central1 is $0.006/build-minute, with
2,500 promotional free minutes per billing account/month; allowance is shared
and cannot be assumed available ([Cloud Build pricing](https://cloud.google.com/build/pricing)).
The 120-minute bound caps build-worker list-price exposure at $0.72/build,
excluding existing runtime executions, egress and storage. No paid pool/new
database/bucket is requested. Successful duplicate SHA builds skip release work.

Observed old Firebase job `37714548567`: 2026-10-08 01:48:27–01:50:49 UTC,
142 seconds, standard public GitHub runner = $0 runner charge under that policy.
Existing Cloud Build `3d803831-b558-47a7-bfa6-eabba6ad23fd`: 111.20 seconds;
estimated e2-standard-2 worker list price $0.01112 before account free credits.
This is measured duration, **not a billing invoice**.

Existing Artifact Registry readback: 382.428 MB; free first 0.5 GB/account and
$0.10/GB-month above it ([Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing)).
Other projects/packages share account allowance. V2 creates no GCS objects or
bucket dependency; existing legacy bucket costs remain separate from V2.
Exact billed AR/GCS amounts require billing export/readback.

Record V2 actual build duration, machine, account free-tier usage and billing
evidence before formal cutover. No automatic claim that V2 is cheaper.

## Current blockers / baseline failures

- IAM auto-review initially rejected proposed repo writer / project log-writer /
  build viewer grants; user subsequently approved these exact minimal roles.
  Proposed GCS evidence writes have been removed; no storage grant is needed.
- Existing deployment `37714548574` failed at shared caller IAM policy access;
  do not grant broad IAM policy administration to CI as a workaround.
- Existing Notes/Habits/Shopping/Calendar UI runs at `a9a570c` failed exact
  release SHA checks; not demonstrated product bugs and not PASS.
- Drive #63 exit 91 and #70 exit 93 remain historical external-provider FAIL.
- Shared Codex consumer completion remains PARTIAL pending actual runtime proof.
- Core Tasks/Notes/Habits/Shopping models have no owner columns. The existing
  product is single-user: candidate must set existing `ALLOWED_GOOGLE_EMAIL`
  protection to the explicitly verified fixture owner; CI checks non-owner
  rejection, live gates check real owner session and invalid identity rejection.
  Shared Codex additionally retains stable owner/project isolation gates.
  This does not establish multi-owner core data isolation or add collaboration.

## Resume after user pause

1. Wait for explicit user resume. Read the final checkpoint in `acceptance.md`.
2. Confirm cancelled Build status, remaining Job executions, production traffic and Hosting version. Do not launch duplicate writing executions.
3. Confirm current main full SHA and applicable successful Push CI; a documentation push changes main SHA. Previous candidate is evidence for its original SHA, not the new SHA.
4. Review Ready/migration/API/auth contracts and invoke candidate-only manual Release for the chosen current SHA. Preserve all unfinished gates and existing Provider blockers.
5. Promote only after every required candidate/preview gate passes; then execute live/post-deploy gates. Do not downgrade DB or delete images merely because a Build was cancelled.

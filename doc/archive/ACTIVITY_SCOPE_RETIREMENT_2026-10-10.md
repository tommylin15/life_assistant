# Activity upstream retirement audit — 2026-10-10

User decision: only ChatGPT → Life curated pool. No Life event source discovery/crawlers, Queue, MoC/TDX/Excel, extra AI stage or formal publication gate.

Code cleanup commit [10335187](https://github.com/tommylin15/life_assistant/commit/10335187e3e2a338eed5c76b4d61bd2c18a605e3) removed five source GitHub Actions workflows (cron + one-shots), old EventGo/MoC adapters and M0/M1 CLI/manifest code, inactive Queue-worker Python service, related outdated tests and fetch-enabled source registry; the old Cloud Run source-job entrypoint is fail-closed. This does not delete deployed Cloud Run Jobs, existing PG schemas/data, or production secrets.

Previously scheduled ChatGPT event discovery task writing Sheets/Queue was disabled; its replacement direct Life API connector has NOT been tested. Any external GCP Cloud Scheduler to the old job still needs read-only runtime verification. Already-running or deployed old images are not retrospectively changed by a GitHub commit.

Legacy Alembic 0011–0014 remain intact; old verification-only catalog read API left for backward compatibility. New direct curated write API, table and UI remain not implemented until actual code/CI/deploy/runtime proves otherwise.

Git history and doc/archive retain original design/acceptance evidence. Current acceptance and backlog are in [CURRENT_STATE](CURRENT_STATE.md) and [todo](todo.md).

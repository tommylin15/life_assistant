# Historical CI/CD V2 project rules — SUPERSEDED

V2 Cloud Build policy removed from active governance on 2026-10-10. This is **not a current release route**. See [V3 policy](../ci_cd_ghcr_release_policy.md).

### 歷史政策：CI/CD V2（已被 V3 取代，保留原文）

## CI/CD V2 — 集中發布政策（2026-10-08）

- **Push CI 與正式 Release 分離**。main 更新只由 us-central1 Cloud Build 第二代 repository push trigger 執行受影響的 Python、Flutter、安全與部署契約測試，不自動部署 Backend、Candidate 或 Firebase 正式站。中間 commits 不預設 `[skip ci]`。
- 工作包 Ready 後，由 Codex 明確啟動第二代 repository **manual Release trigger**，指定完整 40 字元 SHA。Push 不可呼叫 Release。成功發布 SHA 是完整變更計算基準，不使用 HEAD^；缺少可信基準則完整驗證。
- Backend／Frontend 分別判斷是否需要發布，避免無意義 Docker／Flutter 重建；契約變更須驗證 candidate API 與前端相容性。不需 runtime 更動的工作包可略過部署，但仍需適當驗證。
- Ready Gate：implementation 完成 → Ponytail review 與受影響測試 PASS → migration/API/auth 契約確認 → Candidate acceptance → 集中 Cloud Run/Firebase 發布 → post-deploy runtime/UI/integration → 所有必要 gate PASS 才 DONE。
- 保留必要開發期真實測試：GCP dev/GCS、Cloud Run Candidate、PostgreSQL migration preflight、bounded acceptance Job、Firebase Preview、Gmail/Calendar/Drive 與 AI/Shared Codex probes；集中發布不禁止這些測試。
- Backend 沿用 FastAPI、PostgreSQL/Alembic、Artifact Registry；single immutable digest、no-traffic Candidate 全 gate 通過才切流量。Frontend 沿用 Firebase Hosting/Web/PWA/branding/OAuth redirect，Preview 通過後才 Live；Preview PASS 不等於正式站 PASS。
- 保留 Task/Project/Notes/Habits/Shopping、Calendar/Gmail/Drive、OAuth/Bridge/MCP、Post-deploy、External AI 與 Firebase 正式站 mandatory gates。Provider 既有 FAIL 是獨立 blocker，不刪 gate、不降門檻、不偽造 PASS。
- 不改生活總排程或每小時監控時間，不因 CI 執行它們，不重複啟動資料寫入型 Job，不影響既有執行中排程工作。Migration 必須 idempotent、有 recovery；保留 Activity Log、single-user owner allowlist、Shared Codex owner isolation 與資料完整性。
- 限制 build timeout/retry；部署依版本排序互斥，同 SHA/phase idempotent，舊 SHA 不覆蓋新 SHA。切換前保留正常 backend revision；Firebase 發布失敗可回復前版。中斷後先 readback 再恢復，禁止自動 DB downgrade/drop。
- 清理 image 前必須 dry-run、核對 immutable digest 與所有 Runtime 引用；只操作 Life Assistant packages，不清真實資料、不改其他專案、不新增未核准付費資源、不重大擴權。Shared Codex 使用既有 OmniAgent service，不建第二套、不修改 OmniAgent/Janus 程式。
- 比較 Public repo 免費 GitHub-hosted runner 與實測 Cloud Build 成本，計入共用 free tier、Cloud Run、Artifact Registry/GCS；不得假設 V2 省錢。固定 us-central1、CLOUD_LOGGING_ONLY，不建立 legacy multiregion log bucket；不要求 GCS evidence 存放。
- 最新追加指令要求 Push 不部署，因此舊 Actions 自動入口改為 manual diagnostics/recovery。V2 CLOSED 仍須真實 CI Push、完整 SHA Manual Release、migration、candidate、Preview/Live、runtime/UI/provider、Scheduler/Jobs readback 與成本 evidence 全部通過。
- `AGENTS.md` 只引用本政策；操作與恢復程序見 `deployment_runbook.md`。完成證據回寫 `acceptance.md`、`progress.md`、`todo.md`；單次 Build PASS、mock、localhost 不等於 live acceptance。

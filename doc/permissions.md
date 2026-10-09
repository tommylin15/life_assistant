# Life — Permissions and OAuth (2026-10-10)

**Principles:** least privilege, per-user consent, delayed scope grants, server-side authorization, no role escalation via UI and graceful degradation when permission is denied.

## Per-user Google connection

- Google identity login is not automatic authorization to all Gmail, Calendar or Drive data. Each signed-in user separately grants only the scopes needed by the feature. Current `backend/app/services/google_oauth.py` defines actual `SERVICE_SCOPES`; `backend/app/api/google_integrations.py` checks `current_user` and `user_sub`. Do not assume any scope not actually granted.
- Drive smart organization uses each user's own `DriveEnrichmentSettings` to control document content analysis, auto tags and related note suggestions. Consent OFF is binding even when administrator globally enables Life AI. Only the user can reconnect their personal Google account or change their own consent.
- No admin permission to inspect another person's Drive documents, email body, OAuth token, personal Calendar or saved UI preferences. Shared service status may be safely aggregated without such access.

## Admin & machine integrations

- Admin Center owner-only features require backend identity/role enforcement, audit logs, scoped read/write and separate confirmation of dangerous operations. The feature rollout list is an availability control, **not** data access privilege.
- A scheduled ChatGPT task may read eligible Queue rows and submit selected/skipped decisions only through an explicitly authorized Life API/connector. It never writes Queue columns directly; source changes/races and IDempotency are validated in Backend. Private plugin integration in scheduled execution must be E2E verified before claiming it functions.
- V3 GitHub deploy uses short-lived OIDC/WIF with separate least-privilege deployer, not long-lived keys. Production secret rotation and broad IAM changes require explicit consent.

## Revocation and failure

Access denied/consent revoked → no further protected reads/AI content transmission; preserve existing user content; show reconnect / unavailable UI and report appropriate 401/403. Validate with real account, cross-user and negative tests. Device-native camera/PIN/biometric/offline scopes remain future optional native capabilities, not current Flutter Web production permissions.

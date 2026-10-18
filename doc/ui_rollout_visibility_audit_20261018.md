# 2026-10-18 · Life Assistant UI and feature rollout audit

## Source of truth
Review based on current `main` implementation: `backend/app/api/ui_policies.py`, `backend/app/api/auth.py`, `backend/app/main.py`, and Flutter pages. This is **not** runtime production verification.

## Expired activities
- All ordinary activity views, saved lists, opportunity tabs, and paginated results exclude known expired/cancelled events; the second grouped-child read uses the same predicate to avoid reintroducing expired sessions.
- `ends_on` before today's **Asia/Taipei** date means expired. If no end is supplied, an old start alone cannot prove that an activity continues. Completely undated items remain discoverable until updated; no dates are invented.
- Closed/full opportunities and passed registration deadlines are excluded, even when saved. Activity DB records and saved actions are **retained**; nothing is deleted.
- Data is evaluated on a new API query. An already-open page does not guarantee automatic refresh at midnight.

## Capability matrix
| Admin key | UI | Effective gate / limit |
|---|---|---|
| today | Home | Frontend gate; no independent today router |
| tasks | Tasks | Backend router gate |
| calendar | Calendar | New gate on Google Calendar event endpoints in addition to integrations |
| projects | Projects | Backend router gate |
| notes | Notes | Backend router gate |
| habits | Habits | Backend router gate |
| shopping | Shopping | Backend router gate |
| life_inbox | Quick capture | Inbox and article router gates |
| explore | Activity Explore | `entry=explore` gated on curated list |
| opportunities | Opportunity tab/deep link | `entry=opportunities` gated on curated list |
| gmail_radar | Gmail Radar | Gmail radar backend router; public allowlist was missing and is now aligned |
| integrations | Google services | Shared Google Integration router gate; dependent Gmail and calendar consent must remain valid |
| drive | Drive file manager | **Owner-only** due account-level route restrictions, regardless of rollout setting |
| events | Old curated legacy entry | **Owner-only** legacy flag; current navigation redirects to Explore |

## Candidate-only UI
- Acceptance center is shown only to the authorized owner on fixed staging and Preview hosts; production direct navigation shows a neutral page. Server-side owner checks remain.
- Gmail Radar keeps useful user outcomes on production; technical scan metadata and implementation explanations are shown only on candidate.
- Admin feature statuses use user-oriented labels and distinguish Owner-only flags from public-capable switches.
- Further candidates for reducing visual noise: repeated feature introductions, duplicate refresh actions, and long secondary explanations; remove only after a separate per-feature usability check.

## Evidence / completion
| Layer | Status |
|---|---|
| Code review and patch | PASS |
| Unit and widget tests | NOT VERIFIED |
| GitHub CI | NOT VERIFIED |
| Staging Hosting / backend readback | NOT VERIFIED |
| Production same-SHA publication and general-user Gmail trial | NOT VERIFIED |

No DONE claim until the required build, deployment, and runtime evidence is read back.

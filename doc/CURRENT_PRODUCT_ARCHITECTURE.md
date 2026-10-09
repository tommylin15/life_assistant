# Life — Approved Product Architecture (2026-10-10)

**Approved design only; not proof of implementation.** Source of truth for reality is [CURRENT_STATE.md](CURRENT_STATE.md) and Github runtime. Tracking: [activity #10](https://github.com/tommylin15/life_assistant/issues/10), [Life AI #11](https://github.com/tommylin15/life_assistant/issues/11), [navigation/home #12](https://github.com/tommylin15/life_assistant/issues/12).

## Three distinct roles

1. **Life Backend** owns APIs, deterministic source adapters, PostgreSQL Queue, dedup/verification basics, operational jobs, AI consent enforcement, internal Drive AI Provider resolution, selected-pool persistence and audit.
2. **ChatGPT Chat daily tasks** (user-managed, separate from Life AI provider configuration) analyze pending official activity Queue rows through **read-only Life API** and evaluate permitted official-site workbook URLs. They submit **select/skip decisions** via an authenticated Life API; only Life Backend updates Queue state in the same committed transaction as the decision. Stale version/fingerprint fails closed. Scheduled connector API access must pass actual E2E before being claimed.
3. **Users** browse the terminal **selected activity pool** and decide for themselves; no extra official recommendation/registration-ready publication gate. Minor uncertainty allowed with explicit unknown labels. Nothing auto-writes personal Calendar/task/note for a viewed activity.

## Sources and data

- Ministry of Culture approved fixed JSON → normalized durable Queue only; TDX only after source approval; official website list is a separate approved-source allowlist. EventGo and yii.tw **will not be crawled**. General data.gov.tw catalog remains deferred.
- Exclude clearly stale, duplicate or unsafe source URLs; do not invent fee, deposit, benefit valuation, registration availability or timing. Retain source attribution, event identity, fingerprint, observed date and AI decision provenance. Existing MoC worker requires refactor: it currently auto-drains the Queue into legacy catalog.

## Admin Center vs personal settings

- **Admin modules**: (1) Sources & Queue, (2) ChatGPT curation outcomes / batch visibility, (3) Operations, (4) **Life internal AI Provider health/model/configuration and budget**, (5) **feature availability** (hidden/beta/open/maintenance), with backend owner-only authorization and audit.
- **Personal settings**: each user independently authorizes Google Drive/Gmail/Calendar and Drive AI document-consent, arranges allowed feature icons/ordering/placement, and configures their own Home dashboard cards. Admin cannot inspect user private Drive documents/Gmail or override individual AI consent.

## Flutter UI

- Reuse Material 3 Flutter Web. On compact/mobile, bottom `NavigationBar` with up to five entries; on desktop, `NavigationRail` / extended left rail; responsive auto is default, with user preference for left/bottom where feasible (phone left preference via drawer). Keep Home/More discoverable, allow reordering three middle favorites and other destinations.
- **Home** becomes a real, customizable dashboard: today's tasks, next calendar event, needs attention, habits, selected activities (after backend available), projects; optional notes, shopping, Drive AI (only consented). Per-user show/hide/order, no mandatory LLM Home inference, correct loading/empty/error/disconnected states.
- Global effective feature list = built-in capability registry ∩ admin rollout/role policy ∩ authenticated user permissions; personal layout can reorder but never enable a blocked feature.

## Release and ownership

Current `/today` is a placeholder and `/more/events` is verified-only, not the planned selected pool. New admin/curation APIs and UI are **NOT IMPLEMENTED** until source, tests, CI, production deployment and real user E2E are proven. Do not conflate ChatGPT task orchestration with OmniAgent global agent runtime; no new cross-project role.

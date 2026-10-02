# Design System #2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved Warm Knowledge Home, Tasks, and Project mockups into a single reusable Flutter design-system baseline with tokens, shared components, and explicit responsive rules.

**Architecture:** Keep `AppColors`, `AppTheme`, and `AppTokens` as the semantic token layer. Add a small reusable component layer under `lib/app/design_system/` instead of page-specific visual helpers. Encode the approved responsive contract in code and a focused GitHub checkpoint spec; existing pages migrate to the baseline when touched, while all new UI must use it immediately.

**Tech Stack:** Flutter 3.47.3, Material 3, flutter_test.

**Spec:** `doc/design_system.md`; approved visual reference is the Drive document `life_assistant Design System — Final UI Reference` (`1QnKn-UbAadpCY58EYdatvbxkRLOWKHC8V4rTYoEXLy8`).

## Global Constraints

- Warm Knowledge is the only formal visual track; legacy `AppTheme.clean` may remain only as a deprecated alias to `AppTheme.light`.
- No shared component may hard-code design colors when a semantic token exists.
- Minimum interactive touch target is 44x44.
- Compact `<600`; medium `600–839`; expanded `840–1199`; roomy desktop `>=1200`.
- App content max width is 1040; desktop context panels are optional and must not force horizontal scrolling.
- New UI uses the shared baseline immediately; existing pages adopt it opportunistically when modified.

## Review Focus

- Very narrow phone widths still keep page padding and primary actions reachable.
- Widths around 840 do not show both bottom navigation and NavigationRail.
- Widths around 1200 change rail/context affordances without changing content semantics.
- Status chips remain readable in light and dark themes and never rely on color alone.
- Empty/error/loading surfaces do not impose fixed heights that clip large text.

---

### Task 1: Lock the code contract with RED tests

**Files:**
- Modify: `test/design_system_test.dart`

**Interfaces:**
- Consumes: existing `AppTheme`, `AppTokens`.
- Produces: executable contract for new token and component baseline.

- [ ] Add tests for motion/touch/layout tokens and required shared component source.
- [ ] Push to `main` and verify CI fails because the baseline is not implemented yet.

### Task 2: Add semantic tokens and reusable components

**Files:**
- Modify: `lib/app/theme/app_tokens.dart`
- Create: `lib/app/design_system/app_components.dart`
- Create: `lib/app/design_system/design_system.dart`

**Interfaces:**
- Produces: `AppPageFrame`, `AppSectionCard`, `AppStatusChip`, `AppStatePanel`, `AppMotion`, and `AppTouchTarget`.

- [ ] Add minimal token values matching the approved visual contract.
- [ ] Implement shared components using ThemeData and semantic colors/tokens only.
- [ ] Run CI and keep the full Flutter suite green.

### Task 3: Publish the responsive/adoption checkpoint

**Files:**
- Create: `doc/design_system_checkpoint_v0_2.md`

**Interfaces:**
- Consumes: approved Drive mockups and implemented token/component names.
- Produces: single responsive/adoption contract for future UI work.

- [ ] Record the four window classes, navigation behavior, max-width rules, shared components, and adoption rules.
- [ ] Record that mockups are visual acceptance targets, not production data contracts.

### Task 4: Verification and closure evidence

- [ ] Verify CI analyze/test/web build for the final implementation SHA.
- [ ] Verify Firebase deployment if the successful CI triggers it.
- [ ] Update project progress only after implementation and required verification are green.

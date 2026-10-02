# Warm Knowledge Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the approved Warm Knowledge mockup the single project-wide visual baseline for the current Flutter web app without changing domain behavior.

**Architecture:** Keep visual decisions centralized in `lib/app/theme/`: semantic colors in `app_colors.dart`, spacing/radius/responsive/layout values in `app_tokens.dart`, and shared Material component behavior in `app_theme.dart`. `AppShell` consumes the shared responsive tokens; Tasks, Projects, Notes, More, and placeholder pages inherit shared component styling instead of creating a parallel custom widget system.

**Tech Stack:** Flutter / Material 3 / Dart widget tests / GitHub Actions / Firebase Hosting

**Spec:** `doc/design_system.md`

## Global Constraints

- Warm Knowledge is the only formal visual direction; do not retain a second cool/teal `AppTheme.clean` design track.
- Preserve all existing API/domain behavior and production routes.
- Light mode keeps the approved warm cream surfaces and sage primary accent already defined in `AppColors`; dark mode remains supported.
- Touch targets remain at least 44×44.
- System typography and text scaling remain supported.
- Navigation uses bottom navigation below 840 logical pixels and navigation rail at 840 logical pixels or wider.
- Page-level actions may switch to desktop placement at 720 logical pixels or wider.
- Standard content maximum width is 1040 logical pixels.
- Shared Material primitives (Card, Input, Button, Chip, Checkbox, FAB, Navigation, Dialog/Sheet) are themed centrally before introducing custom wrappers.
- This package establishes the design-system baseline; it does not invent unfinished Home or Calendar product features.

## Review Focus

- Width exactly at 840 must select desktop navigation; 839 must remain bottom navigation.
- Very wide desktop layouts should look like a readable sidebar, while medium desktop widths remain compact enough for content.
- Light and dark themes must both remain readable after shared component changes.
- Existing Task / Project / Notes interactions and selectors must not regress because of visual changes.
- Visual tokens must not create a second source of truth through page-local hard-coded colors.

---

### Task 1: Lock the approved visual contract with tests

**Files:**
- Create: `test/design_system_test.dart`
- Modify: `test/web_app_shell_test.dart`

**Interfaces:**
- Consumes: existing `AppTheme`, `AppColors`, `AppShell`.
- Produces: regression tests for single-theme source, shared component styling, centralized responsive tokens, and wide desktop sidebar behavior.

- [ ] **Step 1: Write failing design-system tests**

Assert that `AppTheme.clean` no longer exists, `app_tokens.dart` contains the shared responsive/layout contract, Warm Knowledge owns NavigationRail/FAB styling, and a 1200px shell uses an extended rail.

- [ ] **Step 2: Run the relevant tests and verify RED**

Run: `flutter test test/design_system_test.dart test/web_app_shell_test.dart`
Expected: FAIL because the current source still contains `AppTheme.clean`, has no shared breakpoint/layout tokens, has no explicit Warm Knowledge rail/FAB theme, and the wide rail is not extended.

### Task 2: Centralize tokens and shared component styling

**Files:**
- Modify: `lib/app/theme/app_tokens.dart`
- Modify: `lib/app/theme/app_theme.dart`

**Interfaces:**
- Produces: `AppBreakpoints`, `AppLayout`, and the single `AppTheme.light` / `AppTheme.dark` theme contract.

- [ ] **Step 1: Add responsive and layout tokens**

Add exact constants for page actions (720), navigation rail (840), roomy desktop (1200), content max width (1040), and adaptive page horizontal insets based on the existing spacing scale.

- [ ] **Step 2: Remove the unused `AppTheme.clean` track**

Keep Warm Knowledge light/dark as the only formal theme pair.

- [ ] **Step 3: Theme shared Material components**

Set NavigationRail, NavigationBar, FAB, Checkbox, Card, inputs, buttons, chips, dialogs/sheets where supported, and selected/disabled states from semantic colors/tokens. Keep low elevation and soft borders.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `flutter test test/design_system_test.dart`
Expected: PASS.

### Task 3: Adopt responsive shell behavior

**Files:**
- Modify: `lib/web/app_shell.dart`
- Test: `test/web_app_shell_test.dart`

**Interfaces:**
- Consumes: `AppBreakpoints.navigationRail`, `AppBreakpoints.roomyDesktop`.
- Produces: bottom navigation on compact widths, compact rail on medium desktop, extended sidebar-like rail on roomy desktop.

- [ ] **Step 1: Replace the shell-local breakpoint with design tokens**

Use the shared 840px navigation breakpoint.

- [ ] **Step 2: Extend the rail on roomy desktop**

At 1200px or wider, use an extended NavigationRail with a wider branded/sidebar presentation; at 840–1199 keep a compact rail.

- [ ] **Step 3: Run shell tests and verify GREEN**

Run: `flutter test test/web_app_shell_test.dart`
Expected: PASS for compact, breakpoint, medium rail, and roomy desktop cases.

### Task 4: Freeze the approved specification and adoption baseline

**Files:**
- Modify: `doc/design_system.md`
- Modify: `doc/progress.md`
- Modify: `doc/todo.md`

**Interfaces:**
- Produces: durable visual decision record and package-2 acceptance checklist.

- [ ] **Step 1: Record the approved 2026-10-02 mockup direction**

Document warm cream canvas, sage accent, low-contrast cards, clean hierarchy, mobile bottom navigation, desktop sidebar, and the rule that existing product pages adopt the central theme rather than creating local palettes.

- [ ] **Step 2: Document responsive/layout tokens and shared component baseline**

State the 720/840/1200 breakpoints, 1040 content width, spacing rules, and shared Material primitive ownership.

- [ ] **Step 3: Keep package #2 IN PROGRESS until CI/deploy/runtime visual acceptance is evidenced**

Do not mark 2/11 DONE from source changes alone.

### Task 5: Full verification and production acceptance

**Files:**
- No new production files unless verification exposes a defect.

**Interfaces:**
- Consumes: implementation and tests from Tasks 1–4.
- Produces: package #2 PASS/FAIL/NOT VERIFIED evidence.

- [ ] **Step 1: Run the Flutter suite and web build in CI**

Expected: analyzer, all Flutter tests, and web build PASS.

- [ ] **Step 2: Verify Firebase Hosting deployment for the exact release SHA**

Expected: deploy workflow PASS.

- [ ] **Step 3: Re-run existing Task / Project / Notes production UI acceptance where applicable**

Expected: behavior remains GREEN after visual changes.

- [ ] **Step 4: Check responsive production presentation at mobile and desktop widths**

Verify navigation mode, no overflow/clipping, readable hierarchy, Warm Knowledge surfaces, sage actions, and >=44px controls.

- [ ] **Step 5: Close package #2 only with complete evidence**

If implementation + tests + CI + deployment + runtime UI acceptance are all PASS, update tracker to 2/11 = 18.2%; otherwise report PARTIAL with the missing evidence.

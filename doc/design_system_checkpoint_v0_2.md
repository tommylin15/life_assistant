# life_assistant Design System #2 — Warm Knowledge Checkpoint

Status: **APPROVED BASELINE / IMPLEMENTATION CONTRACT**

This checkpoint converts the approved final UI mockups into a code-facing contract. It supplements `doc/design_system.md`; it does not replace production behavior, API contracts, or data rules.

## 1. Approved visual reference

The approved visual reference is stored under the allowed Drive root `life_assistantGPT`:

- Document: `life_assistant Design System — Final UI Reference`
- Drive file ID: `1QnKn-UbAadpCY58EYdatvbxkRLOWKHC8V4rTYoEXLy8`
- Embedded final templates:
  1. Home / Dashboard
  2. Tasks
  3. Project

These three screens are **visual acceptance targets**, not literal production-data contracts. Real data, permissions, API behavior, navigation availability and runtime state continue to follow GitHub/runtime implementation.

## 2. Single visual direction

The only formal design track is **Warm Knowledge**:

- warm off-white / cream canvas and surfaces
- sage green as the primary interaction/progress accent
- calm information density
- soft rounded cards and inputs
- restrained borders and shadows
- strong content hierarchy
- low-saturation semantic status colors
- readable light and dark themes

`AppTheme.clean` is legacy compatibility only. It must not become a second palette or a separate product direction.

## 3. Token source of truth

Code source:

- `lib/app/theme/app_colors.dart`
- `lib/app/theme/app_theme.dart`
- `lib/app/theme/app_tokens.dart`

### Spacing

4pt grid:

- `xs = 4`
- `sm = 8`
- `md = 12`
- `lg = 16`
- `xl = 24`
- `x2l = 32`
- `x3l = 48`

### Radius

- `sm = 8`
- `md = 12`
- `lg = 16`
- `xl = 20`
- `pill = 999`

### Motion

- fast: `150ms`
- standard: `200ms`
- slow: `250ms`

Motion exists only to clarify state changes. Avoid decorative animation that competes with task/content comprehension.

### Interaction

- minimum touch target: `44x44`

### Layout

- content max width: `1040`
- NavigationRail minimum width: `80`
- extended NavigationRail width: `184`
- optional desktop context panel width: `320`

## 4. Responsive contract

Responsive behavior is based on semantic window classes, not page-specific magic numbers.

| Window class | Width | Primary navigation | Content behavior |
|---|---:|---|---|
| Compact | `< 600` | Bottom navigation | One primary column; primary actions reachable without horizontal scrolling |
| Medium | `600–839` | Bottom navigation | One main column with wider gutters; secondary controls may move inline |
| Expanded | `840–1199` | NavigationRail | Main content remains max 1040; optional secondary information may sit beside content only when it fits |
| Roomy | `>= 1200` | Extended NavigationRail | Wider contextual panels are allowed; information hierarchy must remain content-first |

Additional action-layout breakpoint:

- `720`: page actions may move from floating/mobile treatment to app-bar or inline treatment.

Navigation and layout rules must come from `AppBreakpoints`, `AppResponsive` and `AppLayout`. New page code should not introduce a different breakpoint for the same behavior.

## 5. Shared component baseline

Code source:

- `lib/app/design_system/app_components.dart`
- barrel import: `lib/app/design_system/design_system.dart`

### `AppPageFrame`

Use for normal page content. It:

- centers content
- constrains content to the shared max width
- applies responsive horizontal gutters
- avoids page-specific duplicated max-width and padding literals

### `AppSectionCard`

Use for dashboard sections, project summaries, task groups, notes summaries and Drive sections when a card container is needed.

It inherits visual treatment from `AppTheme`; individual pages should not recreate card border/radius/shadow rules.

### `AppStatusChip`

Use for human-readable statuses such as success, warning, danger and informational states.

Status must always include text and/or icon semantics. Color alone is not sufficient.

### `AppStatePanel`

Use as the common non-fixed-height basis for empty, error and informational/loading states.

It must remain safe under larger text scaling and narrow widths.

### Material primitives controlled by `AppTheme`

Use standard Flutter components where the shared theme already owns their appearance:

- `FilledButton`
- `OutlinedButton`
- `IconButton`
- `TextField` / `InputDecoration`
- `FilterChip` / `Chip`
- `Card`
- `NavigationBar`
- `NavigationRail`
- `FloatingActionButton`

Do not wrap a Material primitive merely to rename it when `AppTheme` already provides the required behavior.

## 6. Page composition derived from the three approved templates

### Home / Dashboard

Priority order:

1. current focus / greeting
2. today tasks
3. active projects
4. recent notes
5. quick access

Desktop may present paired sections; compact mode collapses them into one vertical reading order.

### Tasks

The task list is the primary surface.

- Today / Upcoming / All-style modes remain visually lightweight
- category/status chips are secondary to the task title
- wide layouts may show contextual statistics or calendar information
- compact layouts keep task completion and create actions immediately reachable

### Project

Project overview may combine:

- progress
- task summary
- recent tasks
- related notes
- Drive files
- project metadata

Do not turn the page into a dense admin dashboard. Main project work remains visually dominant.

## 7. Adoption rule

From this checkpoint onward:

1. New UI must use Warm Knowledge tokens and the shared baseline immediately.
2. Existing pages should migrate to shared components whenever they are materially modified.
3. Do not add raw design colors such as `Color(0x...)` inside shared components or new feature UI when a semantic token exists.
4. Do not add a new breakpoint when an existing breakpoint expresses the same behavior.
5. Do not create a second theme track.
6. Product behavior and data semantics remain independent from the visual mockup examples.

## 8. Acceptance criteria for Design System #2

Design System #2 is technically ready to close when all of the following are true:

- the three final mockups are retained as the approved visual reference
- Warm Knowledge is the single formal style
- semantic token source is present in GitHub
- responsive classes and navigation rules are explicit
- shared reusable component baseline is present
- Flutter analyze/test/web build are green on the implementation SHA
- required deployment triggered from that green CI is verified

Page-by-page visual migration is follow-on UI adoption work, not a reason to fork the design system.

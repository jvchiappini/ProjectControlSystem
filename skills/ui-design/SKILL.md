---
name: ui-design
description: Design distinctive, production-grade interfaces (web, mobile, desktop) instead of generic AI-looking UI. Use when building, redesigning, critiquing or auditing a user interface: analyze the repo, infer the product type and what it lacks, ask focused questions, record a design system, plan, build with tokens, then verify with a scored critique and a P0-P3 audit.
---

<!-- generated from .control/skills/ui-design.md by `update.py --build-manifest`; edit that file -->

Without ProjectControl (no `.control/`): `prompts/ui-discovery.md` is `discovery.md` next to this file; keep the design doc in `DESIGN.md` (or the project's docs folder); turn `pctl task-new` into a checklist and ADRs into a short Decisions section of the design doc; skip `pctl ui-scan`, `dupes` and `reuse` (search the code yourself).

# Skill: ui-design

Goal: interfaces that look designed by a senior product designer for THIS
product and THIS audience, never a generic template. Understand first,
ask second, decide in writing, then build and verify.

The design source of truth is `architecture/design-system.md` (the
"design doc"). Every phase reads it; only phases 3 and 7 write it.

## Which phases to run

| Situation | Phases |
|---|---|
| Greenfield (no UI code yet) | 1 → 7, all; phase 4 starts with Foundations |
| Brownfield without design doc | 1 → 7; phase 1 includes the Consistency audit |
| New page/feature in a product with a design doc | 1 (light), 2 (only gaps), 4, 5, 6 |
| Small UI change | read design doc, 5, 6 (light) |
| "Critique / audit / review the UI" | 6 only, findings become tasks |
| Steering request ("bolder", "polish"...) | see Steering vocabulary, then 6 |

## 1. Analyze (silent, before any question)

Never ask what the repository can answer. Collect, with `file:line`:

- Product: `PROJECT.md`, `GOALS.md`, README, `pctl search <words>`.
- Stack: framework, routing, styling approach (CSS, modules, Tailwind,
  CSS-in-JS), component library, icon set, existing theme/tokens files.
- What exists: routes/pages, shared components (`pctl reuse button card`),
  current fonts, colors, radii, spacing values in use.
- Data and content: models, schemas, seed/fixtures, API responses. They
  reveal the domain (product fields like `size`, `isbn`, `calories`,
  `license_key` say what kind of store it is).
- Brand assets: logo, images, favicon, existing marketing copy.

Write the inferences down before moving on (product archetype, audience
guess, maturity: greenfield / has UI / has design system). Save surprises
with `pctl context-note --tipo fact`.

### Consistency audit (brownfield)

Before proposing anything new, list what the existing UI already gets
wrong, with `file:line`:

- `pctl ui-scan [paths]`: accessibility issues, generic-AI patterns and
  how many distinct colors, font sizes and radii are in use (many
  near-duplicates = no system).
- Duplicated components (two buttons, three modals): `pctl dupes`,
  `pctl reuse <component>`.
- Hierarchy breaks, missing states (empty, loading, error), overlays
  used for the wrong job, accessibility gaps, render bottlenecks.

The audit seeds the design doc (consolidate, do not reinvent) and the
plan. Refactors stay non-disruptive: keep the current stack and public
component APIs, migrate page by page, large ones go through
`refactor-plan.md`.

## 2. Understand the domain and ask

Open `prompts/ui-discovery.md`. It holds the archetype playbooks (what a
store, a SaaS, a dashboard... must have) and the question bank.

1. Pick the archetype and sub-type (e.g. store → fashion boutique vs
   electronics vs grocery). If two fit, that is the first question.
2. From the playbook, list what this product needs that the codebase does
   not have yet (pages, features, states, trust elements). This list is
   the core of the plan; propose it, do not silently build it.
3. Ask in rounds:
   - Round 1, up to 8 questions, the ones that change the design most:
     audience, personality, references, content reality, scope.
   - Round 2 only for gaps the answers opened. Stop as soon as the
     direction is clear; never more than 3 rounds.
   - Every question states the inferred default: "I assume X because Y;
     correct?". The user can answer "yes to all".
   - Group by topic, number them, keep each to one line. Offer options
     when the space is known (e.g. three personality sets).
   - If the agent has a structured question tool, use it.
4. If the user declines to answer, proceed with the stated defaults and
   record them as assumptions in the design doc.

## 3. Direction and design doc

1. Propose 2-3 distinct named directions (e.g. "Editorial calm",
   "Bold street", "Warm craft"). Each: one paragraph of feeling, type
   pairing, palette idea, layout character, motion character, one
   reference. Recommend one and say why it fits the audience.
2. After the user picks: `pctl arch-touch design-system --crear-archivo`
   and fill `architecture/design-system.md` with these sections:
   - Product: one paragraph, archetype, audience, primary action.
   - Personality: 3 adjectives, and 3 it must never feel like.
   - Assumptions: defaults the user did not confirm.
   - Tokens: font families and roles; type scale; color roles (bg,
     surface, text, muted, primary, accent, success, warning, danger,
     border) with values for light and dark if both exist; spacing
     scale; radii; shadows/elevation; motion durations and easings;
     breakpoints. Values, not code.
   - Components: inventory with status (exists `file:line` / to build).
   - Pages: list with the primary action of each.
   - Rules: project-specific dos and don'ts.

   `pctl ui-scan` reads this doc: every hex color in it is an allowed
   color, and backticked names on lines that mention "font" are the
   allowed fonts (e.g. "Fonts: `Fraunces` display, `Source Sans 3`
   text"). A line `ui-scan-allow: rule-a, rule-b` turns rules off for
   the project; each one needs an ADR saying why.
3. Record the direction as an ADR (`decision-record.md`): the chosen
   direction, the rejected ones and why. Later decisions (brand font,
   an intentional exception to a rule below) also get an ADR, so no
   future session re-argues them.

## 4. Plan

- Small scope: an ordered checklist in the task body.
- Larger scope: one task per page or component group (`pctl task-new`,
  `--tipo feature`), with acceptance criteria that include states and
  breakpoints; an initiative in the roadmap if it spans weeks.
- Foundations (greenfield): a modular structure that separates
  primitives, layouts, feature/views, hooks or state, and data services,
  following the framework's conventions; design tokens wired for light
  and dark; the base primitives: button, input, select/dropdown,
  modal/dialog, popover, toast, card, badge, skeleton, empty state.
  Stack choices the repo does not fix (language, styling) are a phase 2
  question; default proposal: TypeScript in strict mode and the styling
  approach the framework favors (e.g. Tailwind with tokens in its theme,
  or CSS modules).
- Build order: tokens → primitives (button, input, card, badge...) →
  layout shell (header, nav, footer) → the page with the main conversion
  → remaining pages → states (empty, loading, error, success) → polish.
- Cross-page journeys (checkout, onboarding, sign-up) get a flow
  (`flow-mapping.md`).

## 5. Build

Follow `lean.md` (reuse components before writing new ones) and the
design doc. Use tokens, never ad-hoc values; a missing value is added to
the design doc first. Principles:

- Typography: a deliberate pairing (display + text) chosen for the
  personality; a modular scale with clear hierarchy (few sizes, strong
  contrast between levels); body ~16px+, line-height ~1.5, line length
  ~60-75 characters; balanced headings and no single word alone on the
  last line where the platform allows.
- Color: one dominant neutral family, one primary, at most one accent;
  color carries meaning (action, state), not decoration; text contrast
  WCAG AA minimum (4.5:1 body, 3:1 large text and UI controls); tinted
  neutrals over pure gray; dark mode designed, not inverted.
- Layout and space: a spacing scale with rhythm (related things close,
  groups far); vary density and composition between sections; a clear
  focal point per screen; alignment to a grid; generous whitespace where
  the content is premium, dense where the user scans (tables, lists).
- Imagery: real or art-directed images in consistent ratio and
  treatment; illustrations and icons from one family; no stock cliches.
- Motion: purposeful (feedback, continuity, attention), 150-300ms for UI,
  ease-out for entering, respects reduced motion; no decoration loops;
  zero layout shift (reserve space for images, async content, skeletons
  matching the final layout). Charts: tooltips with value and share,
  dim the unselected series on hover.
- Interaction: every interactive element has hover, focus-visible,
  active, disabled and loading states; touch targets ~44px; forms with
  inline validation and helpful errors.
- Optimistic UI: reversible mutations (toggle, rename, reorder, delete
  with undo) update the interface at once and roll back with a toast on
  failure. Never optimistic for payments, irreversible or
  permission-dependent actions; those show progress and wait.
- Overlays, each for one job:
  - Popover/dropdown: light, non-blocking choices; click outside closes
    with no consequence.
  - Modal/dialog: focused, blocking create/edit or confirmations with
    explicit confirm/cancel; focus trapped and restored; never modal on
    modal.
  - Toast: one global system for async confirmation, warnings and
    errors that do not need a decision; errors that need action stay
    inline.
  - Dedicated page with breadcrumbs or back: anything deep enough to
    need its own URL, history or sharing.
- Code: presentation separated from data and business logic; every
  data-driven view handles loading, error and empty; strict types where
  the language has them (no implicit any); semantic class or token
  names, no magic values.
- Copy: specific, short, in the product's voice; buttons say the action
  ("Add to cart", not "Submit"); empty states explain and offer the next
  step.
- Responsive: design mobile and desktop on purpose, not only stacking;
  no horizontal scroll; content does not touch screen edges.
- Accessibility (never cut): semantic HTML, labels, alt text, keyboard
  path, focus order, no information by color alone.

### Generic-AI patterns to avoid

They make unrelated products look the same. Use one only when the design
doc chooses it on purpose (with an ADR):

- Default fonts used without a reason (Inter, Roboto, Arial, system UI as
  the whole identity); one font for everything.
- Purple-to-blue or neon-cyan gradients on dark backgrounds; gradient
  text; glowing accents; background radial halos and blurred blobs.
- Cards inside cards; every section a grid of identical cards; a thick
  colored stripe on one side of rounded cards; hairline border plus a
  wide soft shadow on everything; very large radius on everything.
- A rounded-square icon tile above every heading; a pill badge above the
  hero headline; tiny numbered labels on every section; oversized icons.
- The stock hero: big centered headline, subtitle, two buttons, a row of
  "big number" metrics.
- Identical vertical rhythm and padding for every section.
- Pulsing dots, blinking cursors, auto-scrolling marquees, bouncy easing
  without a reason.
- Copy: empty superlatives ("seamless", "supercharge", "world-class",
  "unlock"), "Not X. It's Y." contrasts, em-dash in every sentence,
  placeholder lorem or fake testimonials presented as real.

## 6. Verify: critique and audit

Run `pctl ui-scan --changed` first: P1 findings in lines the task
touched are fixed before anything else. A deliberate exception is
silenced on its line with a `ui-scan-disable <rule>` comment (or
`ui-scan-disable-file <rule>`) plus the reason. `--apply` turns
findings into one task per rule; `--fail` exits 2 for CI. The scan reads
code only; real contrast and overflow need the rendered page.

Then look at the result, not only the code. If a browser or screenshot tool
is available, capture the key pages at ~375, ~768 and ~1440px wide, in
light and dark if both exist, and review the images.

Critique, score 1-5 each, with one line of evidence:
hierarchy, distinctiveness (fits the personality, not generic),
consistency with the design doc, usability of the primary action,
responsive quality, states coverage, copy, accessibility.
Anything under 4 gets a concrete fix.

Audit findings use priorities:
P0 blocks use (broken, inaccessible, data loss), P1 hurts the main
journey, P2 visible quality issue, P3 polish.
P0/P1 are fixed in the same task. P2/P3 that are out of scope become
tasks (`pctl task-new`, `--prioridad` alta for P1, media for P2, baja
for P3) so they survive the session.

## 7. Close

- Update the design doc: new tokens, components (`file:line`), rules.
- Note learnings with `pctl context-note` (e.g. a token the team rejected).
- Mark flows touched as updated; follow `session-close.md`.

## Steering vocabulary

When the user asks for one of these, apply it within the design doc
(or update the doc first, with an ADR if it changes the direction):

| Ask | Meaning |
|---|---|
| bolder | stronger contrast in scale, color and composition; one hero moment |
| quieter | fewer colors, less motion, more whitespace, softer weight |
| distill | remove elements that do not serve the primary action |
| colorize | introduce the palette with meaning to a gray UI |
| typeset | fix pairing, scale, hierarchy, measure, rhythm |
| layout | fix spacing rhythm, grid, alignment, density, focal point |
| animate | add purposeful transitions and interaction feedback |
| delight | small moments of personality that match the voice |
| polish | final pass: states, alignment, consistency, details |
| harden | errors, empty/long/missing content, i18n, overflow, slow network |
| clarify | rewrite copy for clarity and voice |
| adapt | breakpoints and devices on purpose |
| optimize | loading, image weight, layout shift, render cost |

# ProjectControl Changelog

Written by the framework maintainers, shipped with each release.
`update.py --check` shows the entries newer than your installed version.

## v5.2.1 (2026-11-07)

### UI review
- `skills/code-review.md`: diffs that touch styles or markup run
  `pctl ui-scan --changed`; P1 findings block the commit.
- `skills/project-control/SKILL.md` points interface work to `ui-design.md`.

### Fixes
- `pctl ui-scan`: tags split over several lines (JSX/HTML attributes one per
  line) are now checked as a whole (missing alt, clickable div...).

## v5.2.0 (2026-11-07)

### UI design
- New skill `skills/ui-design.md` (inspired by Impeccable): analyze the repo
  (stack, components, data, assets), infer the product archetype and what
  it lacks, ask in rounds with stated defaults, propose 2-3 directions,
  record `architecture/design-system.md` + an ADR, plan as tasks, build with
  tokens avoiding generic-AI patterns, verify with a scored critique and a
  P0-P3 audit whose findings become tasks. Greenfield foundations,
  brownfield consistency audit, overlay and optimistic-UI rules, steering
  vocabulary (bolder, quieter, polish, harden...).
- `prompts/ui-discovery.md`: archetype playbooks (store, SaaS, dashboard,
  portfolio, editorial, local business, docs, mobile) and question bank,
  loaded only for discovery.

### UI scan
- `pctl ui-scan [paths] [--changed] [--apply] [--fail]`: stdlib checks over
  styles and markup: accessibility (P1/P2), generic-AI patterns (P3), colors
  and fonts missing from the design doc (P2), counts of distinct values in
  use. `--apply` creates one task per rule (deduplicated); `--fail` exits 2.
  Silence with `ui-scan-disable <rule>` or `ui-scan-allow:` in the design doc.
- `pctl brief` shows one UI line when the project has style/markup files,
  with the P1 count in uncommitted changes.

### Portable skills
- `skills/ui-design/` (SKILL.md + discovery.md) for any agent with skill
  support and the Claude Code plugin.

### Internal
- `lean.tracked_keys()` shared by `debt-scan` and `ui-scan`.

## v5.1.0 (2026-11-07)

### Lean mode
- New skill `skills/lean.md` (inspired by Ponytail): reuse ladder (codebase,
  stdlib, platform, installed deps) before new code; never cuts validation,
  data-loss handling, security or accessibility; lean output (no reprinted
  code, no recaps); `Skipped/risks` line only when something was skipped.
- `pctl lean [off|lite|full|strict]` (default `lite`, stored in
  `.control/lean.json`); one line in `pctl brief`, nothing when off.
- `pctl reuse <words>`: matching docs, code definitions and installed deps.
- `pctl deps-check`: new dependencies per manifest vs a git ref (package.json,
  composer, requirements, pyproject, Pipfile, Cargo, go.mod, Gemfile); also
  shown in the brief and `pctl git-commit`.
- `pctl debt-scan [--apply]`: `shortcut:` markers in code become backlog tasks.

### Shared utilities
- Lean rule: the 2nd copy of logic becomes one shared utility, after
  comparing behaviour. `pctl dupes [paths] [--changed]` finds repeated
  function names and identical blocks.
- Framework code now uses `scripts/lib/util.py` (removed 10 copies of
  `_today`, 5 git wrappers and other duplicates).

### Review and audit
- `pctl review-context [--base REF]`: docs whose refs hit changed lines,
  callers of touched functions, duplicates, new deps.
- `pctl audit-plan [paths]`: entry points, hotspots, largest files.
- `skills/code-review.md`: review/audit procedure and finding format.

### Update notifier
- The brief announces only published versions (version + summary) and tells
  the agent to ask the user before updating; `pctl update-check --skip`
  silences one version.

### Portable skills
- `skills/project-control/SKILL.md` and `skills/lean/SKILL.md` for any agent
  with skill support; Claude Code plugin + marketplace (`.claude-plugin/`).
- New project adapters (created only if missing): `GEMINI.md`,
  `.github/copilot-instructions.md`.

### Fixes
- `pctl skill-list` printed column names instead of values.
- Branch shown as "(no git)": `git rev-parse --abbrev-ref` lacked `HEAD`.
- Wrong `doc-new` / `roadmap-*-new` syntax in the opencode agent.

## v5.0.0 (2026-10-25)

### Context management
- New `pctl brief`: the whole session-start context in one bounded output
  (~2k tokens) — alerts, local rules, last session handoff, tasks,
  `CONTEXT.md`, roadmap, git. Replaces reading ~10 files at start.
- Session handoff: `pctl session-close ... --next "..." --question "..."`;
  the next brief shows it first.
- `pctl context-note "..." --tipo gotcha`: save learnings immediately to the
  `CONTEXT.md` Inbox, so they survive compactions and abrupt endings.
- `pctl session-current`; `session-start` warns about unclosed sessions.
- `pctl search` rewritten: covers ALL of `.control/`, ranks per file,
  AND between words, filters `--area`, `--estado`, `--fm`, `--regex`,
  `--files`, `--code`, `--generated`.
- `SYSTEM.md`: new sections 16 (context discipline) and 17 (updates and
  `SYSTEM.local.md`); section 11 load order is now just `pctl brief`.
- Integrations: `AGENTS.md`, `CLAUDE.md`, and a Claude Code SessionStart
  hook (`.claude/settings.json`) that injects the brief automatically,
  also after compaction. Created only if missing.

### Updates
- `update.py` rewritten: declarative manifest (`framework.json`), install
  record (`.framework_lock.json`), 3-way merge of user-edited framework
  files, conflicts staged in `.control/.update/` (your file is kept),
  `--check`, `--dry-run`, `--take-upstream`, `--resolved`, `--rollback`,
  self-bootstrap, fresh install with `--target`.
- Upstream is read from `framework.json`, no longer from the project's own
  `origin` remote.
- `pctl update-check` and an alert in `pctl brief` when a new version exists
  (cached, at most one `git ls-remote` per day; `PCTL_NO_UPDATE_CHECK=1`
  disables it).
- Generated indexes (`docs/_index.md`, `roadmaps/_index.md`) are no longer
  overwritten by updates; the skill registry is merged by skill name.

### Fixes
- Migration 5 removes `.control/roadmaps/` from `.gitignore` (v4 ignored
  the user's roadmaps by mistake).
- `pctl migrate` no longer auto-promotes proposed skills (SYSTEM.md §10).
- Windows consoles no longer crash on non-ASCII output.

### Upgrading from v4
The v4 updater pulls from your project's `origin`, so it cannot reach this
release. Run once:
`git clone --depth 1 https://github.com/jvchiappini/ProjectControlSystem.git /tmp/pc`
`python /tmp/pc/.control/scripts/update.py --source /tmp/pc --target .`
Files you never edited are updated; files you edited are kept and the new
version is staged for review.

## v4 (2026-07-14)
- Migration `3->4`: create roadmaps directories.

## v3 (2026-07-14)
- Migration `2->3`: add `.gitignore` entries.

## v2 (2026-07-13)
- Migration `1->2`: create missing templates.

## v1 (2026-07-13)
- Migration `0->1`: ensure standard directories.

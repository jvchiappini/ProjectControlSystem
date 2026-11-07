# ProjectControl Changelog

Written by the framework maintainers, shipped with each release.
`update.py --check` shows the entries newer than your installed version.

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

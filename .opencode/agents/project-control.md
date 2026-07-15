---
description: Primary agent for the ProjectControl system. Handles tasks, sessions, architecture, flows, decisions, technical docs, roadmaps, and self-updates via .control/ markdown files and pctl CLI.
mode: primary
---

You are working on a project that uses the **ProjectControl** system. The
rules in `.control/SYSTEM.md` are loaded automatically at session start
via `instructions` — follow them without exception.

## Session start procedure

1. Read `.control/CONTEXT.md` (agent working memory, survives chat
   compactions).
2. Read `.control/PROJECT.md` and `.control/GOALS.md` in full.
3. Read `.control/CHANGELOG.md` to see what has changed in the framework
   since last session.
4. Run `python .control/scripts/pctl.py status` for a project summary.
5. Check `.control/tasks/IN_PROGRESS.md` for current task.
6. Check `.control/docs/_index.md` for technical documentation index.
7. Check `.control/roadmaps/_index.md` for roadmap phases/initiatives.
8. Check `.control/architecture/_index.md` and `.control/flows/_index.md`
   for domain/flow map.
9. If this is the **first session ever** (no `.control/sessions/S-*.md`),
   follow `.control/prompts/prompt_new_project.md` instead.

## Available tools

### Core (tasks, sessions, context)
- `pctl task-new`, `task-move`, `task-show`, `task-list`
- `pctl session-start`, `session-log`, `session-close`
- `pctl context-show`, `context-write`, `context-check`
- `pctl status`, `reindex`, `validate`, `doc-check-refs`

### Architecture & flows
- `pctl arch-touch`, `arch-list`
- `pctl flow-new`, `flow-show`, `flow-list`, `flow-touch`

### Technical documentation (docs/)
- `pctl doc-new --titulo "..." --categoria <guides|api|database|reference|tutorials> [--tags "..."]`
- `pctl doc-list [--categoria] [--estado]`
- `pctl doc-show <id>`
- `pctl doc-touch <id> <draft|published|outdated|deprecated>`
- Or use the frontend at `http://localhost:8420` → Documentación

### Roadmaps (roadmaps/)
- `pctl roadmap-phase-new --titulo "..." [--objetivo "..."]`
- `pctl roadmap-initiative-new --titulo "..." --phase <id> [--objetivo "..."]`
- `pctl roadmap-milestone-new --titulo "..." --initiative <id>`
- `pctl roadmap-list [--fase|--iniciativa|--hito]`
- `pctl roadmap-show <id>`
- `pctl roadmap-touch <id> <estado>`

### Skills & self-evolution
- `pctl skill-propose`, `skill-promote`, `skill-list`
- New skills/scripts go into `skills/proposed/` or `scripts/lib/proposed/`

### Updates
- `python .control/scripts/update.py` — updates the framework itself
- `--dry-run` to preview, `--force` to skip confirmation
- Check `.control/CHANGELOG.md` after each update for changes

### Frontend (control panel)
Start with: `python .control/frontend/server.py [--port 8420]`
Open `http://localhost:8420` for a full web panel with kanban,
architecture canvas, flows, docs reader, and more.

## Key principles

- **Source of truth**: the filesystem, never conversation memory.
- **pctl for mechanical work**: task state changes, session logs,
  indexing, validation all go through `pctl`.
- **Lazy documentation**: only document the domain you are working on.
- **Zero code in markdown**: use `file:line` references, never paste
  code.
- **Task state machine**: `backlog ↔ in_progress ↔ blocked`,
  `in_progress → done`, no direct `backlog → done`.
- **Flows over domains**: `architecture/` documents modules,
  `flows/` documents end-to-end behavior crossing modules.
- **Context budget**: load indexes first, detail only on demand.
- **Framework updates are additive**: the update script never deletes
  user data (tasks, sessions, decisions, docs, roadmaps, etc.).

## Session close (mandatory)

Run through `.control/skills/session-close.md` checklist:
- `pctl reindex`
- `pctl context-check`
- Update `CONTEXT.md` if needed
- `pctl session-close`
- `pctl validate` for reference drift

---
description: Primary agent for the ProjectControl system. Handles tasks, sessions, architecture, flows, and decisions via .control/ markdown files.
mode: primary
---

You are working on a project that uses the ProjectControl system. The
rules in `.control/SYSTEM.md` are loaded automatically at session start
via `instructions` — follow them without exception.

## Session start procedure

1. Read `.control/CONTEXT.md` (agent working memory, survives chat
   compactions).
2. Read `.control/PROJECT.md` and `.control/GOALS.md` in full.
3. Check `.control/tasks/IN_PROGRESS.md` for what is currently being
   worked on.
4. Run `python .control/scripts/pctl.py status` (or
   `python3 .control/scripts/pctl.py status`) to see the task summary.
5. Check `.control/architecture/_index.md` and
   `.control/flows/_index.md` for the domain/flow map.
6. If this is the first session ever on this project (no `.control/sessions/S-*.md`), follow `.control/prompts/prompt_new_project.md` instead.

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

## Session close (mandatory)

Follow `.control/skills/session-close.md` checklist:
- `pctl reindex`
- `pctl context-check`
- Update `CONTEXT.md` if needed
- `pctl session-close`
- `pctl validate` for reference drift

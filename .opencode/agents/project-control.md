---
description: Primary agent for the ProjectControl system. Handles tasks, sessions, architecture, flows, decisions, technical docs, roadmaps, and self-updates via .control/ markdown files and pctl CLI.
mode: primary
---

You are working on a project that uses the **ProjectControl** system. The
rules in `.control/SYSTEM.md` are loaded automatically at session start
via `instructions` — follow them without exception.

## Session start procedure

1. Run `python .control/scripts/pctl.py brief` — one bounded digest with
   alerts, local rules, the last session's handoff (next steps, open
   questions), tasks, `CONTEXT.md` and git state. Do NOT read `.control/`
   files one by one.
2. Handle its Alerts, then `pctl session-start --agente opencode`.
3. Load anything else only when the user's request needs it
   (`pctl search <words>`, `pctl task-show <id>`, a flow, a domain doc).
4. If the brief says `PROJECT.md` does not exist, this is the first
   session: follow `.control/prompts/prompt_new_project.md`.

During work, save non-obvious learnings immediately:
`pctl context-note "..." --tipo gotcha`.

## Skills in `.control/skills/`

The `.control/skills/` directory contains procedural skill files (markdown)
that tell you exactly how to handle specific situations. Every skill is
registered in `.control/skills/_index.md` with its trigger condition.

When you encounter a situation that matches a skill's trigger
(e.g., creating a task, closing a session, documenting a domain), consult
the corresponding skill file first. The full list with triggers is in
`SYSTEM.md` section 15 (Available skills reference).

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
- `pctl doc-new "<title>" <guides|api|database|reference|tutorials> [--tags "..."]`
- `pctl doc-list [--categoria] [--estado]`
- `pctl doc-show <id>`
- `pctl doc-touch <id> <draft|published|outdated|deprecated>`
- Or use the frontend at `http://localhost:8420` → Documentación

### Roadmaps (roadmaps/)
- `pctl roadmap-phase-new "<name>" [--orden N]`
- `pctl roadmap-initiative-new "<name>" <phase-id>`
- `pctl roadmap-milestone-new "<name>" <initiative-id> <phase-id>`
- `pctl roadmap-list [--fase|--iniciativa|--hito]`
- `pctl roadmap-show <id>`
- `pctl roadmap-touch <id> <estado>`

### Skills & self-evolution
- `pctl skill-propose`, `skill-promote`, `skill-list`
- New skills/scripts go into `skills/proposed/` or `scripts/lib/proposed/`

### Context & search
- `pctl brief` (session start), `pctl context-note "..." --tipo <kind>`
- `pctl search <words> [--area tasks,flows] [--fm] [--files] [--code]`
- `pctl lean [off|lite|full|strict]` (code changes follow `skills/lean.md`)
- UI work (new interface, redesign, critique, audit) follows `skills/ui-design.md`; `pctl ui-scan [--changed] [--apply]`
- `pctl reuse <words>`, `pctl dupes [--changed]`, `pctl deps-check`, `pctl debt-scan [--apply]`
- Review: `pctl review-context [--base main]`; audit: `pctl audit-plan`
- `pctl session-current`, `pctl session-close <sid> "..." --next "..."`

### Updates (only with the user's consent)
- When the brief announces a new version: ask the user whether to update now;
  if not, `pctl update-check --skip`
- `python .control/scripts/update.py --check` — is there a new version, what changed
- `--dry-run` full plan, no args to apply, `--rollback` to undo
- Only files in `.control/framework.json` are touched; user edits are
  merged or kept, never overwritten. Project rules go in `SYSTEM.local.md`.

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
- Consolidate the `CONTEXT.md` Inbox; update `CONTEXT.md` if needed; `pctl context-check`
- `pctl validate` for reference drift
- `pctl session-close <sid> "summary" --tareas ... --next "..." [--question "..."]`

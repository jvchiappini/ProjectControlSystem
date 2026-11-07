---
id: SK-0008
nombre: context-budget
tipo: skill
estado: activa
disparador: "start of any session, and any moment the agent is about to read files for general context"
ubicacion: skills/context-budget.md
creado_por: usuario
version: 2
---

# Skill: context-budget

Trigger: always at session start, and whenever you are about to open
files "to get context". See `SYSTEM.md` sections 11 and 16.

## Session start (code execution available)

1. `python .control/scripts/pctl.py brief` — the whole start-up context in
   one bounded output. Skip it if a brief is already in context (hooks
   inject it in some agents, e.g. Claude Code).
2. Act on its **Alerts** first (unclosed session, update conflicts,
   outdated flows).
3. If the handoff has **Next steps** and the user did not ask for
   something else, propose continuing with the first one.
4. Load NOTHING else until the request is known.

Without code execution: `CONTEXT.md`, `tasks/IN_PROGRESS.md`, and the
`## Handoff` section of the newest closed `sessions/S-*.md`. Nothing more.

## Loading on demand (after the request is known)

| Need | Use | Not |
|---|---|---|
| a task | `pctl task-show <id>` | `tasks/BACKLOG.md` |
| "where is X mentioned?" | `pctl search X` (`--area`, `--fm`, `--files`) | opening directories |
| behavior across modules | `pctl flow-list` -> `pctl flow-show <id>` | all domain docs |
| one module | `architecture/<domain>.md` | every `architecture/*.md` |
| code | the `file:start-end` range from a reference | the whole file |
| a past session detail | `pctl session-summarize <id>` | full session bodies |

## Signs the budget is being violated

- Reading a file "just in case" or for "general context".
- Re-reading a file that is already in context and has not changed.
- Opening more than ~3 `.control/` files before the first useful action.
- Searching by opening files instead of `pctl search` / grep.

## When it IS worth loading more

The user explicitly asks for an overview ("summary of everything", "what's
pending"). Even then, prefer `pctl status`, `pctl task-list`,
`pctl roadmap-list` and the generated indexes over opening files one by one.

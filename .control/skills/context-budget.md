---
id: SK-0008
nombre: context-budget
tipo: skill
estado: activa
disparador: "start of any session in a project with many accumulated domains/tasks"
ubicacion: skills/context-budget.md
creado_por: usuario
version: 1
---

# Skill: context-budget

Trigger: always at session start, more critical the larger the project.

## Load order rule (see `SYSTEM.md` section 6)

Default load order, without exception:

1. `PROJECT.md` + `GOALS.md` in full (short by design — if they grew
   a lot, it is a sign they need pruning, not that they should stop
   being read).
2. `tasks/IN_PROGRESS.md` — an index at one line per task, not the
   full tasks.
3. `architecture/_index.md` — domain map, one line each.
4. NOTHING ELSE yet. Only after the user's request in this turn, load:
   - the specific task file(s) (`pctl task-show <id>`)
   - the architecture `.md` of the relevant domain, if it exists
   - specific code files via `file:line`, never the full file if the
     reference already points to a bounded range

## Signs the budget is being violated

- Loading `tasks/BACKLOG.md` entirely when the user asked about a
  single task — use `pctl task-list --estado backlog` with a filter,
  or `pctl task-show <id>` directly if the ID is already known.
- Opening all `.md` files in `architecture/` "for general context" —
  the index already provides that general context, one line per domain.
- Re-reading old sessions in full — the summary of each session
  (`resumen:` in the frontmatter) usually suffices; only open a full
  session body if the event detail is needed.

## When it IS worth loading more

If the user explicitly asks for an overview ("give me a complete
project summary", "I want to see everything pending"), then it is
justified to traverse more — but even then, prefer the generated
indexes over opening files one by one.

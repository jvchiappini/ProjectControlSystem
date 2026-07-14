---
id: SK-0005
nombre: session-close
tipo: skill
estado: activa
disparador: "the agent is about to finish its work turn or the conversation is closing"
ubicacion: skills/session-close.md
creado_por: usuario
version: 1
---

# Skill: session-close

Trigger: ALWAYS, at the end of each work session, without exception
(see `SYSTEM.md` section 7). Not optional even if the user does not
explicitly ask for it.

## Mandatory checklist

1. If no session was started at the beginning of the turn, start one
   now anyway with `pctl session-start --agente <name>` (better late
   than never, so the log is not lost).
2. Confirm that every task state change in this turn went through
   `pctl task-move` (no manual `estado` edits).
3. Run `pctl reindex` — ensures `BACKLOG.md`, `IN_PROGRESS.md`,
   `DONE.md` and `architecture/_index.md` reflect the actual state.
4. Apply `context-maintenance.md`: if something was learned in this
   session that the next session (or a new chat after compaction) would
   need to know, rewrite `CONTEXT.md` completely (do not append) and
   run `pctl context-check` to confirm it is within the size budget.
5. Run `pctl doc-check-refs` (or `pctl validate`, which includes it) —
   if there are broken `file:line` references due to changes in this
   turn, fix them before closing, do not leave them for the next
   session.
6. Close the session:
   `pctl session-close <sid> "<1-2 line summary>" --tareas T-XXXX,T-YYYY`
7. If something was left half-done that is not yet a formal task (an
   idea, a loose end), do not leave it only in the conversation —
   create it as a task in `backlog` with `task-intake.md` so it is not
   lost.

## What NOT to do

- Do not close a session without `reindex` — it is the most common
  cause of the frontend showing outdated data.
- Do not leave a task in `in_progress` without having done any work
  on it in the session — if no progress was made, consider moving it
  back to `backlog`.

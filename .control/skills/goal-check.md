---
id: SK-0006
nombre: goal-check
tipo: skill
estado: activa
disparador: "start of a large task, or every few sessions, or when a task's scope seems to be drifting"
ubicacion: skills/goal-check.md
creado_por: usuario
version: 1
---

# Skill: goal-check

Trigger: before starting a task with considerable scope, or when the
agent notices the requested work does not obviously align with what
`GOALS.md` says — not on every micro-task, that would be noise.

## Procedure

1. Re-read `GOALS.md` (it is short, should not weigh on context).
2. Ask yourself: does this task advance any of the success criteria
   listed there, or is it reasonable collateral work (technical debt,
   maintenance)? If the answer is not clear, say it explicitly to the
   user instead of proceeding silently — it is not a blocker, it is a
   transparency note: "this is not directly in `GOALS.md`, do you
   confirm you want to prioritize it anyway?"
3. If the project has many sessions and `ROADMAP.md` no longer reflects
   reality (completed phases not marked, new phases not added), point
   it out to the user and offer to update it — but never rewrite
   `ROADMAP.md` without telling them, it is a project-level document
   that the user must be able to trust only changes with their
   awareness.

## What NOT to do

- Do not turn this into a bureaucratic gate on every small task — it
  ruins the flow the system was designed for.
- Do not reinterpret `GOALS.md` creatively to justify any request —
  if it genuinely does not fit, saying so is more useful than forcing
  the justification.

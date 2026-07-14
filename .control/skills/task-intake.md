---
id: SK-0001
nombre: task-intake
tipo: skill
estado: activa
disparador: "user creates a raw todo (bare title, no details) from the frontend or in chat"
ubicacion: skills/task-intake.md
creado_por: usuario
version: 1
---

# Skill: task-intake

Trigger: the user adds a new item to the backlog with only a title
(from the kanban frontend, or by writing it in chat) and it still has
no context, acceptance criteria, or well-defined priority.

## Procedure

1. If the task already exists (created by the user without `pctl`,
   directly in markdown), read it with `pctl task-show <id>`. If it
   does not exist yet, create it with `pctl task-new "<title>"`.
2. Do not invent scope the user did not give. If critical information
   is missing to write reasonable acceptance criteria, ask — do not
   assume.
3. Enrich the file body (direct `.md` edit, this does not go through
   `pctl`):
   - `## Contexto`: 2-4 lines of why this task exists and which domain
     it touches.
   - `## Criterios de aceptación`: concrete, verifiable checkboxes.
   - If you detect dependencies with another existing task, add them to
     the `depende_de` field in the frontmatter (manual field edit —
     there is no `pctl` command for this yet; see `skill-authoring.md`
     if it repeats often enough to warrant automation).
4. Adjust `--prioridad` and `--tipo` if the default is not correct,
   using direct frontmatter edit since it is not a state change.
5. Do not change the task state at this step. `task-intake` only
   enriches; promotion to `in_progress` is the responsibility of
   `task-promotion.md`.

## What NOT to do

- Do not document architecture at this step (that is
  `architecture-update.md`, and only when work starts on the task, not
  when it is created).
- Do not paste example code inside the context — if existing code
  needs referencing, use `file:line`.

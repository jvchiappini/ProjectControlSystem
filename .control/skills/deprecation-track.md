# Skill: deprecation-track

Trigger: something is marked as obsolete (function, endpoint, module),
or an ADR is created with non-empty `reemplaza`.

## Procedure

1. **Search documentation references** — `pctl search "<component name>"`
   across all `.control/` to find mentions in tasks, flows, decisions,
   architecture.
2. **Update flows** — if any flow mentions the component, mark it as
   `desactualizado` with `pctl flow-touch <id> desactualizado`.
3. **Mark in CONTEXT.md** — add a line in the `## Cambios recientes`
   section indicating what was deprecated and what replaces it.
4. **Check open tasks** — if there are `in_progress` or `backlog` tasks
   referencing the component, add a note in their body.
5. **Complete ADR** — ensure the ADR documenting the replacement has in
   `## Consecuencias` a list of everything that needs to be migrated.

## Output

Checklist in the ADR body with verifiable items. Each item is a file
or flow that was left updated.

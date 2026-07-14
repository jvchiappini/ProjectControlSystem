# Skill: refactor-plan

Trigger: task type `refactor`, or the agent detects 2+ occurrences of
the same manual pattern.

## Procedure

1. **Map callers** — search all references to the code being
   refactored (`grep -r` or IDE search). List affected files.
2. **Enumerate risks** — what could break. For each risk, create a
   checkbox in `## Criterios de aceptacion`.
3. **Estimate diff** — how many files it touches, how much of each
   (rough estimate: small <5 files, medium <15, large >=15).
4. **Check flows** — if the code crosses domains, review
   `flows/_index.md`. If a flow covering it exists, read it. If not,
   create it with `pctl flow-new`.
5. **Plan order** — numbered steps in `## Contexto` of the task so
   the refactor is revertible step by step.

## Output

The task must have before coding:
- `## Contexto`: step order, files to touch
- `## Criterios de aceptacion`: one checkbox per mitigated risk
- Flow created or updated if it crosses domains

## What NOT to do

- Do not refactor and add features in the same commit.
- Do not change formatting/whitespace together with logic — do it in a
  separate commit with type `style`.

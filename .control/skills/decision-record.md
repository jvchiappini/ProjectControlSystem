---
id: SK-0004
nombre: decision-record
tipo: skill
estado: activa
disparador: "a design decision was made with discarded alternatives, or one that will be hard to revert"
ubicacion: skills/decision-record.md
creado_por: usuario
version: 1
---

# Skill: decision-record

Trigger: a technical approach was chosen among several possibilities
(library, pattern, data structure, protocol, etc), especially if it
is costly to revert or if someone could reasonably ask "why was it
done this way and not another?".

Do not create an ADR for trivial or easily reversible decisions
(variable name, order of two independent steps). The signal is: if in
3 months someone will ask "why?", it warrants an ADR.

## Procedure

1. Determine the next ID: check the last `D-XXXX` in `decisions/`.
   There is no dedicated `pctl` command yet — if this becomes frequent,
   propose automating it via `skill-authoring.md`.
2. Create `decisions/D-XXXX.md` with frontmatter:
   ```
   id, titulo, fecha, estado (aceptada by default unless discussed
   first), reemplaza, version_schema
   ```
3. Body with exactly these three sections:
   - `## Contexto` — what problem forced the decision, in a few lines.
   - `## Decisión` — what was chosen, in a clear statement.
   - `## Consecuencias` — what is gained, what is lost, what remains
     to be reviewed later.
4. Link the ADR from the architecture `.md` of the affected domain,
   in the "Decisiones relevantes" section — only the ID and title, do
   not duplicate the content there.
5. If this decision replaces a previous one: mark the new one with
   `reemplaza: [D-000X]` and change the old one's `estado` to
   `reemplazada` (edit its frontmatter).

## What NOT to do

- Do not include example code from the evaluated alternatives — describe
  the trade-off in prose.
- Do not create an ADR per commit; group related decisions from the
  same session into a single document if it makes sense.

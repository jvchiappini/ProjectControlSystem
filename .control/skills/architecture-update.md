---
id: SK-0003
nombre: architecture-update
tipo: skill
estado: activa
disparador: "a design/structure change was made in a domain and needs to be reflected in documentation"
ubicacion: skills/architecture-update.md
creado_por: usuario
version: 1
---

# Skill: architecture-update

Trigger: upon finishing (or during) work on a task that touched a
domain's design — not every time a line of code is written, only when
something changes that another person/agent would need to know to
understand the system.

## Prior rule (see `domain-scoping.md`)

Before writing, confirm the target domain is exactly one. If the task
touched two domains at once, update each `.md` separately, each with
its own scope — do not mix both in a single file.

## Procedure

1. If `architecture/<domain>.md` does not exist yet:
   `pctl arch-touch <domain> --estado parcial --crear-archivo`. This
   creates the file with the standard template and updates the index.
2. Edit the file directly (no `pctl` command for content, only for
   index registration). Always keep the fixed sections:
   `## Proposito`, `## Componentes clave`, `## Diagrama`,
   `## Decisiones relevantes`, `## Estado de documentacion`.
3. In "Componentes clave", each line is
   `Name — what it does, where it lives: file:line-line`. Never paste
   the actual code (see `SYSTEM.md` section 3).
4. If the change warrants a new or modified diagram, the `.mmd` goes in
   `diagrams/<domain>.mmd` and is referenced from the `## Diagrama`
   section — the diagram lives separately, never embedded as a code
   block inside the `.md`.
5. If the decision behind the change is non-trivial (there were
   discarded alternatives, trade-offs), do not explain it at length
   here — create an ADR with `decision-record.md` and just link it in
   "Decisiones relevantes".
6. When finished, update the actual state with
   `pctl arch-touch <domain> --estado <parcial|documentado>` (this
   also updates the date in the index).

## What NOT to do

- Do not touch `architecture/_index.md` by hand — it is generated.
- Do not document domains that were not part of the current task, even
  if you saw them while exploring the code. For those, at most
  `pctl arch-touch <seen_domain> --estado sin_documentar` (without
  `--crear-archivo`), just to register that it exists.

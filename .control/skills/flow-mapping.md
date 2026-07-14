---
id: SK-0011
nombre: flow-mapping
tipo: skill
estado: activa
disparador: "a behavior/interaction involving more than one domain is implemented or modified, or the user asks 'what happens when...'"
ubicacion: skills/flow-mapping.md
creado_por: usuario
version: 1
---

# Skill: flow-mapping

Trigger: any observable end-to-end behavior that involves more than
one domain — typical in video games (input → game logic → animation →
audio) but applies to any system with module interactions (checkout
touching cart + payments + notifications).

## Why it exists (difference from `architecture-update.md`)

`architecture/<domain>.md` documents a module from the inside. A
**flow** documents an end-to-end behavior, regardless of how many
modules it touches. Without this, understanding "what happens when the
player presses attack" forces reading full input, combat, and
animation domains — exactly the token cost this system exists to avoid.

## Before touching code: check if a flow already exists

1. Read `flows/_index.md` (one line per flow, lightweight). If the
   behavior to be touched already has a documented flow, open ONLY
   that file (`pctl flow-show <id>`) — it is the fastest way to know
   exactly which file and which line to touch, without reading the
   rest of the code.
2. If the flow exists but its state is `desactualizado`, correct it as
   part of this same task before trusting its steps.

## Creating a new flow

Triggered when: a new cross-domain interaction is implemented, or the
agent notices it explained "what happens when X" more than once
without a flow to back it up.

1. `pctl flow-new "<descriptive name>" --dominios <a,b,c> --disparador "<what triggers it>"`
2. Complete `## Pasos` with a numbered list, each step as a short
   statement + exact `file:line-line` reference. Never paste the
   code — the value of the flow is the path, not a copy.
3. If the flow has a clear temporal sequence (A calls B which triggers
   C), add a Mermaid sequence diagram in `diagrams/flows/<id>.mmd` and
   reference it in `## Diagrama`.
4. Mark `estado: vigente` with `pctl flow-touch <id> vigente` once
   the steps are verified correct (it starts as `borrador`).
5. Do NOT list the domains as if they were full architecture
   documentation — in `## Dominios relacionados` only the names go,
   the detail of each domain still lives in its own
   `architecture/<domain>.md`.

## Maintenance

- If a refactor changes files referenced by a vigente flow, update the
  steps in the same session (part of `doc-drift-check.md`) or, if
  there is no time, mark
  `pctl flow-touch <id> desactualizado` so it is visible in
  `pctl status` and nobody trusts broken steps.
- A flow with more than ~8-10 steps should probably be split into two
  more specific flows (e.g., "melee attack" and "ranged attack" instead
  of a single "combat system").

## What NOT to do

- Do not create a flow for something that lives entirely in a single
  domain — that is already covered by `architecture/<domain>.md`.
- Do not duplicate domain architecture content inside the flow; the
  flow is the execution path, not a second copy of the design.

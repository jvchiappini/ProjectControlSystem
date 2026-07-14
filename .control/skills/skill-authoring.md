---
id: SK-0007
nombre: skill-authoring
tipo: skill
estado: activa
disparador: "the agent detects a manual pattern repeated 2 or more times that could be automated"
ubicacion: skills/skill-authoring.md
creado_por: usuario
version: 1
---

# Skill: skill-authoring (meta-skill)

Trigger: the agent notices it did the same thing manually two or more
times in the project (e.g., always calculating the next ADR ID by hand,
always reformatting the same kind of data before analysis). This is
the only skill that creates other skills or scripts — it never skips
the proposal flow.

## Hard rule (see `SYSTEM.md` section 5)

The agent NEVER moves something directly into `active/` (skills) or
`lib/` (scripts). Everything is born in `proposed/`. Promotion to
`active/` requires `pctl skill-promote SK-XXXX`, executed only with
explicit user confirmation in the current turn.

## Procedure for proposing a new script

1. Write the script in `scripts/lib/proposed/<name>.py`. It must be
   self-contained or only import from `scripts/lib/` (do not depend on
   `proposed/` of another unpromoted script).
2. Register the proposal:
   ```
   pctl skill-propose "<name>" --tipo script \
     --disparador "<when it would be used>" \
     --ubicacion "scripts/lib/proposed/<name>.py"
   ```
3. Explain to the user, in the same turn, what the script does and why
   it is worth automating. Ask if they want to promote it.
4. If the user confirms: `pctl skill-promote SK-XXXX`, and move the
   file from `proposed/` to `lib/` (this is a manual filesystem edit,
   there is no `pctl` command for moving the physical file yet — an
   ironic candidate for its own future automation).
5. If the user does not confirm or does not respond: the proposal stays
   in `proposed/` unused. It is not deleted — it may be useful later or
   for another agent working on the project.

## Procedure for proposing a skill (procedural markdown)

Same as above but the file goes in `skills/proposed/<name>.md` with
the same frontmatter as other skills (`estado: propuesta`).

## What NOT to do

- Do not propose a skill for something that happened only once.
- Do not propose scripts that duplicate something `pctl` already does.
- Do not write code with destructive effects (deleting files,
  overwriting without backup) without explicitly flagging it in the
  proposal to the user.

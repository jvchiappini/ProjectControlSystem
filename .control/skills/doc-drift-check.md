---
id: SK-0010
nombre: doc-drift-check
tipo: skill
estado: activa
disparador: "session close, or after refactors that move/renumber code lines"
ubicacion: skills/doc-drift-check.md
creado_por: usuario
version: 1
---

# Skill: doc-drift-check

Trigger: part of the `session-close.md` checklist, and also
immediately after any refactor that you know moved code lines in a
file referenced from `architecture/` or `tasks/`.

## Why it exists

The system avoids pasting code in markdown and instead references
`file:line`. The cost of that decision is that references become
outdated if the code moves. This skill is the counterweight: without
it, the referenced documentation silently rots.

## Procedure

1. Run `pctl validate` (includes reference checking). It reports
   references to files that no longer exist or lines out of range.
2. This catches obvious breaks (file deleted/moved, file truncated)
   but does NOT catch that line 42 still exists but now has different
   code — that requires agent judgment: if a file referenced from
   `architecture/` was touched in this session, manually review if
   the reference still points to what it claims.
3. Fix broken references before closing the session, do not postpone
   them — they accumulate fast in large projects.
4. If the same file is refactored very often and this becomes constant
   friction, it is a good candidate to propose via `skill-authoring.md`
   a script that automatically recalculates line ranges using text
   anchors instead of fixed numbers.

## What NOT to do

- Do not ignore `pctl validate` errors "for later" — if they
  accumulate, nobody ever fixes them and the documentation ceases to
  be reliable, which is exactly what this system aims to prevent.

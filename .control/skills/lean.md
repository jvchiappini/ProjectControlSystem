---
id: SK-0022
nombre: lean
tipo: skill
estado: activa
disparador: "before writing or changing code, when lean mode is not off"
ubicacion: skills/lean.md
creado_por: usuario
version: 1
---

# Skill: lean

Goal: the smallest change that fully solves the task. Every line of code,
every dependency and every token of output must earn its place. Lean about
the solution, never about understanding: read the code the change touches
and trace its flow first (`pctl search`, the flow/domain `file:line` refs).

## Ladder (stop at the first rung that holds)

1. Does it need to exist? Check the task's acceptance criteria. Not asked
   for = not built.
2. Already in this codebase? `pctl reuse <words>` lists matching docs,
   code definitions and installed dependencies as `file:line`. Reuse or
   extend; never write a twin.
3. Standard library?
4. Native platform feature (HTML input types, DB constraints, framework
   built-ins)?
5. Dependency already installed? (also shown by `pctl reuse`)
6. One line?
7. Only then: the minimum new code that works.

## Never cut

Validation at trust boundaries, handling that prevents data loss, security,
accessibility. Logic with a branch, loop, parser, money or security gets one
small test (see `test-gap.md`).

## Levels (`pctl lean`)

- `lite` (default): the ladder and "never cut". A new dependency needs a
  one-line reason given to the user (`pctl deps-check` lists them; the
  brief and `git-commit` show them too).
- `full`: lite + no speculative options, config, abstractions or files
  nobody asked for; edit existing files before creating new ones.
- `strict`: full + every new file, abstraction or dependency is justified
  in one line; a new dependency also needs an ADR (`decision-record.md`).

## Output (tokens are cost)

- Do not reprint code that is already in a file or a diff; point to
  `file:line`.
- Use edits, not full-file rewrites, when an edit is possible.
- No preamble, no restating the request, no recap of what the diff shows.
- Answer the question asked; no unrequested alternatives or tutorials.

## Close of a change

Only if something was skipped, deferred or not verified, say it in one
line: `Skipped/risks: ...`. If the work belongs to a task, append the same
line to the task body under `## Skipped / risks` so the next session sees
it. If nothing was skipped, write nothing.

A deliberate shortcut left in code is marked `shortcut: <what and why>`
in a comment. When you add or remove one, run `pctl debt-scan --apply`:
new markers become backlog tasks, removed ones are reported for closing.
Marker word: `debt_marker` in `.control/lean.json`.

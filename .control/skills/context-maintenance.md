---
id: SK-0012
nombre: context-maintenance
tipo: skill
estado: activa
disparador: "start of every session (reading) and close of every relevant session (writing)"
ubicacion: skills/context-maintenance.md
creado_por: usuario
version: 1
---

# Skill: context-maintenance

Trigger: ALWAYS at session start (reading) and when closing any session
where something non-obvious was learned about the project (writing).
It exists because the chat gets compacted or a new one opens, and
`CONTEXT.md` is the only thing designed to survive that without forcing
a re-read of all past sessions.

## Difference from other files (do not confuse)

- `PROJECT.md` / `GOALS.md`: identity and vision, written by the user,
  rarely changes.
- `sessions/*.md`: append-only log, one file per session, never
  rewritten, grows indefinitely.
- `CONTEXT.md`: agent working memory, a SINGLE file that is
  **rewritten entirely** each time (not appended). It is the first
  thing read after `SYSTEM.md`.

## At session start

1. Read `CONTEXT.md` in full (short by design). If it does not exist
   yet, that is normal for a new or just-started project — create one
   the first time something worth remembering is learned.
2. Treat its content as a starting point, not absolute truth — if
   something there contradicts what is now observed in the code, flag
   it and correct it at session close.

## During the session (do not wait for the close)

The moment you learn something non-obvious that would be expensive to
rediscover (a trap, a hidden dependency, a convention, a user preference),
save it:

`pctl context-note "<one line, with file:line if relevant>" --tipo gotcha`

Kinds: `fact`, `gotcha`, `convention`, `todo`, `decision`. It is appended
to the `Inbox` section of `CONTEXT.md` and logged in the open session, so
it survives a chat compaction or a session that ends abruptly.

## At session close (part of `session-close.md`)

0. Consolidate the Inbox: move each note into its section (or its
   permanent place: `architecture/`, `flows/`, `decisions/`), drop the
   ones no longer true, and leave the Inbox empty.
1. Ask yourself: did I learn anything in this session that the next
   session (or a new chat, or the same agent without memory of this
   conversation) would need to know and that is NOT already in
   `PROJECT.md`, `architecture/` or `flows/`? If the answer is no,
   no need to touch `CONTEXT.md`.
2. If yes: rewrite the entire file (do not append) with
   `pctl context-write --file <tmp>` (best to generate the content in
   a temporary file and pass it with `--file` to avoid shell escaping
   issues). Keep the fixed sections from the template.
3. Run `pctl context-check`. If it warns about excessive length,
   PROMOTE what is already stable and confirmed to its permanent place
   (`PROJECT.md` if it is project identity,
   `architecture/<domain>.md` if it belongs to a specific module,
   `roadmaps/` if it belongs to roadmap context, `decisions/` if it
   is a decision with trade-offs) and prune `CONTEXT.md` to what
   remains genuine working memory.
4. Update the "Last relevant session" section with the session ID and
   one line, not the full log content.

## What NOT to do

- Do not turn this into a second `sessions/` — if it starts growing
  without limit, it means you are appending instead of rewriting, or
  not pruning what was already promoted elsewhere.
- Do not duplicate content that already lives in `PROJECT.md`,
  `architecture/` or `flows/` — `CONTEXT.md` is for what does not yet
  have a formal place or is too ephemeral to deserve one.

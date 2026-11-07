# Skill: code-review

Trigger: before `git-commit --yes`, or when the user asks for an
explicit review or audit.

## Procedure (review of a change)

1. `pctl review-context [--base main]` — the reading list beyond the
   diff: docs whose `file:line` refs hit changed lines (`*`), callers of
   touched functions in other files, duplicates, new dependencies. Read
   those ranges; do not explore further unless they point somewhere.
2. Run the checklist below on the diff.
3. New copies of existing logic (`pctl dupes --changed`) are shared
   instead (see `lean.md`, "Shared utilities").

## Checklist

1. **No secrets** — check that there are no hardcoded tokens,
   passwords, or keys (`.gitignore`, `.env`, `.env.*` should be in
   `.gitignore`).
2. **No dead code** — unused imports, assigned-but-unread variables,
   uncalled functions.
3. **Errors handled** — try/except with no silent `pass`, specific
   exceptions not generic `Exception`.
4. **Follows project conventions** — naming, folder structure, patterns
   from neighboring code.
5. **No out-of-scope changes** — the diff should touch only what is
   needed for the task. If formatting or accidental refactors happened,
   separate them.
6. **Logs without sensitive data** — do not log full request bodies,
   tokens, passwords.
7. **Documentation references updated** — if a file was moved or
   renamed, update `file:line` references in `.control/`.
8. **New dependencies justified** — `pctl deps-check` lists them; each
   needs a reason (and an ADR in lean `strict`). See `skills/lean.md`.
9. **No duplicated logic** — callers use the shared utility, not a copy.
10. **UI changes checked** — if the diff touches styles or markup,
   `pctl ui-scan --changed`: P1 findings block the commit; the rest
   follow `ui-design.md` phase 6.
11. **Commit message in English** — the commit message must be 100% in
   English, regardless of the language used in the user's conversation.

## Whole-repo audit

`pctl audit-plan [paths]` gives the order (entry points, hotspots,
largest files, duplication). Apply the checklist file by file in that
order. Findings too big to fix now become tasks (`pctl task-new`).

## Output

One bullet per finding, most severe first:
`file:line — what goes wrong — fix — cost if skipped`.
List them BEFORE allowing the commit. No findings: "ok".

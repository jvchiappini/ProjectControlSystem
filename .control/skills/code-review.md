# Skill: code-review

Trigger: before `git-commit --yes`, or when the user asks for an
explicit review.

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
8. **Commit message in English** — the commit message must be 100% in
   English, regardless of the language used in the user's conversation.

## Output

If issues are found, list them as bullets BEFORE allowing the commit.
If no issues are found, minimal output: "ok".

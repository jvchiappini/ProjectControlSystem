# Skill: test-gap

Trigger: `pctl task-move <id> done` (or its frontend equivalent)
without the task being type `docs` or `chore`.

## Procedure

1. **Verify task type** — if it is `docs` or `chore`, skip the check.
2. **Look for existing tests** — check if there are test files for the
   same files the task touched (convention: `test_*.py`, `*.test.ts`,
   `*.spec.ts`, `__tests__/`, etc).
3. **If tests exist** — verify that at least one new test covers the
   change. `git diff --stat` helps see if test files were touched.
4. **If no tests exist** — ask the user before allowing `task-move done`:
   > "This task has no tests. Create a testing subtask in backlog or
   > proceed without tests?"
5. **If the user opts for tests** — create a `chore` task in backlog
   with title "Tests for [original task title]" and `depende_de`
   pointing to the original task.

## Output

- If tests exist: permission to move to `done`.
- If no tests and user agrees: testing task created in backlog.
- If no tests and user does not agree: move is still allowed but it is
  logged in the session: "T-XXXX moved to done without tests".

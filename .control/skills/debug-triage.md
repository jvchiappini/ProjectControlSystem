# Skill: debug-triage

Trigger: user reports a bug without a clear root cause, or asks for
debugging help.

## Procedure

1. **Create bug task** with `pctl task-intake "<report>"` — this parses
   the raw text and suggests type/priority/domain.
2. **Reproduce the bug** — ask for concrete steps from the user if
   they did not provide them.
3. **Isolate variables** — identify if it is environmental (OS,
   browser, specific data) or universal.
4. **Check recent changes** — `git log --oneline -10` to see what was
   touched before the bug appeared.
5. **Document findings** — add to the task body in `## Notas del agente`
   with `file:line` references to the suspicious lines.
6. **If it crosses domains** — check `flows/_index.md` for a documented
   flow covering the affected behavior.

## Output

The task must end up with:
- Clear context of the problem
- At least one root cause hypothesis
- References to the involved code lines
- If the cause could not be determined, document what was tried and
  what is missing

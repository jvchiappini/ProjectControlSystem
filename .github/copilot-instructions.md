<!-- generated from AGENTS.md by `update.py --build-manifest` -->

# Agent instructions

This project uses **ProjectControl** (`.control/`). Rules: `.control/SYSTEM.md` (mandatory).

Session start - one command, nothing else:

    python .control/scripts/pctl.py brief

It prints the handoff from the last session, tasks in progress, working
memory (`CONTEXT.md`), alerts and local rules within ~2k tokens. Do not
read `.control/` files one by one; load more only when the task needs it
(`pctl search <words>`, `pctl task-show <id>`).

During work: save non-obvious learnings immediately with
`pctl context-note "..." --tipo gotcha|convention|fact|todo|decision`.

Session end: follow `.control/skills/session-close.md`
(`pctl session-close <sid> "summary" --next "..."`).

Project-specific rules go in `.control/SYSTEM.local.md`, never in
`SYSTEM.md` (framework updates replace it).

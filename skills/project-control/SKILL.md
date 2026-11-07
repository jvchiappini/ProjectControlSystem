---
name: project-control
description: Persistent project memory and control for coding agents (ProjectControl). Use when the repository has a .control/ directory, at session start or end in such a repo, or when the user wants tasks, sessions, handoffs, architecture/flow docs or decisions that survive across chats, or asks to install, set up or update ProjectControl.
---

# ProjectControl

Markdown in `.control/` is the project's source of truth; `pctl` does the
mechanical work. Load as little as possible: one brief, then only what the
task needs.

## Repo has `.control/`

1. Session start: `python .control/scripts/pctl.py brief` (skip it if a
   "ProjectControl brief" is already in context). It holds the last
   handoff, tasks, working memory, alerts and local rules.
2. Rules: `.control/SYSTEM.md` (mandatory). Its section 15 maps each
   situation to a procedure in `.control/skills/*.md`; open one only when
   its trigger happens.
3. While the brief shows "Lean mode", code changes follow
   `.control/skills/lean.md`.
4. Interface work (new UI, redesign, critique, audit) follows
   `.control/skills/ui-design.md`; `pctl ui-scan --changed` checks it.
5. Save learnings the moment they happen:
   `pctl context-note "..." --tipo gotcha|convention|fact|todo|decision`.
6. Session end: `.control/skills/session-close.md` (leave a handoff with
   `--next`).
7. If the brief announces a ProjectControl update, ask the user. Only with
   their consent: `python .control/scripts/update.py` (`--check` previews,
   `pctl update-check --skip` stops the reminder for that version).

## Repo without `.control/`

Install only if the user wants it. From the project root (Python 3.8+, git):

    git clone --depth 1 https://github.com/jvchiappini/ProjectControlSystem.git <tmp>
    python <tmp>/.control/scripts/update.py --source <tmp> --target .

Then follow `.control/prompts/prompt_new_project.md` to set it up.

## No code execution

Read `.control/CONTEXT.md`, `.control/tasks/IN_PROGRESS.md` and the
`## Handoff` of the newest `.control/sessions/S-*.md`. Edit markdown by hand
following the frontmatter in `.control/scripts/lib/schema.md`.

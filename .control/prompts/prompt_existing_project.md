# Initial prompt — existing project

Use this prompt when starting a session on a project that ALREADY has
`.control/` initialized (i.e., `.control/PROJECT.md` already exists).

---

This project already has a control system in `.control/`. Before doing
anything else:

1. Read `.control/SYSTEM.md` in full — these are the mandatory rules.
2. Read `.control/CONTEXT.md` if it exists — it is the working memory
   that the agent has been building across previous sessions. It is
   faster and more reliable than re-reading old sessions.
3. Read `.control/PROJECT.md` and `.control/GOALS.md` in full.
4. Run `python .control/scripts/pctl.py status` to see the task summary
   and any outdated flows (or read `.control/tasks/IN_PROGRESS.md` if
   no code execution is available).
5. Read `.control/architecture/_index.md` (map only),
   `.control/roadmaps/_index.md` (roadmap overview),
   `.control/docs/_index.md` (documentation panel), and
   `.control/flows/_index.md` (map only) — do not open each domain or
   flow yet.
6. If the project uses opencode and `opencode.json` does not exist at
   the root, suggest creating it with
   `instructions: [".control/SYSTEM.md"]` and
   `default_agent: "project-control"`, along with
   `.opencode/agents/project-control.md` (the agent prompt for the
   ProjectControl workflow).

With that, summarize in 3-5 lines for the user: where the project
stands, what's in progress, and what seems most urgent. Then ask or
confirm what to work on next — do not assume.

When the user indicates which domain/topic they will work on:

- If the behavior to touch crosses more than one domain (input->logic,
  request->response, event->effect, etc.), check
  `.control/flows/_index.md` first — if a flow already exists, that
  is the entry point, not the full domains.
- Open ONLY the architecture file for that domain
  (`.control/architecture/<domain>.md`) if it exists. If it does not
  exist, do not create it yet — create it only if the work ends up
  generating something worth documenting (see `skills/domain-scoping.md`).
- Open ONLY the tasks relevant to that domain, not the entire backlog.

At the end of the session, follow the checklist in
`.control/skills/session-close.md` without exception — including
rewriting `CONTEXT.md` if applicable.

# Initial prompt — new project

Use this prompt when `.control/PROJECT.md` does NOT exist yet (the
project has no control system initialized).

---

This project does not have `.control/` initialized yet. Before writing
any code or documentation:

1. Conduct a brief interview with the user (max 5-6 questions, not a
   long questionnaire):
   - What is the project goal in one sentence?
   - What kind of project is it? (web app, API, library, mobile, etc)
   - Main technical stack, if already decided?
   - Are there important constraints? (time, budget, compatibility)
   - Is it a simple project or do you expect it to grow significantly
     (monorepo, multiple domains)? This determines whether task IDs
     are simple (`T-0001`) or prefixed (`T-PROD-0001`).

2. With those answers, generate the minimal scaffolding:
   - `.control/SYSTEM.md` (copy as-is, it is fixed)
   - `.control/PROJECT.md` with what the user answered
   - `.control/GOALS.md` with the objective and 2-3 success criteria
   - `.control/ROADMAP.md` with very high-level phases (no individual
     tasks yet — 3 to 5 phases max)
   - `.control/CONTEXT.md` (copy the template; it will fill in as the
     agent learns non-obvious things while working)
   - `.control/architecture/_index.md` (table header only, no domains
     yet — they fill in as work is done)
   - `.control/flows/_index.md` (table header only, no flows yet —
     they are created when a cross-domain behavior appears)
   - Folder structure: `tasks/`, `architecture/`, `flows/`,
     `diagrams/`, `sessions/`, `decisions/`, `skills/`, `scripts/`
   - If the user works with opencode: create `opencode.json` at the
     project root with `instructions: [".control/SYSTEM.md"]` and
     `default_agent: "project-control"`, and create
     `.opencode/agents/project-control.md` (the agent prompt that
     teaches the workflow). See this repo's `opencode.json` and
     `.opencode/agents/` for reference.

3. Do NOT create domain documentation or flows that do not exist yet.
   Do NOT create tasks until the user asks for concrete work.

4. Show the user a summary of what was created and wait for
   confirmation before starting the first real task.

From this point on, the project uses
`.control/prompts/prompt_existing_project.md` for every future session.

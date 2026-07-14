# Skill: onboarding

Trigger: the project has no previous sessions (`sessions/S-*.md` does
not exist), indicating this is the first time an agent works here.

## Procedure

1. **Load SYSTEM.md** — always, it is mandatory.
2. **Check PROJECT.md** — if it does not exist, create it from the
   `PROJECT.md.template` with basic data (project name from repo/dir
   name, detected stack).
3. **Map initial domains** — review the project's folder structure
   (`src/`, `app/`, `api/`, `packages/`, etc) and suggest domains with
   `pctl arch-touch <domain> --estado sin_documentar` for each
   significant root folder.
4. **Run reindex** — `pctl reindex` so indexes reflect the initial
   state.
5. **Create first flow if applicable** — if the project has a clear
   end-to-end behavior (e.g., "request -> response" in an API, or
   "input -> render" in a UI), create an initial flow with
   `pctl flow-new`.
6. **Start CONTEXT.md** — write initial context with what was learned
   during onboarding (stack, structure, identified domains).

## Output

Project ready to work: PROJECT.md exists, domains mapped, CONTEXT.md
written, first flow created if applicable.

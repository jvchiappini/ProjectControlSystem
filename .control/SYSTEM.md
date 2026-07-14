# SYSTEM.md — mandatory project rules

This file is loaded ALWAYS, in every session, by every agent (Claude,
GPT, Cursor, Copilot, a human reading manually, etc). It is the
invariant contract of the project. Never ignore it, even if the user
does not mention it explicitly.

## 0. Source of truth

The filesystem inside `.control/` is the ONLY source of truth for the
project state. No agent should rely on its own conversation memory for
knowing what exists, what is pending, or what was decided — always
re-read `.control/` at the start of a session.

## 1. Control tool (`pctl`)

If the environment has code execution (bash/python available):

- EVERY operation on tasks, sessions, and indexes goes through
  `python .control/scripts/pctl.py <command>`. See `pctl.py --help`.
- The files `tasks/BACKLOG.md`, `tasks/IN_PROGRESS.md`, `tasks/DONE.md`
  and `architecture/_index.md` are **generated**. Never edit them by hand.
  Regenerate with `pctl reindex`.
- The only things edited directly with a text editor are:
  - the narrative body of a task file (`tasks/**/T-XXXX.md`)
  - `PROJECT.md`, `GOALS.md`, `ROADMAP.md`
  - `architecture/<domain>.md` (only the domain being touched)
  - `decisions/D-XXXX.md`

If the environment has NO code execution (chat-only agent), edit the
markdown directly, respecting the exact frontmatter schema defined in
`scripts/lib/schema.md`, so `pctl` can still read it afterward without
breaking.

## 2. Lazy documentation (mandatory rule)

- The agent documents **only** the domain related to the current task.
  Never create or expand documentation for domains that were not
  requested, even if you discover them while exploring the code.
- If a new undocumented domain appears while exploring the repo, the
  agent ONLY adds a row to `architecture/_index.md` (via
  `pctl arch touch <domain> --estado sin_documentar`). Do not write
  content there.
- Before documenting, the agent must be clear about a single target
  domain. If the task is ambiguous between two domains, ask the user
  instead of documenting both (see skill `domain-scoping.md`).

## 3. Zero code inside markdown

- No file inside `.control/` contains real code blocks (functions,
  classes, executable snippets copied from the project).
- All code references use the form `path/file:line` or
  `path/file:start_line-end_line`. Correct example:
  "Stock validation lives in `src/products/stock.py:42-58`."
  Forbidden example: pasting those lines inside the `.md`.
- Allowed exceptions: Mermaid diagrams (`.mmd`), and short shell
  commands for `pctl` usage as instruction examples (not business
  logic).

## 4. Task state machine

Valid transitions only:

```
backlog <-> in_progress <-> blocked
in_progress -> done
in_progress -> backlog
done -> in_progress   (reopen; pctl logs reason and date automatically)
```

`backlog -> done` directly is PROHIBITED — must always go through
`in_progress`, even if just for a moment, to avoid losing the record
that something was done. `in_progress -> blocked` requires reason
(`--reason "..."`). `in_progress -> done` requires all "Acceptance
criteria" checkboxes to be checked, unless `--force "reason"` is used
(it gets logged). Every state change generates a line in the active
session log — no silent state changes.

### 4.1 Task dependencies

If a task has `depende_de` entries, moving it to `in_progress` requires
all listed tasks to be in `done` state first (unless `--force` is used).
This prevents work from starting on tasks whose prerequisites are not
completed. See skill `task-promotion.md`.

## 5. Flows (mandatory for behaviors that cross domains)

A domain (`architecture/<domain>.md`) documents a module. A **flow**
(`flows/F-XXXX.md`) documents an observable end-to-end behavior that
crosses domains. This applies to ANY system with module interaction,
not just games: the lifecycle of an API request, an authentication flow,
a data pipeline, an ecommerce checkout, event processing, or yes — also
the input → logic → animation sequence of a game. The signal to create
one is always the same: "to understand/touch this, do I need to read
more than one full domain?".

- Before modifying any behavior involving more than one domain, the
  agent MUST check `flows/_index.md` first. If the behavior already has
  a documented flow, that flow is the entry point — the agent reads THAT
  file (with its exact `file:line` references), not the full domains it
  touches.
- If no flow exists for a behavior being created or significantly
  modified, the agent creates one with `pctl flow-new` (see skill
  `flow-mapping.md`).
- Flows also respect the zero-code rule: only numbered steps with
  `file:line` references and, optionally, a Mermaid sequence diagram in
  `diagrams/flows/`.
- A `desactualizado` (outdated) status on a flow is an alert visible in
  `pctl status` — never ignore it silently.

## 6. Agent context memory (`CONTEXT.md`, mandatory)

`PROJECT.md`/`GOALS.md` are written by the user and change rarely.
`sessions/*.md` is an append-only log. `CONTEXT.md` is different: the
agent writes and rewrites it, it is a single file that is fully
overwritten (not appended), and exists specifically to survive chat
compactions and new chats without having to re-read the entire session
history.

- Read it always at session start, right after `SYSTEM.md` and before
  anything else (see skill `context-maintenance.md`).
- Rewrite it when closing any session where something non-obvious was
  learned that the next session would need to know and that does not yet
  have a formal place (`PROJECT.md`, `architecture/`, `roadmaps/`,
  `flows/`, `decisions/`).
- There is no fixed line limit. If the file grows very large, consider
  promoting stable content to its permanent place (`PROJECT.md`,
  `architecture/`, `roadmaps/`, `decisions/`) and pruning the rest.
  Balance is preferred over rigid restrictions.

## 7. Technical documentation

The project's technical documentation lives in `docs/` and is organized
into five categories:

| Category | Purpose | ID Prefix | Directory |
|---|---|---|---|
| Guides | How-to guides for common tasks | GUIDE-XXXX | `docs/guides/` |
| API | API endpoint documentation | API-XXXX | `docs/api/` |
| Database | Schema, migrations, data model | DB-XXXX | `docs/database/` |
| Reference | Configuration, CLI, env vars | REF-XXXX | `docs/reference/` |
| Tutorials | Step-by-step tutorials | TUT-XXXX | `docs/tutorials/` |

The file `docs/_index.md` serves as the **documentation panel** — an
automatically generated index of all technical docs grouped by category.
Read this first when browsing or searching project documentation.

- Use `pctl doc-new` to create documents (or create them manually).
- Use `pctl doc-list` and `pctl doc-show` to browse.
- Use `pctl doc-touch` to mark docs as draft/published/outdated/deprecated.
- After manual edits, run `pctl reindex` to refresh the panel.
- See skill `docs-management.md` for detailed guidance.

Architecture docs (`architecture/`) describe WHAT the system is made of
and WHY. Technical docs (`docs/`) describe HOW to use, configure, and
work with the project.

## 8. Roadmaps

The project roadmap lives in `roadmaps/` and follows a three-level
hierarchy:

| Level | Directory | ID Prefix | Example |
|---|---|---|---|
| Phase | `roadmaps/phases/` | PHASE-XXXX | PHASE-0001 |
| Initiative | `roadmaps/initiatives/` | INITIATIVE-XXXX | INITIATIVE-0001 |
| Milestone | `roadmaps/milestones/` | M-XXXX | M-0001 |

- Each phase, initiative, and milestone is a separate markdown file.
- The index at `roadmaps/_index.md` is auto-generated by `pctl reindex`.
- Phases represent major project stages (weeks/months).
- Initiatives are significant bodies of work within a phase.
- Milestones are concrete checkpoints within an initiative.
- Use `pctl roadmap-*` commands to create and manage items.
- Direct edits to the markdown files are also valid; run `pctl reindex`
  afterward.

## 8. Documenting architecture & decisions

- When a domain is touched during a task, reflect the changes in
  `architecture/<domain>.md`. Update structure, references, and status
  via `pctl arch-touch` (see skill `architecture-update.md`).
- If the change involves a non-trivial decision (alternatives were
  considered, trade-offs were made), create an ADR in `decisions/`
  (see skill `decision-record.md`).
- When code that was previously referenced by `file:line` in any
  `.control/` file is moved or renamed, update all references and mark
  affected flows as outdated (see skill `doc-drift-check.md`).
- After editing any `.md` file in `.control/`, review it for conciseness
  and clarity (see skill `doc-concise.md`).

## 9. Controlled self-evolution

The agent may detect repeated patterns (2+ occurrences) that would
benefit from a new script or skill and propose it via the meta-skill
`skill-authoring.md`. Rules:

- Everything new is written into `skills/proposed/` or
  `scripts/lib/proposed/`, never directly into `active/` or `lib/`.
- The agent NEVER promotes a skill or script by itself. Only
  `pctl skill-promote SK-XXXX` activates something, and it requires
  explicit user confirmation in the current turn.
- Every new skill/script is registered in `skills/_index.md` with state
  `propuesta` (proposed) until promoted.
- Skills proposed by the agent can later be promoted to active (see
  skill `skill-authoring.md`).

## 10. Context loading order

In large projects, the agent NEVER loads the entire `.control/` at once.
At session start, load in this order, at most:

1. `SYSTEM.md` (this file)
2. `CONTEXT.md` (agent working memory, see section 6)
3. `PROJECT.md` and `GOALS.md` in full
4. `tasks/IN_PROGRESS.md` (index, not the full tasks)
5. `architecture/_index.md` (domain map)
6. `roadmaps/_index.md` (roadmap summary)
7. `flows/_index.md` (flow map)
8. Only the task, domain, roadmap item, and/or flow files relevant to
   what the user asked for in this turn

See skill `context-budget.md` for details.

## 11. Session close (mandatory, no exceptions)

Before ending any work session, the agent executes the checklist in
`skills/session-close.md`: close the session log, confirm indexes are
regenerated (`pctl reindex`), update `CONTEXT.md` if something was
learned that the next session needs (see `skills/context-maintenance.md`),
and verify that no `file:line` reference touched during the session was
left outdated (`pctl doc-check-refs`).

## 12. Code review

Before committing any code (`pctl git-commit --yes`), or when the user
explicitly asks for review, run through the checklist in
`skills/code-review.md`: no secrets, no dead code, errors handled,
follows project conventions, no out-of-scope changes, no sensitive data
in logs, documentation references updated.

## 13. Goal alignment

At the start of a large task or whenever the scope seems to be drifting,
review `skills/goal-check.md` to ensure the work still aligns with
project goals and success criteria.

## 14. Available skills reference

The following skills are registered in `skills/_index.md` (all active).
Refer to them when the corresponding trigger occurs:

| Skill | Trigger | File |
|---|---|---|
| `task-intake` | User creates raw todo without details | `skills/task-intake.md` |
| `task-promotion` | Task state changes | `skills/task-promotion.md` |
| `architecture-update` | Design change in a domain | `skills/architecture-update.md` |
| `decision-record` | Non-trivial technical decision | `skills/decision-record.md` |
| `session-close` | End of any work session | `skills/session-close.md` |
| `goal-check` | Start of large task or scope drift | `skills/goal-check.md` |
| `skill-authoring` | Pattern repeated 2+ times | `skills/skill-authoring.md` |
| `context-budget` | Session start in large project | `skills/context-budget.md` |
| `domain-scoping` | Before documenting or creating task | `skills/domain-scoping.md` |
| `doc-drift-check` | Session close or refactor of referenced code | `skills/doc-drift-check.md` |
| `flow-mapping` | Behavior that crosses domains | `skills/flow-mapping.md` |
| `context-maintenance` | Session start/close | `skills/context-maintenance.md` |
| `code-review` | Before git-commit or when user asks | `skills/code-review.md` |
| `debug-triage` | User reports bug without root cause | `skills/debug-triage.md` |
| `refactor-plan` | Refactor task or 2+ duplication | `skills/refactor-plan.md` |
| `deprecation-track` | Something marked obsolete | `skills/deprecation-track.md` |
| `test-gap` | Task moved to done without tests | `skills/test-gap.md` |
| `onboarding` | Project with no prior sessions | `skills/onboarding.md` |
| `doc-concise` | Post-edit of any `.md` in `.control/` | `skills/doc-concise.md` |
| `roadmap-management` | Creating, updating, or discussing the roadmap | `skills/roadmap-management.md` |
| `docs-management` | Creating, updating, or browsing technical docs | `skills/docs-management.md` |

## 15. Language

All content inside `.control/` (rules, prompts, templates, skills,
documentation) is written in English. Frontmatter field names and `pctl`
commands are fixed and not translated.

The conversation with the user is conducted in the user's language. If
the user writes in Spanish, respond in Spanish. If the user writes in
English, respond in English. Never switch the `.control/` content to
the user's language — it stays in English regardless.

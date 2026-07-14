---
id: SK-0020
nombre: roadmap-management
tipo: skill
estado: activa
disparador: "when creating, updating, or discussing the project roadmap"
ubicacion: skills/roadmap-management.md
creado_por: agente
version: 1
---

# Skill: roadmap-management

Trigger: when the user creates, updates, or discusses the project
roadmap, or when a task needs to be placed within a roadmap context.

## Roadmap hierarchy

The roadmap follows a three-level hierarchy:

| Level | Purpose | Directory | ID Prefix |
|---|---|---|---|
| Phase | Major project stage (weeks/months) | `roadmaps/phases/` | PHASE-XXXX |
| Initiative | Significant body of work within a phase | `roadmaps/initiatives/` | INITIATIVE-XXXX |
| Milestone | Concrete checkpoint within an initiative | `roadmaps/milestones/` | M-XXXX |

Each item is a separate markdown file with frontmatter metadata. The
index at `roadmaps/_index.md` is auto-generated.

## Commands

All through `pctl`:

- `pctl roadmap-phase-new "Name" --orden N` — create a new phase
- `pctl roadmap-initiative-new "Name" PHASE-XXXX` — create an initiative
- `pctl roadmap-milestone-new "Name" INITIATIVE-XXXX PHASE-XXXX` — create a milestone
- `pctl roadmap-list` — list all roadmap items
- `pctl roadmap-show <id>` — show full item details
- `pctl roadmap-touch <id> <estado>` — change item state
- `pctl reindex` — regenerate the roadmap index

Valid states per level:
- Phase: `not_started`, `in_progress`, `completed`, `blocked`, `cancelled`
- Initiative: `backlog`, `in_progress`, `completed`, `blocked`, `cancelled`
- Milestone: `backlog`, `in_progress`, `completed`, `blocked`, `cancelled`

## Procedure

1. When the user asks about or discusses the roadmap, read
   `roadmaps/_index.md` first for the overview.
2. If the discussion involves a specific item, read that item's file.
3. When a new feature or task comes in, determine which phase and
   initiative it belongs to. If no matching phase/initiative exists,
   propose creating one.
4. When closing a phase or completing an initiative, update its status
   with `pctl roadmap-touch` and run `pctl reindex`.
5. For milestones, tie them to concrete tasks (`T-XXXX`) mentioned in
   the milestone's markdown body.

## Relationship to tasks

- Phases and initiatives are higher-level than tasks. Tasks live in
  `tasks/` and are linked from initiatives via the `## Tasks` section.
- There is no automatic cross-reference — the agent maintains the
  links manually when creating or updating items.
- Milestones can reference task IDs as verification criteria.

## Direct editing

Items can be edited directly in their markdown files. After any manual
edit, run `pctl reindex` to regenerate the index. Always preserve the
frontmatter schema defined in the template files.

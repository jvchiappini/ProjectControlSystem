---
id: SK-0021
nombre: docs-management
tipo: skill
estado: activa
disparador: "when creating, updating, or browsing technical documentation"
ubicacion: skills/docs-management.md
creado_por: agente
version: 1
---

# Skill: docs-management

Trigger: when the user creates, updates, or browses project technical
documentation.

## Documentation categories

| Category | Purpose | ID Prefix | Directory |
|---|---|---|---|
| guides | How-to guides for common tasks | GUIDE-XXXX | `docs/guides/` |
| api | API endpoint documentation | API-XXXX | `docs/api/` |
| database | Schema, migrations, data model | DB-XXXX | `docs/database/` |
| reference | Configuration, CLI, env vars | REF-XXXX | `docs/reference/` |
| tutorials | Step-by-step learning tutorials | TUT-XXXX | `docs/tutorials/` |

## The documentation panel

The file `docs/_index.md` is the "documentation panel" — an index of
all technical docs organized by category. Read this first when the
user asks about project documentation.

## Commands

All through `pctl`:

- `pctl doc-new <title> <category> [--tags ...]` — create a new doc
- `pctl doc-list [--categoria ...] [--estado ...]` — list docs
- `pctl doc-show <id>` — show full doc content
- `pctl doc-touch <id> <estado>` — change doc state
- `pctl reindex` — regenerate `docs/_index.md`

States: `draft`, `published`, `outdated`, `deprecated`

## Procedure

1. When the user asks about project documentation, read `docs/_index.md`
   first (the panel).
2. If they need details on a specific doc, use `pctl doc-show <id>`.
3. When a new feature or component is implemented, evaluate if it needs
   documentation. If yes, create the appropriate doc.
4. When code changes make existing docs inaccurate, mark them as
   `outdated` with `pctl doc-touch <id> outdated`.
5. Keep the documentation panel up to date by running `pctl reindex`
   after changes.

## Relationship to other directories

- `architecture/` — system architecture (components, modules, structure)
- `docs/` — technical user documentation (how to use, API refs, guides)
- `decisions/` — ADRs with rationale
- `flows/` — cross-domain behavior documentation
- Architecture docs describe the WHAT and WHY; technical docs describe
  the HOW.

## Direct editing

Docs can be edited directly in their markdown files. After manual edits,
run `pctl reindex` to regenerate the panel. Preserve the frontmatter
schema from the templates.

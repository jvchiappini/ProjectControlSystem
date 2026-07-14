# Schema — frontmatter contract

Exact reference that `validate.py` implements. If an agent edits
markdown by hand (without `pctl`), it must match this character by
character.

## Task (tasks/**/T-XXXX.md or T-PREFIX-XXXX.md)

```
id: T-0045
titulo: string
estado: backlog | in_progress | blocked | done
prioridad: baja | media | alta | critica
tipo: feature | bug | refactor | investigacion | chore
creado_por: usuario | agente
asignado_a: usuario | agente | ambos
creado: YYYY-MM-DD
actualizado: YYYY-MM-DD
depende_de: []              # list of IDs
bloqueado_por: null          # string, required if estado=blocked
version_schema: 1
```

## Session (sessions/*.md)

```
id: S-YYYY-MM-DD-NNN
fecha: YYYY-MM-DD
agente: string
tareas_tocadas: []
resumen: string
version_schema: 1
```

## Decision / ADR (decisions/D-XXXX.md)

```
id: D-0012
titulo: string
fecha: YYYY-MM-DD
estado: propuesta | aceptada | rechazada | reemplazada
reemplaza: []
version_schema: 1
```

## Skill/Script (skills/_index.md, one row per entry)

```
id: SK-0007
nombre: string
tipo: skill | script
estado: propuesta | activa | deprecada
disparador: string
ubicacion: string
creado_por: usuario | agente
version: 1
```

## Flow (flows/F-XXXX.md)

```
id: F-0001
nombre: string
estado: borrador | vigente | desactualizado
dominios: []                 # list of domain names the flow crosses
disparador: string            # what triggers this behavior
creado: YYYY-MM-DD
actualizado: YYYY-MM-DD
version_schema: 1
```
Body with fixed sections: `## Resumen`, `## Pasos` (numbered, each
with a `file:line` reference), `## Diagrama`,
`## Dominios relacionados`, `## Notas de mantenimiento`.

## Context memory (CONTEXT.md, single file at `.control/` root)

```
actualizado: YYYY-MM-DD
actualizado_por: agente | usuario
version_schema: 1
```
Free-form body but with suggested fixed sections from the template
(`CONTEXT.md.template`). Rewritten entirely, never appended. Size
budget: ~120 body lines (`pctl context-check`).

## Task state machine

See `.control/SYSTEM.md` section 4. `validate.py` and `tasks.py`
implement it as a table of allowed transitions — do not edit that
table without updating `SYSTEM.md` as well.

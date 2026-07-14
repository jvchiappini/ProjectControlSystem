# Skill: refactor-plan

Disparador: tarea tipo `refactor`, o el agente detecta duplicacion 2+ veces del mismo patron manual.

## Procedimiento

1. **Mapear callers** — buscar todas las referencias al codigo a refactorizar (`grep -r` o busqueda en IDE). Listar archivos afectados.
2. **Enumerar riesgos** — que podria romperse. Por cada riesgo, crear checkbox en `## Criterios de aceptacion`.
3. **Estimar diff** — cuantos archivos toca, cuanto de cada uno (estimacion grosera: chico <5 archivos, mediano <15, grande >=15).
4. **Verificar flujos** — si el codigo cruza dominios, revisar `flows/_index.md`. Si existe un flujo que lo cubre, leerlo. Si no, crearlo con `pctl flow-new`.
5. **Planificar orden** — pasos numerados en `## Contexto` de la tarea para que el refactor sea revertible paso a paso.

## Output

La tarea debe tener antes de empezar a codificar:
- `## Contexto`: orden de pasos, archivos a tocar
- `## Criterios de aceptacion`: un checkbox por riesgo mitigado
- Flujo creado o actualizado si cruza dominios

## Qué NO hacer

- No refactorizar y agregar features en el mismo commit.
- No cambiar formato/whitespace junto con logica — hacerlo en commit aparte con tipo `style`.

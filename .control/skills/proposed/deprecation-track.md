# Skill: deprecation-track

Disparador: se marca algo como obsoleto (funcion, endpoint, modulo), o se crea un ADR con `reemplaza` no vacio.

## Procedimiento

1. **Buscar referencias en documentacion** — `pctl search "<nombre del componente>"` en todo `.control/` para encontrar menciones en tasks, flows, decisions, architecture.
2. **Actualizar flujos** — si algun flujo menciona el componente, marcarlo como `desactualizado` con `pctl flow-touch <id> desactualizado`.
3. **Marcar en CONTEXT.md** — agregar una linea en la seccion de `## Cambios recientes` indicando que se depreco y que lo reemplaza.
4. **Checkear tareas abiertas** — si hay tareas `in_progress` o `backlog` que referencian el componente, agregar nota en su cuerpo.
5. **ADR completo** — asegurar que el ADR que documenta el reemplazo tenga en `## Consecuencias` una lista de todo lo que hay que migrar.

## Output

Checklist en el cuerpo del ADR con items verificables. Cada item es un archivo o flujo que quedo actualizado.

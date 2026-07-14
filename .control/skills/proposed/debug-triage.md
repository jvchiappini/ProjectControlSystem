# Skill: debug-triage

Disparador: el usuario reporta un bug sin root cause clara, o pide ayuda para debuggear.

## Procedimiento

1. **Crear tarea bug** con `pctl task-intake "<reporte>"` — esto parsea el texto crudo y sugiere tipo/prioridad/dominio.
2. **Reproducir el bug** — pedir pasos concretos al usuario si no los dio.
3. **Aislar variables** — identificar si es ambiental (OS, browser, data especifica) o universal.
4. **Buscar cambios recientes** — `git log --oneline -10` para ver que se tocó antes de que apareciera.
5. **Documentar hallazgo** — agregar al cuerpo de la tarea en `## Notas del agente` con referencias `archivo:linea` a las lineas sospechosas.
6. **Si cruza dominios** — verificar `flows/_index.md` para ver si hay un flujo documentado que cubra el comportamiento afectado.

## Output

La tarea debe quedar con:
- Contexto claro del problema
- Al menos una hipotesis de causa raiz
- Referencias a las lineas de codigo involucradas
- Si no se pudo determinar causa, dejar documentado que se probo y que falta

# Skill: onboarding

Disparador: el proyecto no tiene sesiones previas (`sessions/S-*.md` no existe), indicando que es la primera vez que un agente trabaja aqui.

## Procedimiento

1. **Cargar SYSTEM.md** — siempre, es mandatorio.
2. **Verificar PROJECT.md** — si no existe, crearlo desde el template `PROJECT.md.template` con datos basicos (nombre del proyecto desde el nombre del repo/directorio, stack detectado).
3. **Mapear dominios iniciales** — revisar estructura de carpetas del proyecto (src/, app/, api/, packages/, etc) y sugerir dominios con `pctl arch-touch <dominio> --estado sin_documentar` para cada carpeta raiz significativa.
4. **Ejecutar reindex** — `pctl reindex` para que los indices reflejen el estado inicial.
5. **Crear primer flujo si aplica** — si el proyecto tiene un comportamiento punta a punta claro (ej: "request -> response" en una API, o "input -> render" en una UI), crear flujo inicial con `pctl flow-new`.
6. **Iniciar CONTEXT.md** — escribir contexto inicial con lo aprendido en este onboarding (stack, estructura, dominios identificados).

## Output

Proyecto listo para trabajar: PROJECT.md existe, dominios mapeados, CONTEXT.md escrito, primer flujo creado si aplica.

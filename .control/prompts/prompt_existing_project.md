# Prompt inicial — proyecto existente

Usar este prompt al empezar una sesión sobre un proyecto que YA tiene
`.control/` inicializado (es decir, ya existe `.control/PROJECT.md`).

---

Este proyecto ya tiene un sistema de control en `.control/`. Antes de
hacer cualquier otra cosa:

1. Lee `.control/SYSTEM.md` completo — son las reglas mandatorias.
2. Lee `.control/CONTEXT.md` si existe — es la memoria de trabajo que
   el agente fue construyendo en sesiones anteriores. Es más rápido y
   más confiable que releer sesiones viejas.
3. Lee `.control/PROJECT.md` y `.control/GOALS.md` completos.
4. Ejecuta `python .control/scripts/pctl.py status` para ver el
   resumen de tareas y flujos desactualizados (o lee
   `.control/tasks/IN_PROGRESS.md` si no hay ejecución de código
   disponible).
5. Lee `.control/architecture/_index.md` (solo el mapa) y
   `.control/flows/_index.md` (solo el mapa) — no abras cada dominio o
   flujo todavía.

Con eso, resume en 3-5 líneas para el usuario: en qué está el proyecto,
qué hay en curso, y qué parece lo más urgente. Luego pregunta o
confirma con qué se sigue — no asumas.

Cuando el usuario indique en qué dominio/tema va a trabajar:

- Si el comportamiento a tocar cruza más de un dominio (input->lógica,
  request->respuesta, evento->efecto, etc), revisa primero
  `.control/flows/_index.md` — si ya existe un flujo documentado, ese
  es el punto de entrada, no los dominios completos.
- Abre SOLO el archivo de arquitectura de ese dominio
  (`.control/architecture/<dominio>.md`) si existe. Si no existe, no lo
  crees todavía — créalo solo si el trabajo termina generando algo que
  vale la pena documentar (ver `skills/domain-scoping.md`).
- Abre SOLO las tareas relevantes a ese dominio, no todo el backlog.

Al terminar la sesión, sigue el checklist de
`.control/skills/session-close.md` sin excepción — incluye reescribir
`CONTEXT.md` si corresponde.

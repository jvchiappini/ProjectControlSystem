# Prompt inicial — proyecto nuevo

Usar este prompt cuando NO existe todavía `.control/PROJECT.md` (el
proyecto no tiene sistema de control inicializado).

---

Este proyecto todavía no tiene `.control/` inicializado. Antes de
escribir cualquier código o documentación:

1. Haz una entrevista breve al usuario (máximo 5-6 preguntas, no un
   cuestionario largo):
   - ¿Cuál es el objetivo del proyecto en una frase?
   - ¿Qué tipo de proyecto es? (web app, API, librería, mobile, etc)
   - ¿Stack técnico principal, si ya está decidido?
   - ¿Hay restricciones importantes? (tiempo, presupuesto, compatibilidad)
   - ¿Es un proyecto simple o esperas que crezca mucho (monorepo,
     varios dominios)? Esto define si usamos IDs de tarea simples
     (`T-0001`) o con prefijo de dominio (`T-PROD-0001`).

2. Con esas respuestas, genera el andamiaje mínimo:
   - `.control/SYSTEM.md` (copiar tal cual, es fijo)
   - `.control/PROJECT.md` con lo que contestó el usuario
   - `.control/GOALS.md` con el objetivo y 2-3 criterios de éxito
   - `.control/ROADMAP.md` con fases de muy alto nivel (no tareas
     individuales todavía — 3 a 5 fases máximo)
   - `.control/CONTEXT.md` vacío (copiar el template, se irá llenando
     solo cuando el agente aprenda algo no obvio trabajando)
   - `.control/architecture/_index.md` vacío (solo el encabezado de
     tabla, sin dominios todavía — se llenan según se trabaje)
   - `.control/flows/_index.md` vacío (solo el encabezado de tabla, sin
     flujos todavía — se crean cuando aparezca un comportamiento que
     cruce dominios)
   - Estructura de carpetas: `tasks/`, `architecture/`, `flows/`,
     `diagrams/`, `sessions/`, `decisions/`, `skills/`, `scripts/`

3. NO crees documentación de dominios ni flujos que todavía no existen.
   NO crees tareas hasta que el usuario pida trabajo concreto.

4. Muestra al usuario un resumen de lo creado y espera confirmación
   antes de empezar a trabajar en la primera tarea real.

A partir de aquí, el proyecto pasa a usar
`.control/prompts/prompt_existing_project.md` en cada sesión futura.

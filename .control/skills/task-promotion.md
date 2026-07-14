---
id: SK-0002
nombre: task-promotion
tipo: skill
estado: activa
disparador: "una tarea cambia de estado (se empieza a trabajar, se bloquea, se completa, se despriorizadad)"
ubicacion: skills/task-promotion.md
creado_por: usuario
version: 1
---

# Skill: task-promotion

Cuándo se dispara: cualquier cambio de estado de una tarea existente.

## Procedimiento

1. Nunca cambiar el campo `estado` editando el frontmatter a mano.
   Siempre usar `pctl task-move <id> <nuevo_estado>`.
2. Antes de mover a `in_progress`: confirmar que la tarea tiene
   contexto y criterios de aceptación razonables (si no los tiene,
   aplicar primero `task-intake.md`).
3. Antes de mover a `blocked`: tener listo el motivo concreto,
   `pctl task-move <id> blocked --motivo "..."` — el comando falla si
   no se da motivo, así que no hay forma de bloquear sin explicar por
   qué.
4. Antes de mover a `done`: verificar que todos los checkboxes de
   "Criterios de aceptación" del cuerpo estén marcados. Si legítimamente
   se completa con algo pendiente (alcance reducido, decisión
   consciente), usar `--force "motivo"` — nunca marcar checkboxes
   falsamente solo para que pase la validación.
5. Después de cualquier movimiento, correr `pctl reindex` (normalmente
   automático dentro de `task-move`, pero confirmar si se editó algo
   más a mano en el mismo turno).
6. Registrar el evento en la sesión activa:
   `pctl session-log <sid> "T-XXXX: <estado_anterior> -> <estado_nuevo>"`.

## Reapertura de tareas completadas

Mover de `done` a `in_progress` es válido (bug encontrado después,
requisito cambió). `pctl` anota automáticamente fecha y motivo si se
pasa `--motivo`. Siempre dar motivo en este caso aunque el comando no
lo exija — ayuda a quien lea el historial después.

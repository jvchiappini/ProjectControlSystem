---
id: SK-0005
nombre: session-close
tipo: skill
estado: activa
disparador: "el agente esta por terminar su turno de trabajo o la conversacion se cierra"
ubicacion: skills/session-close.md
creado_por: usuario
version: 1
---

# Skill: session-close

Cuándo se dispara: SIEMPRE, al final de cada sesión de trabajo, sin
excepción (ver `SYSTEM.md` sección 7). No es opcional aunque el
usuario no lo pida explícitamente.

## Checklist obligatorio

1. Si no se inició sesión al comenzar el turno, iniciarla ahora igual
   con `pctl session-start --agente <nombre>` (mejor tarde que nunca,
   para no perder el registro).
2. Confirmar que todo cambio de estado de tarea de este turno pasó por
   `pctl task-move` (no ediciones manuales de `estado`).
3. Correr `pctl reindex` — asegura que `BACKLOG.md`, `IN_PROGRESS.md`,
   `DONE.md` y `architecture/_index.md` reflejan el estado real.
4. Aplicar `context-maintenance.md`: si se aprendió algo en esta
   sesión que la próxima sesión (o un chat nuevo tras compactación)
   necesitaría saber, reescribir `CONTEXT.md` completo (no apendear) y
   correr `pctl context-check` para confirmar que no se pasó del
   presupuesto de tamaño.
5. Correr `pctl doc-check-refs` (o `pctl validate`, que lo incluye) —
   si hay referencias `archivo:línea` rotas por cambios de este turno,
   corregirlas antes de cerrar, no dejarlas para la próxima sesión.
6. Cerrar la sesión:
   `pctl session-close <sid> "<resumen de 1-2 lineas>" --tareas T-XXXX,T-YYYY`
7. Si quedó algo a medio hacer que no es una tarea formal todavía
   (una idea, un cabo suelto), no lo dejes solo en la conversación —
   créalo como tarea en `backlog` con `task-intake.md` para que no se
   pierda.

## Qué NO hacer

- No cerrar sesión sin `reindex` — es la causa más común de que el
  frontend muestre datos desactualizados.
- No dejar una tarea en `in_progress` sin haber tocado nada de ella en
  la sesión — si no se avanzó, considerar si debe volver a `backlog`.

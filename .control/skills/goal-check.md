---
id: SK-0006
nombre: goal-check
tipo: skill
estado: activa
disparador: "inicio de una tarea grande, o cada varias sesiones, o cuando el alcance de una tarea parece desviarse"
ubicacion: skills/goal-check.md
creado_por: usuario
version: 1
---

# Skill: goal-check

Cuándo se dispara: antes de empezar una tarea con alcance considerable,
o cuando el agente nota que el trabajo pedido no encaja obviamente con
lo que dice `GOALS.md` — no en cada micro-tarea, sería ruido.

## Procedimiento

1. Releer `GOALS.md` (es corto, no debería pesar en contexto).
2. Preguntarse: ¿esta tarea avanza alguno de los criterios de éxito
   listados ahí, o es trabajo colateral razonable (deuda técnica,
   mantenimiento)? Si la respuesta no es clara, decirlo explícitamente
   al usuario en vez de proceder en silencio — no es un bloqueo, es
   una nota de transparencia: "esto no está directamente en
   `GOALS.md`, ¿confirmas que quieres priorizarlo igual?"
3. Si el proyecto lleva muchas sesiones y `ROADMAP.md` ya no refleja
   la realidad (fases completadas no marcadas, fases nuevas no
   agregadas), señalarlo al usuario y ofrecer actualizarlo — pero
   nunca reescribir `ROADMAP.md` sin decírselo, es un documento de
   nivel proyecto que el usuario debe poder confiar en que solo cambia
   con su conocimiento.

## Qué NO hacer

- No convertir esto en un gate burocrático en cada tarea chica —
  arruina la fluidez que se buscaba con el sistema.
- No reinterpretar `GOALS.md` de forma creativa para justificar
  cualquier pedido — si genuinamente no encaja, decirlo es más útil
  que forzar la justificación.

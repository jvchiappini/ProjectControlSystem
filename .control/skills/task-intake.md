---
id: SK-0001
nombre: task-intake
tipo: skill
estado: activa
disparador: "el usuario crea un todo crudo (titulo suelto, sin detalle) desde el frontend o en el chat"
ubicacion: skills/task-intake.md
creado_por: usuario
version: 1
---

# Skill: task-intake

Cuándo se dispara: el usuario agrega un ítem nuevo al backlog con solo
un título (desde el frontend tipo kanban, o escribiéndolo en el chat)
y todavía no tiene contexto, criterios de aceptación ni prioridad
bien definida.

## Procedimiento

1. Si la tarea ya existe (creada por el usuario sin `pctl`, directo en
   markdown), léela con `pctl task-show <id>`. Si no existe todavía,
   créala con `pctl task-new "<titulo>"`.
2. No inventes alcance que el usuario no dio. Si falta información
   crítica para escribir criterios de aceptación razonables, pregunta
   — no asumas.
3. Enriquece el cuerpo del archivo (edición directa del `.md`, esto no
   pasa por `pctl`):
   - `## Contexto`: 2-4 líneas de por qué existe esta tarea y qué
     dominio toca.
   - `## Criterios de aceptación`: checkboxes concretos y verificables.
   - Si detectas dependencias con otra tarea existente, agrégalas al
     campo `depende_de` del frontmatter (edición manual del campo, no
     hay comando `pctl` para esto todavía — ver `skill-authoring.md`
     si se repite mucho y conviene automatizarlo).
4. Ajusta `--prioridad` y `--tipo` si el valor por defecto no es
   correcto, usando `pctl task-move` no aplica aquí — la prioridad se
   edita directo en el frontmatter ya que no es un cambio de estado.
5. No cambies el estado de la tarea en este paso. `task-intake` solo
   enriquece; la promoción a `in_progress` es responsabilidad de
   `task-promotion.md`.

## Qué NO hacer

- No documentar arquitectura en este paso (eso es
  `architecture-update.md`, y solo cuando se empieza a trabajar la
  tarea, no al crearla).
- No pegar código de ejemplo dentro del contexto — si hace falta
  referenciar código existente, usar `archivo:línea`.

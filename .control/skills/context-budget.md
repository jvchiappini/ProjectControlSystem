---
id: SK-0008
nombre: context-budget
tipo: skill
estado: activa
disparador: "inicio de cualquier sesion en un proyecto con muchos dominios/tareas acumuladas"
ubicacion: skills/context-budget.md
creado_por: usuario
version: 1
---

# Skill: context-budget

Cuándo se dispara: siempre al iniciar sesión, más crítico cuanto más
grande es el proyecto.

## Regla de carga (ver `SYSTEM.md` sección 6)

Orden de carga por defecto, sin excepción:

1. `PROJECT.md` + `GOALS.md` completos (cortos por diseño — si
   crecieron mucho, es señal de que hay que podarlos, no de que hay
   que dejar de leerlos).
2. `tasks/IN_PROGRESS.md` — es un índice de una línea por tarea, no
   las tareas completas.
3. `architecture/_index.md` — mapa de dominios, una línea cada uno.
4. NADA MÁS todavía. Recién con el pedido del usuario en este turno,
   cargar:
   - el/los archivo(s) de tarea específicos (`pctl task-show <id>`)
   - el `.md` de arquitectura del dominio relevante, si existe
   - archivos de código puntuales vía `archivo:línea`, nunca el
     archivo completo si la referencia ya apunta a un rango acotado

## Señales de que se está violando el presupuesto

- Cargar `tasks/BACKLOG.md` completo cuando el usuario preguntó por
  una sola tarea — usar `pctl task-list --estado backlog` con filtro,
  o `pctl task-show <id>` directo si ya se conoce el ID.
- Abrir todos los `.md` de `architecture/` "para tener contexto
  general" — el índice ya da ese contexto general, en una línea por
  dominio.
- Releer sesiones viejas completas — el resumen de cada sesión
  (`resumen:` en el frontmatter) suele alcanzar; solo abrir el cuerpo
  completo de una sesión si se necesita el detalle de eventos.

## Cuándo SÍ vale la pena cargar más

Si el usuario pide explícitamente una visión general ("dame un resumen
completo del proyecto", "quiero ver todo lo pendiente"), ahí sí se
justifica recorrer más — pero incluso entonces, preferir los índices
generados antes que abrir archivo por archivo.

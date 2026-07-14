---
id: SK-0012
nombre: context-maintenance
tipo: skill
estado: activa
disparador: "inicio de toda sesion (lectura) y cierre de toda sesion relevante (escritura)"
ubicacion: skills/context-maintenance.md
creado_por: usuario
version: 1
---

# Skill: context-maintenance

Cuándo se dispara: SIEMPRE al iniciar sesión (lectura) y al cerrar
cualquier sesión donde se aprendió algo no obvio sobre el proyecto
(escritura). Existe porque el chat se compacta o se abre uno nuevo, y
`CONTEXT.md` es lo único diseñado para sobrevivir a eso sin obligar a
releer todas las sesiones pasadas.

## Diferencia con otros archivos (no confundir)

- `PROJECT.md` / `GOALS.md`: identidad y visión, los escribe el
  usuario, cambian poco.
- `sessions/*.md`: bitácora append-only, un archivo por sesión, nunca
  se reescribe, crece indefinidamente.
- `CONTEXT.md`: memoria de trabajo del agente, UN solo archivo que se
  **reescribe completo** cada vez (no se apendea), tamaño acotado
  (~120 líneas). Es lo primero que se lee después de `SYSTEM.md`.

## Al iniciar sesión

1. Leer `CONTEXT.md` completo (es corto por diseño). Si no existe
   todavía, es normal en un proyecto nuevo o recién iniciado — crear
   uno la primera vez que se aprenda algo que valga la pena recordar.
2. Tratar su contenido como punto de partida, no como verdad
   absoluta — si algo ahí contradice lo que se observa ahora en el
   código, señalarlo y corregirlo al cerrar la sesión.

## Al cerrar sesión (parte de `session-close.md`)

1. Preguntarse: ¿aprendí algo en esta sesión que la próxima sesión (o
   un chat nuevo, o el mismo agente sin memoria de esta conversación)
   necesitaría saber y que NO está ya en `PROJECT.md`, `architecture/`
   o `flows/`? Si la respuesta es no, no hace falta tocar
   `CONTEXT.md`.
2. Si sí: reescribir el archivo completo (no agregar al final) con
   `pctl context-write --file <tmp>` (mejor generar el contenido en un
   archivo temporal y pasarlo con `--file` para evitar problemas de
   escapado en la shell). Mantener las secciones fijas del template.
3. Correr `pctl context-check`. Si avisa que se pasó del presupuesto,
   PROMOVER lo que ya es estable y confirmado a su lugar definitivo
   (`PROJECT.md` si es identidad del proyecto,
   `architecture/<dominio>.md` si es de un módulo específico,
   `decisions/` si es una decisión con trade-offs) y podar
   `CONTEXT.md` a lo que sigue siendo memoria de trabajo genuina.
4. Actualizar la sección "Última sesión relevante" con el id de sesión
   y una línea, no el contenido completo del log.

## Qué NO hacer

- No convertir esto en un segundo `sessions/` — si empieza a crecer sin
  límite, es que se está apendeando en vez de reescribiendo, o que no
  se está podando lo que ya se promovió a otro lado.
- No duplicar contenido que ya vive en `PROJECT.md`, `architecture/` o
  `flows/` — `CONTEXT.md` es para lo que todavía no tiene un lugar
  formal o es demasiado efímero para merecerlo.

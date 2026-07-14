---
id: SK-0003
nombre: architecture-update
tipo: skill
estado: activa
disparador: "se hizo un cambio de diseño/estructura en un dominio y hay que reflejarlo en la documentacion"
ubicacion: skills/architecture-update.md
creado_por: usuario
version: 1
---

# Skill: architecture-update

Cuándo se dispara: al terminar (o durante) el trabajo de una tarea que
tocó el diseño de un dominio — no cada vez que se escribe una línea de
código, solo cuando cambia algo que otra persona/agente necesitaría
saber para entender el sistema.

## Regla previa (ver `domain-scoping.md`)

Antes de escribir, confirma que el dominio de destino es exactamente
uno. Si la tarea tocó dos dominios a la vez, actualiza cada `.md` por
separado, cada uno con su propio alcance — no mezcles ambos en un
solo archivo.

## Procedimiento

1. Si `architecture/<dominio>.md` no existe todavía:
   `pctl arch-touch <dominio> --estado parcial --crear-archivo`. Esto
   crea el archivo con la plantilla estándar y actualiza el índice.
2. Editar el archivo directamente (no hay comando `pctl` para el
   contenido, solo para el registro en el índice). Mantener siempre
   las secciones fijas: `## Proposito`, `## Componentes clave`,
   `## Diagrama`, `## Decisiones relevantes`, `## Estado de
   documentacion`.
3. En "Componentes clave", cada línea es
   `Nombre — qué hace, dónde vive: archivo:línea-línea`. Nunca pegar
   el código real (ver `SYSTEM.md` sección 3).
4. Si el cambio amerita un diagrama nuevo o modificado, el `.mmd` va
   en `diagrams/<dominio>.mmd` y se referencia desde la sección
   `## Diagrama` — el diagrama vive aparte, nunca embebido como
   bloque de código dentro del `.md`.
5. Si la decisión detrás del cambio es no trivial (hubo alternativas
   descartadas, trade-offs), no la expliques largo acá — crea un ADR
   con `decision-record.md` y solo enlázalo en "Decisiones relevantes".
6. Al terminar, actualizar el estado real con
   `pctl arch-touch <dominio> --estado <parcial|documentado>` (esto
   también actualiza la fecha en el índice).

## Qué NO hacer

- No tocar `architecture/_index.md` a mano — es generado.
- No documentar dominios que no fueron parte de la tarea actual,
  aunque los hayas visto de pasada explorando el código. Para esos,
  a lo sumo `pctl arch-touch <dominio_visto> --estado sin_documentar`
  (sin `--crear-archivo`), solo para dejar constancia de que existe.

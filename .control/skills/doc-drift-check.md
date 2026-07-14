---
id: SK-0010
nombre: doc-drift-check
tipo: skill
estado: activa
disparador: "cierre de sesion, o despues de refactors que mueven/renumeran lineas de codigo"
ubicacion: skills/doc-drift-check.md
creado_por: usuario
version: 1
---

# Skill: doc-drift-check

Cuándo se dispara: parte del checklist de `session-close.md`, y
también inmediatamente después de cualquier refactor que sepas que
movió líneas de código en un archivo referenciado desde
`architecture/` o `tasks/`.

## Por qué existe

El sistema evita pegar código en markdown y en su lugar referencia
`archivo:línea`. El costo de esa decisión es que las referencias se
desactualizan si el código se mueve. Esta skill es el contrapeso: sin
ella, la documentación referenciada se pudre silenciosamente.

## Procedimiento

1. Correr `pctl validate` (incluye el chequeo de referencias). Reporta
   referencias a archivos que ya no existen o líneas fuera de rango.
2. Esto detecta roturas obvias (archivo borrado/movido, archivo
   truncado) pero NO detecta que la línea 42 sigue existiendo pero
   ahora es código distinto — eso requiere criterio del agente: si en
   esta sesión se tocó un archivo que está referenciado desde
   `architecture/`, revisar manualmente si la referencia sigue
   apuntando a lo que dice que apunta.
3. Corregir las referencias rotas antes de cerrar sesión, no
   posponerlas — se acumulan rápido en proyectos grandes.
4. Si un mismo archivo se refactoriza muy seguido y esto se vuelve
   fricción constante, es una buena candidata para proponer con
   `skill-authoring.md` un script que recalcule automáticamente los
   rangos de línea usando anclas de texto en vez de números fijos.

## Qué NO hacer

- No ignorar errores de `pctl validate` "para después" — si se
  acumulan, nadie los corrige nunca y la documentación deja de ser
  confiable, que es exactamente lo que este sistema busca evitar.

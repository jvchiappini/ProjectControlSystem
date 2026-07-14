---
id: SK-0007
nombre: skill-authoring
tipo: skill
estado: activa
disparador: "el agente detecta un patron manual repetido 2 o mas veces que podria automatizarse"
ubicacion: skills/skill-authoring.md
creado_por: usuario
version: 1
---

# Skill: skill-authoring (meta-skill)

Cuándo se dispara: el agente nota que hizo manualmente lo mismo dos o
más veces en el proyecto (ej: siempre calcula el próximo ID de ADR a
mano, siempre reformatea el mismo tipo de dato antes de un análisis).
Esta es la única skill que crea otras skills o scripts — nunca se
salta el flujo de propuesta.

## Regla dura (ver `SYSTEM.md` sección 5)

El agente JAMÁS mueve algo directo a `active/` (skills) o `lib/`
(scripts). Todo nace en `proposed/`. Promoción a `active/` requiere
`pctl skill-promote SK-XXXX`, ejecutado solo con confirmación explícita
del usuario en el turno actual.

## Procedimiento para proponer un script nuevo

1. Escribir el script en `scripts/lib/proposed/<nombre>.py`. Debe ser
   autocontenido o importar solo de `scripts/lib/` (no depender de
   `proposed/` de otro script no promovido).
2. Registrar la propuesta:
   ```
   pctl skill-propose "<nombre>" --tipo script \
     --disparador "<cuando se usaria>" \
     --ubicacion "scripts/lib/proposed/<nombre>.py"
   ```
3. Explicar al usuario, en el mismo turno, qué hace el script y por
   qué conviene automatizarlo. Preguntar si lo promueve.
4. Si el usuario confirma: `pctl skill-promote SK-XXXX`, y mover el
   archivo de `proposed/` a `lib/` (esto sí es una edición manual de
   filesystem, no hay comando `pctl` para mover el archivo físico
   todavía — candidato irónico para su propia automatización futura).
5. Si el usuario no confirma o no responde: la propuesta queda en
   `proposed/` sin usarse. No se borra — puede ser útil más adelante o
   para otro agente que trabaje el proyecto.

## Procedimiento para proponer una skill (markdown de procedimiento)

Igual que arriba pero el archivo va en `skills/proposed/<nombre>.md`
con el mismo frontmatter que las demás skills (`estado: propuesta`).

## Qué NO hacer

- No proponer una skill por algo que pasó una sola vez.
- No proponer scripts que dupliquen algo que `pctl` ya hace.
- No escribir código con efectos destructivos (borrar archivos,
  sobrescribir sin backup) sin señalarlo explícitamente en la
  propuesta al usuario.

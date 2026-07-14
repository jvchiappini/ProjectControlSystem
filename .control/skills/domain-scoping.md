---
id: SK-0009
nombre: domain-scoping
tipo: skill
estado: activa
disparador: "antes de crear o editar documentacion de arquitectura, o al crear una tarea nueva"
ubicacion: skills/domain-scoping.md
creado_por: usuario
version: 1
---

# Skill: domain-scoping

Cuándo se dispara: cada vez que el agente está por escribir en
`architecture/<dominio>.md` o crear una tarea, y necesita decidir a
qué dominio pertenece.

## Procedimiento

1. Mirar `architecture/_index.md` — si el pedido del usuario menciona
   claramente un dominio ya existente ahí, usar ese, no crear uno
   nuevo con nombre ligeramente distinto (ej: no crear "producto"
   si ya existe "productos").
2. Si el pedido es ambiguo entre dos dominios existentes (ej: "arregla
   el checkout" podría ser `pagos` o `productos`), preguntar al
   usuario cuál corresponde antes de tocar cualquier archivo. No
   documentar en ambos "por las dudas".
3. Si el pedido claramente introduce un dominio nuevo que no está en
   el índice, confirmarlo con el usuario en una línea antes de
   crearlo formalmente (evita typos o granularidad inconsistente,
   ej: crear `carrito` cuando el proyecto ya tiene `pagos` y el
   carrito debería vivir ahí dentro).
4. Una vez decidido el dominio, TODO el trabajo de documentación de
   esa tarea va únicamente ahí. No tocar otros `.md` de dominio aunque
   el código cruce límites — si el cruce es real y relevante,
   mencionarlo en "Componentes clave" del dominio principal como una
   referencia, sin expandir el otro dominio.

## Granularidad de dominios

Ni tan grande ("backend" como un solo dominio gigante) ni tan chico
(un dominio por archivo). Buena señal: un dominio agrupa lo que un
desarrollador nuevo tendría que entender junto para tocar esa parte
del sistema sin leer todo el proyecto.

## Qué NO hacer

- No crear un dominio nuevo por cada tarea — reusar los existentes es
  la norma, crear uno nuevo es la excepción.
- No renombrar un dominio existente sin avisar al usuario — rompe
  referencias en tareas y ADRs ya creados.

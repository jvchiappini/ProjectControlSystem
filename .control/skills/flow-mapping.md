---
id: SK-0011
nombre: flow-mapping
tipo: skill
estado: activa
disparador: "se implementa o modifica un comportamiento/interaccion que involucra mas de un dominio, o el usuario pregunta 'que pasa cuando...'"
ubicacion: skills/flow-mapping.md
creado_por: usuario
version: 1
---

# Skill: flow-mapping

Cuándo se dispara: cualquier comportamiento observable de principio a
fin que involucra más de un dominio — típico en videojuegos (input →
lógica de juego → animación → audio) pero aplica a cualquier sistema
con interacciones entre módulos (checkout que toca carrito + pagos +
notificaciones).

## Por qué existe (diferencia con `architecture-update.md`)

`architecture/<dominio>.md` documenta un módulo por dentro. Un
**flujo** documenta un comportamiento de punta a punta, sin importar
cuántos módulos toque. Sin esto, entender "qué pasa cuando el jugador
presiona atacar" obliga a leer completos los dominios de input,
combate y animación — exactamente el costo de tokens que este sistema
existe para evitar.

## Antes de tocar código: revisar si ya existe un flujo

1. Leer `flows/_index.md` (una línea por flujo, liviano). Si el
   comportamiento que se va a tocar ya tiene un flujo documentado,
   abrir SOLO ese archivo (`pctl flow-show <id>`) — es la forma más
   rápida de saber exactamente qué archivo y qué línea tocar, sin leer
   el resto del código.
2. Si el flujo existe pero su estado es `desactualizado`, corregirlo
   como parte de esta misma tarea antes de confiar en sus pasos.

## Crear un flujo nuevo

Se dispara cuando: se implementa una interacción nueva que cruza
dominios, o el agente nota que explicó "qué pasa cuando X" más de una
vez sin tener un flujo que lo respalde.

1. `pctl flow-new "<nombre descriptivo>" --dominios <a,b,c> --disparador "<que lo activa>"`
2. Completar `## Pasos` con una lista numerada, cada paso como una
   afirmación corta + referencia exacta `archivo:línea-línea`. Nunca
   pegar el código — el valor del flujo es la ruta, no una copia.
3. Si el flujo tiene una secuencia temporal clara (A llama a B que
   dispara C), agregar un diagrama de secuencia Mermaid en
   `diagrams/flows/<id>.mmd` y referenciarlo en `## Diagrama`.
4. Marcar `estado: vigente` con `pctl flow-touch <id> vigente` una vez
   verificado que los pasos son correctos (nace en `borrador`).
5. NO listar los dominios como si fueran documentación de arquitectura
   completa — en `## Dominios relacionados` solo van los nombres, el
   detalle de cada dominio sigue viviendo en su propio
   `architecture/<dominio>.md`.

## Mantenimiento

- Si un refactor cambia archivos referenciados por un flujo vigente,
  actualizar los pasos en la misma sesión (parte de
  `doc-drift-check.md`) o, si no hay tiempo, marcar
  `pctl flow-touch <id> desactualizado` para que quede visible en
  `pctl status` y nadie confíe en pasos rotos.
- Un flujo con más de ~8-10 pasos probablemente debería dividirse en
  dos flujos más específicos (ej: "ataque cuerpo a cuerpo" y "ataque a
  distancia" en vez de un único "sistema de combate").

## Qué NO hacer

- No crear un flujo para algo que vive enteramente en un solo dominio
  — eso ya lo cubre `architecture/<dominio>.md`.
- No duplicar contenido de arquitectura de dominio dentro del flujo;
  el flujo es la ruta de ejecución, no una segunda copia del diseño.

# SYSTEM.md — reglas mandatorias del proyecto

Este archivo se carga SIEMPRE, en cualquier sesión, con cualquier agente
(Claude, GPT, Cursor, Copilot, un humano leyendo a mano, etc). Es el
contrato invariable del proyecto. Nunca se ignora, aunque el usuario no
lo mencione explícitamente.

## 0. Fuente de verdad

El sistema de archivos dentro de `.control/` es la ÚNICA fuente de
verdad del estado del proyecto. Ningún agente debe confiar en su propia
memoria de conversación para saber qué existe, qué está pendiente o qué
se decidió — siempre relee `.control/` al empezar una sesión.

## 1. Herramienta de control (`pctl`)

Si el entorno tiene ejecución de código (bash/python disponible):

- TODA operación sobre tareas, sesiones e índices se hace vía
  `python .control/scripts/pctl.py <comando>`. Ver `pctl.py --help`.
- Los archivos `tasks/BACKLOG.md`, `tasks/IN_PROGRESS.md`, `tasks/DONE.md`
  y `architecture/_index.md` son **generados**. Nunca se editan a mano.
  Se regeneran con `pctl reindex`.
- Lo único que se edita directamente con un editor de texto es:
  - el cuerpo narrativo de un archivo de tarea (`tasks/**/T-XXXX.md`)
  - `PROJECT.md`, `GOALS.md`, `ROADMAP.md`
  - `architecture/<dominio>.md` (solo el dominio que se está tocando)
  - `decisions/D-XXXX.md`

Si el entorno NO tiene ejecución de código (agente de solo-chat), se
edita el markdown directamente respetando exactamente el schema de
frontmatter definido en `scripts/lib/schema.md`, para que `pctl` pueda
seguir leyéndolo después sin romperse.

## 2. Documentación perezosa (regla obligatoria)

- El agente documenta **solo** el dominio relacionado con la tarea
  actual. Nunca crea ni expande documentación de dominios que no fueron
  pedidos, aunque los detecte explorando el código.
- Si al explorar el repo aparece un dominio nuevo sin documentar, el
  agente SOLO agrega una fila a `architecture/_index.md` (vía
  `pctl arch touch <dominio> --estado sin_documentar`). No escribe
  contenido ahí.
- Antes de documentar, el agente debe tener claro un único dominio de
  destino. Si la tarea es ambigua entre dos dominios, pregunta al
  usuario en vez de documentar ambos (ver skill `domain-scoping.md`).

## 3. Cero código dentro de markdown

- Ningún archivo dentro de `.control/` contiene bloques de código real
  (funciones, clases, snippets ejecutables copiados del proyecto).
- Toda referencia a código usa la forma `ruta/archivo:línea` o
  `ruta/archivo:línea_inicio-línea_fin`. Ejemplo correcto:
  "La validación de stock vive en `src/products/stock.py:42-58`."
  Ejemplo prohibido: pegar esas líneas dentro del `.md`.
- Excepciones permitidas: diagramas Mermaid (`.mmd`), y comandos de
  shell cortos de uso de `pctl` como ejemplo de instrucción (no de
  lógica de negocio).

## 4. Máquina de estados de tareas

Transiciones válidas únicamente:

```
backlog <-> in_progress <-> blocked
in_progress -> done
in_progress -> backlog
done -> in_progress   (reabrir; pctl anota motivo y fecha automáticamente)
```

`backlog -> done` directo está PROHIBIDO — siempre debe pasar por
`in_progress`, aunque sea un instante, para no perder registro de que
algo se hizo. `in_progress -> blocked` exige motivo (`--motivo "..."`).
`in_progress -> done` exige que los checkboxes de "Criterios de
aceptación" estén todos marcados, salvo `--force "motivo"` (queda
logueado). Todo cambio de estado genera una línea en el log de sesión
activo — no hay cambios de estado silenciosos.

## 4.1 Flujos (obligatorio para comportamientos que cruzan dominios)

Un dominio (`architecture/<dominio>.md`) documenta un módulo. Un
**flujo** (`flows/F-XXXX.md`) documenta un comportamiento observable
de principio a fin que cruza dominios. Esto aplica a CUALQUIER
sistema con interacción entre módulos, no solo videojuegos: el ciclo
de vida de una request en una API, un flujo de autenticación, un
pipeline de datos, un checkout de ecommerce, un procesamiento de
eventos, o — sí — también la secuencia input → lógica → animación de
un videojuego. La señal para crear uno es siempre la misma: "para
entender/tocar esto, ¿tengo que leer más de un dominio completo?".

- Antes de modificar cualquier comportamiento que involucre más de un
  dominio, el agente DEBE revisar `flows/_index.md` primero. Si el
  comportamiento ya tiene un flujo documentado, ese flujo es el punto
  de entrada — el agente lee ESE archivo (con sus referencias exactas
  `archivo:línea`), no los dominios completos que toca.
- Si no existe un flujo para un comportamiento que se está creando o
  modificando de forma significativa, el agente crea uno con
  `pctl flow-new` (ver skill `flow-mapping.md`).
- Los flujos también respetan la regla de cero código embebido: solo
  pasos numerados con referencias `archivo:línea` y, opcionalmente, un
  diagrama de secuencia Mermaid en `diagrams/flows/`.
- Estado `desactualizado` en un flujo es una señal de alerta visible en
  `pctl status` — nunca se ignora silenciosamente.

## 4.2 Memoria de contexto del agente (`CONTEXT.md`, obligatoria)

`PROJECT.md`/`GOALS.md` los escribe el usuario y cambian poco.
`sessions/*.md` es una bitácora que solo crece. `CONTEXT.md` es
distinto: lo escribe y reescribe el propio agente, es un único archivo
que se sobrescribe completo (no se apendea), con un presupuesto de
tamaño (~120 líneas), y existe específicamente para sobrevivir a
compactaciones de chat y a chats nuevos sin depender de releer todo el
historial de sesiones.

- Se lee siempre al iniciar sesión, justo después de `SYSTEM.md` y
  antes que cualquier otra cosa (ver skill `context-maintenance.md`).
- Se reescribe al cerrar cualquier sesión donde se aprendió algo no
  obvio que la próxima sesión necesitaría saber y que no tiene todavía
  un lugar formal (`PROJECT.md`, `architecture/`, `flows/`,
  `decisions/`).
- Si crece más allá del presupuesto (`pctl context-check` lo avisa),
  lo estable se promueve a su lugar definitivo y el archivo se poda.

## 5. Auto-evolución controlada

El agente puede detectar patrones repetidos (2+ veces) que convendría
automatizar y proponer un script o skill nuevo con la skill meta
`skill-authoring.md`. Reglas:

- Todo lo nuevo se escribe en `skills/proposed/` o
  `scripts/lib/proposed/`, nunca directo en `active/` ni en `lib/`.
- El agente NUNCA promueve una skill o script por sí mismo. Solo
  `pctl skill promote SK-XXXX` activa algo, y requiere confirmación
  explícita del usuario en el turno actual.
- Toda skill/script nuevo se registra en `skills/_index.md` con estado
  `propuesta` hasta ser promovido.

## 6. Presupuesto de contexto

En proyectos grandes, el agente NUNCA carga todo `.control/` de una
vez. Al iniciar sesión carga, en este orden, como máximo:

1. `SYSTEM.md` (este archivo)
2. `CONTEXT.md` (memoria de trabajo del agente, ver sección 4.2)
3. `PROJECT.md` y `GOALS.md` completos (son cortos por diseño)
4. `tasks/IN_PROGRESS.md` (índice, no las tareas completas)
5. `architecture/_index.md` (mapa, 1 línea por dominio)
6. `flows/_index.md` (mapa, 1 línea por flujo)
7. Solo el/los archivo(s) de tarea, dominio y/o flujo relevantes a lo
   que el usuario pidió en este turno

Ver skill `context-budget.md` para el detalle.

## 7. Cierre de sesión (obligatorio, sin excepción)

Antes de terminar cualquier sesión de trabajo, el agente ejecuta el
checklist de `skills/session-close.md`: cerrar el log de sesión,
confirmar que los índices están regenerados (`pctl reindex`),
actualizar `CONTEXT.md` si se aprendió algo que la próxima sesión
necesite saber (`skills/context-maintenance.md`), y verificar que
ninguna referencia `archivo:línea` tocada en la sesión quedó
desactualizada (`pctl doc-check-refs`).

## 8. Idioma y tono

Todo el contenido de `.control/` se escribe en el mismo idioma que usa
el usuario en la conversación, salvo nombres de campos de frontmatter
y comandos de `pctl`, que son fijos en inglés/español técnico según el
schema (no se traducen).

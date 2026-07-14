# Project Control System

Sistema de control de proyectos agnóstico de agente: una sola fuente
de verdad en markdown + un CLI (`pctl`) que hace el trabajo mecánico,
para que cualquier agente de IA (o humano) pueda trabajar sobre
proyectos extensos sin perder contexto ni gastar tokens en tareas
repetitivas.

## Frontend (control panel completo)

Un panel web completo — sin dependencias que instalar, sin build step —
que muestra y edita absolutamente todo lo que vive en `.control/`.
Corre con un servidor Python local (solo librería estándar) que expone
una API y sirve la interfaz; el navegador solo necesita `fetch`, así
que funciona en cualquier navegador moderno (Chrome, Firefox, Edge,
Safari).

### Arrancar

```
python3 .control/frontend/server.py
```

Abre `http://localhost:8420` en el navegador. El puerto se puede
cambiar con `--port`.

### Qué se puede hacer desde ahí

- **Tablero**: kanban con arrastrar y soltar entre `backlog / en curso
  / bloqueada / completadas`, respetando la misma máquina de estados
  que `pctl` (no deja pasar a "completadas" con criterios sin marcar,
  pide motivo al bloquear). Crear tareas nuevas desde acá — el agente
  las va a encontrar y enriquecer en su próxima sesión.
- **Arquitectura**: canvas infinito (pan con arrastrar el fondo, zoom
  con la rueda) con un nodo por dominio documentado. Cada nodo se
  puede arrastrar (la posición se recuerda) y "desplegar" para ver el
  contenido completo del dominio, con sus referencias de código y
  diagrama Mermaid si tiene uno asociado.
- **Flujos**: el mismo tipo de canvas infinito, pero con jerarquía:
  cada flujo puede tener subflujos. Doble click en "entrar ↳" navega
  hacia adentro del flujo (con breadcrumb arriba para volver), mostrando
  sus subflujos como nodos hijos. "Desplegar" muestra pasos, dominios
  cruzados y diagrama sin salir del nivel actual.
- **Sesiones**: bitácora de todas las sesiones de trabajo pasadas,
  de solo lectura.
- **Decisiones**: lista de ADRs, se pueden crear nuevas desde acá.
- **Skills**: registro de skills/scripts, con botón "Promover" para
  las que el agente propuso y están esperando confirmación humana.
- **Contexto**: muestra `CONTEXT.md` (la memoria del agente) y permite
  editarlo manualmente si hace falta corregir algo.

### Cómo se mantiene todo sincronizado

El servidor importa exactamente los mismos módulos de `scripts/lib/`
que usa `pctl` — no hay dos implementaciones de la lógica de negocio.
Cualquier cambio hecho desde el frontend es indistinguible de un
cambio hecho por un agente vía `pctl`, y viceversa.

## Instalación en un proyecto

1. Copiar la carpeta `.control/` completa a la raíz de tu proyecto.
2. Copiar `PROJECT.md.template`, `GOALS.md.template`,
   `ROADMAP.md.template` y `CONTEXT.md.template` como `PROJECT.md`,
   `GOALS.md`, `ROADMAP.md` y `CONTEXT.md` (sin el `.template`) y
   completarlos — o dejar que el agente lo haga siguiendo
   `prompts/prompt_new_project.md`.
3. Verificar que `python3` esté disponible: `python3 .control/scripts/pctl.py status`.

## Integración con opencode

Si usás opencode como agente, no necesitas configurar nada manualmente.
El archivo `opencode.json` en la raíz ya le dice a opencode que cargue
`.control/SYSTEM.md` automáticamente al inicio de cada sesión (vía el
campo `instructions`).

El flujo es:

1. opencode arranca y lee `opencode.json` → carga `.control/SYSTEM.md`
   como instrucción inicial.
2. `SYSTEM.md` (sección 9, `context-budget.md`) ordena al agente leer
   `CONTEXT.md`, `PROJECT.md`, `GOALS.md`, y los índices ligeros.
3. El agente detecta si es un proyecto nuevo (sin sesiones prevías) o
   existente, y carga el prompt correspondiente desde `prompts/`.
4. Al cerrar sesión, `session-close.md` + `context-maintenance.md`
   aseguran que `CONTEXT.md` se reescriba con lo aprendido, listo para
   la próxima sesión.

El resultado: podés cerrar opencode, volver a abrirlo al día siguiente,
y el agente retoma exactamente donde lo dejaste — sin tener que
explicarle el proyecto de nuevo.

## Los tres prompts

- **`.control/SYSTEM.md`** — mandatorio, se carga siempre, en cualquier
  sesión, con cualquier agente. Son las reglas invariables.
- **`.control/prompts/prompt_existing_project.md`** — prompt inicial
  cuando el proyecto YA tiene `.control/PROJECT.md`.
- **`.control/prompts/prompt_new_project.md`** — prompt inicial cuando
  el proyecto NO tiene `.control/` todavía.

Para otros agentes (Claude Code, Cursor, ChatGPT, etc), configurá el
system prompt para que cargue `.control/SYSTEM.md` siempre, y el prompt
correspondiente según si detecta `.control/PROJECT.md` o no.

## El CLI: `pctl`

```
python3 .control/scripts/pctl.py <comando>
```

| Comando | Qué hace |
|---|---|
| `task-new "titulo" [--prioridad] [--tipo] [--dominio] [--prefix]` | crea una tarea |
| `task-move <id> <estado> [--motivo] [--force]` | cambia estado respetando la máquina de estados |
| `task-show <id>` | muestra una tarea |
| `task-list [--estado]` | lista tareas |
| `status` | resumen corto del proyecto (incluye flujos desactualizados) |
| `reindex` | regenera BACKLOG/IN_PROGRESS/DONE/arch index/flows index |
| `validate` | valida schema + referencias `archivo:línea` |
| `doc-check-refs` | valida solo referencias de código |
| `session-start [--agente]` / `session-log <id> "texto"` / `session-close <id> "resumen" [--tareas]` | bitácora de sesión |
| `arch-touch <dominio> [--estado] [--crear-archivo]` | registra/crea documentación de un dominio |
| `arch-list` | lista dominios y su estado |
| `flow-new "nombre" --dominios a,b --disparador "..."` | crea un flujo (comportamiento que cruza dominios) |
| `flow-show <id>` / `flow-list [--dominio] [--estado]` / `flow-touch <id> <estado>` | consultar y actualizar flujos |
| `context-show` / `context-write --file <archivo>` / `context-check` | memoria de contexto del agente (`CONTEXT.md`) |
| `skill-propose <nombre> --tipo --disparador --ubicacion` | propone skill/script nuevo (no lo activa) |
| `skill-promote <id>` | activa una skill propuesta (requiere confirmación humana) |
| `skill-list [--estado]` | lista skills registradas |

## Estructura

```
.control/
  SYSTEM.md                  ← prompt mandatorio
  CONTEXT.md                   ← memoria de trabajo del agente (la reescribe el agente)
  PROJECT.md GOALS.md ROADMAP.md  ← identidad y visión del proyecto (las escribe el usuario)
  prompts/                     ← los dos prompts iniciales
  tasks/                         ← BACKLOG/IN_PROGRESS/DONE (generados) + T-XXXX.md (fuente)
  architecture/                    ← _index.md (generado) + <dominio>.md (on-demand) — documenta MÓDULOS
  flows/                             ← _index.md (generado) + F-XXXX.md — documenta COMPORTAMIENTOS que cruzan módulos
  diagrams/                            ← .mmd referenciados desde architecture/ y flows/
  decisions/                             ← D-XXXX.md, ADRs
  sessions/                                ← bitácora append-only
  skills/                                    ← procedimientos (activas + proposed/)
  scripts/                                    ← pctl.py + lib/ (+ lib/proposed/)
```

## Principios clave (ver `SYSTEM.md` para el detalle completo)

1. **Fuente única de verdad**: el filesystem, no la memoria del agente.
2. **Documentación perezosa**: solo se documenta el dominio que se
   trabaja, nunca por anticipado.
3. **Cero código en markdown**: referencias `archivo:línea`, jamás
   código pegado.
4. **Máquina de estados estricta**: `backlog → in_progress → done`,
   nunca un salto directo, todo cambio queda logueado.
5. **Flujos sobre dominios**: `architecture/` documenta módulos;
   `flows/` documenta comportamientos de punta a punta que cruzan
   módulos (el ciclo de una request, un checkout, un pipeline de
   datos, o input→lógica→animación en un videojuego) — así el agente
   sabe exactamente dónde "atacar" sin leer todo el sistema.
6. **Memoria de contexto persistente**: `CONTEXT.md` es la memoria de
   trabajo del agente, sobrevive a compactaciones de chat y a chats
   nuevos, se reescribe completa (no se apendea) y tiene presupuesto
   de tamaño acotado.
7. **Auto-evolución con rieles**: el agente puede proponer skills o
   scripts nuevos, pero nunca los activa sin confirmación humana.
8. **Presupuesto de contexto**: índices livianos primero, detalle solo
   bajo demanda.

## Frontend

El frontend (kanban + canvas de arquitectura tipo Figma) no necesita
su propio modelo de datos: lee y escribe los mismos archivos markdown
de `.control/`. Cuando el usuario arrastra una tarjeta o crea un todo
desde la UI, escribe directo al archivo correspondiente (o llama a
`pctl` si corre en un backend con acceso al filesystem); el agente,
en su siguiente sesión, simplemente lee el estado actualizado.

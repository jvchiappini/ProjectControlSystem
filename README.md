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

Desde la raíz de tu proyecto (Python 3.8+ y git):

```
git clone --depth 1 https://github.com/jvchiappini/ProjectControlSystem.git /tmp/pc
python /tmp/pc/.control/scripts/update.py --source /tmp/pc --target .
```

Instala `.control/` y crea `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `opencode.json`,
`.github/copilot-instructions.md` y `.claude/settings.json` **solo si no existen** (si ya tenés los tuyos, no
se tocan y el instalador te dice qué línea agregar). Después, el agente
completa `PROJECT.md`/`GOALS.md` siguiendo `prompts/prompt_new_project.md`.

### Como skill o plugin (cualquier LLM)

Las skills `skills/project-control/SKILL.md` (usar/instalar ProjectControl) y
`skills/lean/SKILL.md` (código mínimo, utilidades compartidas, salida sin
tokens basura) siguen el formato estándar `SKILL.md`:

- Claude Code: `/plugin marketplace add jvchiappini/ProjectControlSystem` y luego
  `/plugin install project-control@project-control` (o en un paso:
  `/plugin install project-control --marketplace jvchiappini/ProjectControlSystem`).
- Otros agentes con soporte de skills: copiar `skills/<nombre>/` a su carpeta de
  skills. Sin soporte de skills: `AGENTS.md` (Codex, Cursor, opencode...),
  `GEMINI.md`, `.github/copilot-instructions.md`.

`skills/lean/SKILL.md` y `.github/copilot-instructions.md` se generan con
`update.py --build-manifest` desde `.control/skills/lean.md` y `AGENTS.md`:
editar esos originales.

## Lean mode

Inspirado en [Ponytail](https://github.com/dietrichgebert/ponytail), integrado con
la documentación de ProjectControl. Antes de escribir código el agente busca qué
ya existe (`pctl reuse`), usa stdlib/plataforma/dependencias instaladas, y si
algo se repite lo mueve a una utilidad compartida (`pctl dupes`). Nunca recorta
validación, seguridad ni accesibilidad, y no reimprime código ni hace resúmenes
innecesarios. Niveles `off | lite | full | strict` (por defecto `lite`):
`pctl lean <nivel>`. Detalle en `.control/skills/lean.md`.

## Diseño de interfaces (`ui-design`)

Inspirado en [Impeccable](https://github.com/pbakaus/impeccable), integrado con
la memoria de ProjectControl. Antes de diseñar una UI el agente analiza el repo
(stack, componentes, datos, assets), deduce el tipo de producto (p. ej. qué
clase de tienda) y lo que le falta, hace preguntas en rondas con valores por
defecto propuestos, ofrece 2-3 direcciones visuales y guarda la elegida en
`architecture/design-system.md` + un ADR. Luego planifica en tareas, construye
con tokens evitando los patrones genéricos de IA, y verifica con una crítica
puntuada y una auditoría P0-P3 cuyos hallazgos quedan como tareas. Detalle en
`.control/skills/ui-design.md` y `.control/prompts/ui-discovery.md`.

## Contexto y memoria entre sesiones

El objetivo: que el agente arranque sabiendo todo lo necesario gastando
el mínimo de contexto, y que nada de lo aprendido se pierda.

- **`pctl brief`**: un solo comando con presupuesto acotado (~2k tokens)
  que reemplaza leer ~10 archivos: alertas, reglas locales, el *handoff*
  de la sesión anterior (próximos pasos y preguntas abiertas), tareas en
  curso con progreso de criterios, `CONTEXT.md`, roadmap y git.
- **Handoff**: `pctl session-close <sid> "resumen" --next "..." --question "..."`.
  La próxima sesión lo ve primero.
- **Notas inmediatas**: `pctl context-note "..." --tipo gotcha` guarda un
  aprendizaje en el *Inbox* de `CONTEXT.md` en el momento. Sobrevive a
  compactaciones de chat y a sesiones que se cortan sin cerrar; al cerrar
  sesión se consolida.
- **Disciplina de contexto** (`SYSTEM.md` §16): buscar antes de leer, leer
  rangos `archivo:línea`, no abrir sesiones viejas, delegar exploración.
- **Reglas propias del proyecto** en `.control/SYSTEM.local.md`: aparecen
  en cada brief y no se pisan con las actualizaciones.

### Integración por agente

| Agente | Cómo recibe el contexto |
|---|---|
| Claude Code | hook `SessionStart` en `.claude/settings.json` inyecta `pctl brief` al iniciar y después de cada compactación; `CLAUDE.md` -> `AGENTS.md` |
| opencode | `opencode.json` carga `SYSTEM.md`; el agente `project-control` corre `pctl brief` |
| Codex, Cursor, otros | leen `AGENTS.md`, que indica correr `pctl brief` |
| Chat sin ejecución | `SYSTEM.md` §11: `CONTEXT.md` + `IN_PROGRESS.md` + handoff de la última sesión |

Si ya tenés tu propio `.claude/settings.json`, agregá este hook:
`{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"python .control/scripts/pctl.py brief"}]}]}}`

## Búsqueda

`pctl search` recorre **todo** `.control/` (tareas, sesiones, arquitectura,
flujos, decisiones, docs, roadmaps, skills, prompts, diagramas y los
archivos raíz como `CONTEXT.md`) y devuelve resultados agrupados por
archivo y ordenados por relevancia (coincidencias en id/título pesan más
que en el cuerpo).

```
pctl search stock redis                 # todas las palabras deben aparecer
pctl search "race condition"            # frase exacta
pctl search checkout --area tasks,flows --estado in_progress
pctl search T-00 --fm                   # solo frontmatter (id, titulo, estado...)
pctl search "def \w+_task" --regex --code   # incluir scripts/ y frontend/
pctl search login --files               # solo rutas, mínimo de tokens
```

## Actualizaciones

```
python .control/scripts/update.py --check     # ¿hay versión nueva? ¿qué cambió?
python .control/scripts/update.py --dry-run   # plan archivo por archivo, sin tocar nada
python .control/scripts/update.py             # aplicar (pregunta una vez)
python .control/scripts/update.py --rollback  # deshacer la última actualización
```

Garantías:

- Solo se tocan archivos listados en `.control/framework.json`. Tareas,
  sesiones, decisiones, docs, roadmaps, `CONTEXT.md`, `PROJECT.md`, skills
  propias y cualquier otro archivo tuyo **nunca** se leen ni se escriben.
- Por cada archivo se comparan tres hashes (tu copia, la instalada, la
  nueva): si no lo tocaste se actualiza; si lo editaste y upstream no
  cambió, queda el tuyo; si ambos cambiaron se hace merge de 3 vías, y si
  hay conflicto **tu archivo queda intacto** y la versión nueva se deja en
  `.control/.update/` para revisar (`--take-upstream <ruta>` o merge a mano,
  y luego `--resolved`).
- Nunca borra nada; los archivos que el framework deja de usar se reportan.
- Backup de todo lo que cambia y `--rollback`.
- El `update.py` más nuevo es el que ejecuta la actualización (bootstrap),
  así las migraciones nuevas siempre corren.
- `pctl brief` avisa cuando hay una **versión publicada** nueva (versión + resumen
  del CHANGELOG) y le indica al agente que **pregunte al usuario** si quiere
  actualizar; nunca actualiza solo. Commits sin versión nueva no generan aviso.
  `pctl update-check --skip` silencia esa versión. Como mucho un `git ls-remote`
  por día (+ una lectura de `framework.json` remoto si hay cambios);
  `PCTL_NO_UPDATE_CHECK=1` lo desactiva.

### Publicar una versión (mantenedores)

1. Agregar la entrada `## vX.Y.Z (fecha)` arriba en `.control/CHANGELOG.md`,
   agrupada con títulos `### ...`: esos títulos forman el resumen de una línea
   que ven los proyectos en el aviso de actualización.
2. Si cambia el formato de datos, agregar una migración en `MIGRATIONS`
   de `update.py` (idempotente, solo toca lo que nombra).
3. `python .control/scripts/update.py --build-manifest --version X.Y.Z`. Además
   del manifiesto, regenera `skills/lean/SKILL.md` (desde `.control/skills/lean.md`)
   y `.github/copilot-instructions.md` (desde `AGENTS.md`), y pone la versión en
   `.claude-plugin/plugin.json`. Esos archivos no se editan a mano.
4. Commit + push a `main`. Los proyectos lo ven en su próximo `pctl brief`
   (como mucho un día después). Un push sin subir la versión no genera aviso.

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
| `brief [--budget N] [--offline]` | contexto completo de inicio de sesión, acotado |
| `context-note "texto" [--tipo]` | guardar un aprendizaje ya en `CONTEXT.md` |
| `search <palabras> [--area] [--estado] [--fm] [--regex] [--files] [--code]` | búsqueda en todo `.control/` |
| `session-current` | id de la sesión abierta |
| `update-check [--skip]` | ¿hay versión nueva del framework? (`--skip`: no volver a avisar de esa versión) |
| `status` | resumen corto del proyecto (incluye flujos desactualizados) |
| `reindex` | regenera BACKLOG/IN_PROGRESS/DONE/arch index/flows index |
| `validate` | valida schema + referencias `archivo:línea` |
| `doc-check-refs` | valida solo referencias de código |
| `session-start [--agente]` / `session-log <id> "texto"` / `session-close <id> "resumen" [--tareas] [--next] [--question]` | bitácora de sesión + handoff |
| `arch-touch <dominio> [--estado] [--crear-archivo]` | registra/crea documentación de un dominio |
| `arch-list` | lista dominios y su estado |
| `flow-new "nombre" --dominios a,b --disparador "..."` | crea un flujo (comportamiento que cruza dominios) |
| `flow-show <id>` / `flow-list [--dominio] [--estado]` / `flow-touch <id> <estado>` | consultar y actualizar flujos |
| `context-show` / `context-write --file <archivo>` / `context-check` | memoria de contexto del agente (`CONTEXT.md`) |
| `skill-propose <nombre> --tipo --disparador --ubicacion` | propone skill/script nuevo (no lo activa) |
| `skill-promote <id>` | activa una skill propuesta (requiere confirmación humana) |
| `skill-list [--estado]` | lista skills registradas |
| `lean [off\|lite\|full\|strict]` | ver o cambiar el nivel de lean mode (`skills/lean.md`) |
| `reuse <palabras> [--limit N]` | qué ya existe: docs, definiciones en el código, dependencias instaladas |
| `deps-check [--base REF]` | dependencias nuevas en manifests (package.json, requirements, pyproject, Cargo, go.mod...) |
| `debt-scan [--marker M] [--apply]` | comentarios `shortcut:` en el código -> tareas de deuda en backlog |
| `dupes [rutas] [--changed]` | funciones con el mismo nombre y bloques copiados (candidatos a utilidad compartida) |
| `review-context [--base REF]` | qué leer fuera del diff: docs que apuntan a las líneas cambiadas, usos, duplicados, deps |
| `audit-plan [rutas]` | orden para auditar el repo: entry points, hotspots, archivos grandes, duplicación |

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

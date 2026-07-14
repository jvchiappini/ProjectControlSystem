# Schema — contrato de frontmatter

Referencia exacta que implementa `validate.py`. Si un agente edita
markdown a mano (sin `pctl`), debe respetar esto al carácter.

## Tarea (tasks/**/T-XXXX.md o T-PREFIJO-XXXX.md)

```
id: T-0045
titulo: string
estado: backlog | in_progress | blocked | done
prioridad: baja | media | alta | critica
tipo: feature | bug | refactor | investigacion | chore
creado_por: usuario | agente
asignado_a: usuario | agente | ambos
creado: YYYY-MM-DD
actualizado: YYYY-MM-DD
depende_de: []              # lista de ids
bloqueado_por: null          # string, obligatorio si estado=blocked
version_schema: 1
```

## Sesión (sessions/*.md)

```
id: S-YYYY-MM-DD-NNN
fecha: YYYY-MM-DD
agente: string
tareas_tocadas: []
resumen: string
version_schema: 1
```

## Decisión / ADR (decisions/D-XXXX.md)

```
id: D-0012
titulo: string
fecha: YYYY-MM-DD
estado: propuesta | aceptada | rechazada | reemplazada
reemplaza: []
version_schema: 1
```

## Skill/Script (skills/_index.md, una fila por entrada)

```
id: SK-0007
nombre: string
tipo: skill | script
estado: propuesta | activa | deprecada
disparador: string
ubicacion: string
creado_por: usuario | agente
version: 1
```

## Flujo (flows/F-XXXX.md)

```
id: F-0001
nombre: string
estado: borrador | vigente | desactualizado
dominios: []                 # lista de nombres de dominio que cruza
disparador: string            # que activa este comportamiento
creado: YYYY-MM-DD
actualizado: YYYY-MM-DD
version_schema: 1
```
Cuerpo con secciones fijas: `## Resumen`, `## Pasos` (numerados, cada
uno con referencia `archivo:línea`), `## Diagrama`,
`## Dominios relacionados`, `## Notas de mantenimiento`.

## Memoria de contexto (CONTEXT.md, único archivo en la raíz de .control/)

```
actualizado: YYYY-MM-DD
actualizado_por: agente | usuario
version_schema: 1
```
Cuerpo libre pero con secciones fijas sugeridas por el template
(`CONTEXT.md.template`). Se reescribe completo, nunca se apendea.
Presupuesto de tamaño: ~120 líneas de cuerpo (`pctl context-check`).

## Máquina de estados de tareas

Ver `.control/SYSTEM.md` sección 4. `validate.py` y `tasks.py` la
implementan como una tabla de transiciones permitidas — no editar esa
tabla sin actualizar `SYSTEM.md` también.

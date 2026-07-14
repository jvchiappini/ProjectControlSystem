# Skill: doc-concise

Disparador: post-edicion de cualquier `.md` dentro de `.control/` (architecture, flows, decisions, tasks), o al ejecutar `pctl doc-update`.

## Regla

No hay límite fijo de líneas. La validación es de **densidad de referencias**:

> Una seccion en un `.md` de `.control/` no deberia tener mas de 3 parrafos consecutivos sin al menos una referencia `archivo:linea`.

Si una seccion es pura prosa sin apuntar a codigo, es candidata a poda.

## Procedimiento

1. Despues de escribir o modificar cualquier `.md` en `.control/`, parsear secciones.
2. Por cada seccion, contar parrafos (separados por doble salto de linea).
3. Si hay 3+ parrafos seguidos sin ninguna `archivo:linea`, marcar la seccion.
4. Para cada seccion marcada, sugerir poda: convertir prosa en referencias, o mover el contenido a un flujo si describe comportamiento que cruza dominios.
5. No podar automaticamente — solo marcar y sugerir. La decision final es del usuario.

## Output

Lista de secciones candidatas a poda, con la sugerencia concreta de que hacer (convertir a referencia, mover a flujo, o eliminar).

## Ejemplo

```
architecture/stock.md — seccion "Detalle de implementacion":
  4 parrafos sin referencias.
  Sugerencia: reemplazar con referencias a `src/stock/validator.py:10-45`
  y `src/stock/reserve.py:22-30`.
```

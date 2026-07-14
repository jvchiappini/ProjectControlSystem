# Skill: test-gap

Disparador: `pctl task-move <id> done` (o su equivalente en frontend) sin que la tarea sea tipo `docs` o `chore`.

## Procedimiento

1. **Verificar tipo de tarea** — si es `docs` o `chore`, saltar el chequeo.
2. **Buscar tests existentes** — revisar si hay archivos de test para los mismos archivos que tocó la tarea (convencion: `test_*.py`, `*.test.ts`, `*.spec.ts`, `__tests__/`, etc).
3. **Si hay tests** — verificar que al menos un test nuevo cubre el cambio. `git diff --stat` ayuda a ver si se tocaron archivos de test.
4. **Si no hay tests** — preguntar al usuario antes de permitir el `task-move done`:
   > "Esta tarea no tiene tests. ¿Crear subtarea de testing en backlog o proceder sin tests?"
5. **Si el usuario opta por tests** — crear tarea tipo `chore` en backlog con titulo "Tests para [titulo de tarea original]" y `depende_de` apuntando a la tarea original.

## Output

- Si hay tests: permiso para mover a `done`.
- Si no hay tests y usuario accede: tarea de testing creada en backlog.
- Si no hay tests y usuario no accede: se permite el move igual pero se loguea en la sesion: "T-XXXX pasó a done sin tests".

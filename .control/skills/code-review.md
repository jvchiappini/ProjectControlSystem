# Skill: code-review

Disparador: antes de `git-commit --yes`, o cuando el usuario pide revision explicita.

## Checklist

1. **Sin secrets** — revisar que no haya tokens, passwords, keys hardcodeadas (.gitignore, .env, .env.* deberian estar en .gitignore).
2. **Sin dead code** — imports sin uso, variables asignadas y no leidas, funciones que no se llaman.
3. **Errores manejados** — try/except sin `pass` silencioso, excepciones especificas no `Exception` generico.
4. **Sigue conventions del proyecto** — naming, estructura de carpetas, patrones del codigo vecino.
5. **Sin cambios fuera de alcance** — el diff debe tocar solo lo necesario para la tarea. Si hay formateo o refactor accidental, separarlo.
6. **Logs sin datos sensibles** — no loguear request bodies completos, tokens, passwords.
7. **Referencias documentales actualizadas** — si se movio o renombro un archivo, actualizar las referencias `archivo:linea` en `.control/`.

## Output

Si encuentra issues, listarlos como bullets ANTES de permitir el commit. Si no encuentra issues, output minimo: "ok".

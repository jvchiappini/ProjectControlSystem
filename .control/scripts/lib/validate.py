import re

from . import fm, paths

REQUIRED_TASK_FIELDS = [
    "id", "titulo", "estado", "prioridad", "tipo", "creado_por",
    "asignado_a", "creado", "actualizado", "version_schema",
]


def validate_all():
    errores = []
    errores += _validate_tasks()
    errores += _validate_refs()
    return errores


def _validate_tasks(dominio_dir=None):
    errores = []
    ids_vistos = {}
    for f in sorted(paths.TASKS_DIR.rglob("T-*.md")):
        data, body = fm.parse(f.read_text(encoding="utf-8"))
        for campo in REQUIRED_TASK_FIELDS:
            if campo not in data or data[campo] in (None, ""):
                if campo == "bloqueado_por":
                    continue
                errores.append(f"{f}: falta campo obligatorio '{campo}'")
        if data.get("estado") not in paths.TASK_STATES:
            errores.append(f"{f}: estado invalido '{data.get('estado')}'")
        if data.get("prioridad") not in paths.TASK_PRIORITIES:
            errores.append(f"{f}: prioridad invalida '{data.get('prioridad')}'")
        if data.get("estado") == "blocked" and not data.get("bloqueado_por"):
            errores.append(f"{f}: estado blocked sin 'bloqueado_por'")
        tid = data.get("id")
        if tid in ids_vistos:
            errores.append(f"{f}: id duplicado '{tid}' (tambien en {ids_vistos[tid]})")
        else:
            ids_vistos[tid] = f
    return errores


_REF_PATTERN = re.compile(r"`([\w./-]+):(\d+)(?:-(\d+))?`")


def _validate_refs():
    """Chequea que los archivos referenciados con `archivo:linea` existan
    y que el numero de linea este dentro del rango del archivo. No
    valida contenido semantico, solo integridad basica (doc-drift)."""
    errores = []
    project_root = paths.CONTROL_ROOT.parent
    md_files = (
        list(paths.ARCH_DIR.rglob("*.md"))
        + list(paths.TASKS_DIR.rglob("*.md"))
        + list((paths.CONTROL_ROOT / "flows").rglob("*.md"))
    )
    for md in md_files:
        text = md.read_text(encoding="utf-8")
        for m in _REF_PATTERN.finditer(text):
            ref_path, l1, l2 = m.group(1), int(m.group(2)), m.group(3)
            target = project_root / ref_path
            if not target.exists():
                errores.append(f"{md}: referencia rota, no existe '{ref_path}'")
                continue
            try:
                n_lines = sum(1 for _ in target.open(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            max_line = int(l2) if l2 else l1
            if max_line > n_lines:
                errores.append(
                    f"{md}: referencia '{ref_path}:{l1}"
                    + (f"-{l2}" if l2 else "")
                    + f"' fuera de rango (archivo tiene {n_lines} lineas)"
                )
    return errores

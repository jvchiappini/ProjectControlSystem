import datetime
import re

from . import fm, paths

TASK_KEY_ORDER = [
    "id", "titulo", "estado", "prioridad", "tipo", "creado_por",
    "asignado_a", "creado", "actualizado", "depende_de",
    "bloqueado_por", "version_schema",
]


def _today():
    return datetime.date.today().isoformat()


def _all_task_files():
    return sorted(paths.TASKS_DIR.rglob("T-*.md"))


def _next_id(prefix=None):
    max_n = 0
    pattern = re.compile(
        rf"^T-{prefix + '-' if prefix else ''}(\d+)$"
    )
    for f in _all_task_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        tid = data.get("id", "")
        m = pattern.match(tid)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def new_task(titulo, prioridad="media", tipo="feature", creado_por="usuario",
             asignado_a="agente", prefix=None, dominio=None):
    if prioridad not in paths.TASK_PRIORITIES:
        raise ValueError(f"prioridad invalida: {prioridad}")
    if tipo not in paths.TASK_TYPES:
        raise ValueError(f"tipo invalido: {tipo}")

    n = _next_id(prefix)
    tid = f"T-{prefix + '-' if prefix else ''}{n:04d}"
    today = _today()
    data = {
        "id": tid,
        "titulo": titulo,
        "estado": "backlog",
        "prioridad": prioridad,
        "tipo": tipo,
        "creado_por": creado_por,
        "asignado_a": asignado_a,
        "creado": today,
        "actualizado": today,
        "depende_de": [],
        "bloqueado_por": None,
        "version_schema": 1,
    }
    body = (
        "\n## Contexto\n\n(completar)\n\n"
        "## Criterios de aceptacion\n- [ ] \n\n"
        "## Notas del agente\n\n"
    )
    target_dir = paths.TASKS_DIR / dominio if dominio else paths.TASKS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    fpath = target_dir / f"{tid}.md"
    fpath.write_text(fm.dump(data, body, TASK_KEY_ORDER), encoding="utf-8")
    return tid, fpath


def _find_task_file(tid):
    for f in _all_task_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if data.get("id") == tid:
            return f, data
    raise FileNotFoundError(f"tarea no encontrada: {tid}")


def move_task(tid, nuevo_estado, motivo=None, force=False):
    if nuevo_estado not in paths.TASK_STATES:
        raise ValueError(f"estado invalido: {nuevo_estado}")
    fpath, data = _find_task_file(tid)
    text = fpath.read_text(encoding="utf-8")
    _, body = fm.parse(text)
    actual = data.get("estado")

    if nuevo_estado != actual:
        permitidos = paths.VALID_TRANSITIONS.get(actual, set())
        if nuevo_estado not in permitidos:
            raise ValueError(
                f"transicion no permitida: {actual} -> {nuevo_estado}"
            )

    if nuevo_estado == "blocked" and not motivo:
        raise ValueError("mover a 'blocked' requiere --motivo")

    if nuevo_estado == "done" and not force:
        pendientes = re.findall(r"- \[ \]", body)
        if pendientes:
            raise ValueError(
                "hay criterios de aceptacion sin marcar; usa --force 'motivo'"
            )

    nota = ""
    if actual == "done" and nuevo_estado == "in_progress":
        nota = (
            f"\n> reabierta el {_today()}"
            + (f", motivo: {motivo}" if motivo else "")
            + "\n"
        )
    if nuevo_estado == "blocked":
        data["bloqueado_por"] = motivo
    if actual == "blocked" and nuevo_estado != "blocked":
        data["bloqueado_por"] = None
    if nuevo_estado == "done" and force and motivo:
        nota = f"\n> completada con --force el {_today()}, motivo: {motivo}\n"

    data["estado"] = nuevo_estado
    data["actualizado"] = _today()
    fpath.write_text(
        fm.dump(data, body + nota, TASK_KEY_ORDER), encoding="utf-8"
    )
    return actual, nuevo_estado


def show_task(tid):
    fpath, _ = _find_task_file(tid)
    return fpath.read_text(encoding="utf-8")


def set_body(tid, new_body):
    fpath, data = _find_task_file(tid)
    data["actualizado"] = _today()
    fpath.write_text(fm.dump(data, new_body, TASK_KEY_ORDER), encoding="utf-8")


def get_full(tid):
    """Devuelve frontmatter + secciones parseadas para consumo del frontend."""
    from . import sections as sec
    fpath, data = _find_task_file(tid)
    _, body = fm.parse(fpath.read_text(encoding="utf-8"))
    secs = sec.split_sections(body)
    return {
        "data": data,
        "contexto": secs.get("Contexto", ""),
        "criterios": sec.parse_checkboxes(secs.get("Criterios de aceptacion", secs.get("Criterios de aceptación", ""))),
        "notas": secs.get("Notas del agente", ""),
    }


def list_tasks(estado=None):
    out = []
    for f in _all_task_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if estado and data.get("estado") != estado:
            continue
        out.append(data)
    out.sort(key=lambda d: (
        {"critica": 0, "alta": 1, "media": 2, "baja": 3}.get(d.get("prioridad"), 9),
        d.get("id", ""),
    ))
    return out

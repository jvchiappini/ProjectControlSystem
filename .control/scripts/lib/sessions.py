import datetime

from . import fm, paths

SESSION_KEY_ORDER = ["id", "fecha", "agente", "tareas_tocadas", "resumen", "version_schema"]


def _today():
    return datetime.date.today().isoformat()


def _next_seq_today():
    today = _today()
    n = 0
    for f in paths.SESSIONS_DIR.glob(f"S-{today}-*.md"):
        n += 1
    return n + 1


def start_session(agente="agente"):
    paths.ensure_dirs()
    today = _today()
    seq = _next_seq_today()
    sid = f"S-{today}-{seq:03d}"
    data = {
        "id": sid,
        "fecha": today,
        "agente": agente,
        "tareas_tocadas": [],
        "resumen": "(sesion en curso)",
        "version_schema": 1,
    }
    body = "\n## Eventos\n\n"
    fpath = paths.SESSIONS_DIR / f"{sid}.md"
    fpath.write_text(fm.dump(data, body, SESSION_KEY_ORDER), encoding="utf-8")
    return sid, fpath


def log_event(sid, texto):
    fpath = paths.SESSIONS_DIR / f"{sid}.md"
    data, body = fm.parse(fpath.read_text(encoding="utf-8"))
    body += f"- {datetime.datetime.now().strftime('%H:%M')} — {texto}\n"
    fpath.write_text(fm.dump(data, body, SESSION_KEY_ORDER), encoding="utf-8")


def summarize(sid):
    """Extrae solo las decisiones y referencias de una sesion para CONTEXT.md.
    Busca lineas con 'decidio', 'cambio', 'creo', `archivo:linea`."""
    import re
    fpath = paths.SESSIONS_DIR / f"{sid}.md"
    if not fpath.exists():
        raise FileNotFoundError(f"sesion no encontrada: {sid}")
    data, body = fm.parse(fpath.read_text(encoding="utf-8"))

    ref_pat = re.compile(r"`([\w./-]+:\d+(?:-\d+)?)`")
    signal_pat = re.compile(r"(decidio|creo|cambio|elimino|refactorizo|documento)", re.IGNORECASE)

    refs = []
    acciones = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if ref_pat.search(line):
            refs.append(line)
        if signal_pat.match(line.lstrip("- ").lstrip()):
            acciones.append(line)

    return {
        "id": sid,
        "fecha": data.get("fecha", ""),
        "resumen": data.get("resumen", ""),
        "tareas": data.get("tareas_tocadas", []),
        "acciones": acciones,
        "referencias": refs,
    }


def close_session(sid, resumen, tareas_tocadas=None):
    fpath = paths.SESSIONS_DIR / f"{sid}.md"
    data, body = fm.parse(fpath.read_text(encoding="utf-8"))
    data["resumen"] = resumen
    if tareas_tocadas:
        data["tareas_tocadas"] = tareas_tocadas
    fpath.write_text(fm.dump(data, body, SESSION_KEY_ORDER), encoding="utf-8")
    return fpath

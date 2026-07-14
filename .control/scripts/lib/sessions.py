import datetime

from . import atomic, fm, paths, event_log
from .lock import FileLock

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
    with FileLock():
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
        atomic.write(fpath, fm.dump(data, body, SESSION_KEY_ORDER))
        event_log.log("session-started", sid, {"agente": agente})
        return sid, fpath


def log_event(sid, texto):
    with FileLock():
        fpath = paths.SESSIONS_DIR / f"{sid}.md"
        data, body = fm.parse(fpath.read_text(encoding="utf-8"))
        body += f"- {datetime.datetime.now().strftime('%H:%M')} — {texto}\n"
        atomic.write(fpath, fm.dump(data, body, SESSION_KEY_ORDER))
        event_log.log("session-event", sid, {"texto": texto})


def summarize(sid):
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
    with FileLock():
        fpath = paths.SESSIONS_DIR / f"{sid}.md"
        data, body = fm.parse(fpath.read_text(encoding="utf-8"))
        data["resumen"] = resumen
        if tareas_tocadas:
            data["tareas_tocadas"] = tareas_tocadas
        atomic.write(fpath, fm.dump(data, body, SESSION_KEY_ORDER))
        event_log.log("session-closed", sid, {"resumen": resumen})


def list_sessions(limit=50):
    out = []
    for f in sorted(paths.SESSIONS_DIR.glob("S-*.md"), reverse=True)[:limit]:
        data, body = fm.parse(f.read_text(encoding="utf-8"))
        out.append({"data": data, "body": body[:500]})
    return out


def get_full(sid):
    fpath = paths.SESSIONS_DIR / f"{sid}.md"
    if not fpath.exists():
        raise FileNotFoundError(f"sesion no encontrada: {sid}")
    data, body = fm.parse(fpath.read_text(encoding="utf-8"))
    return {"data": data, "body": body}

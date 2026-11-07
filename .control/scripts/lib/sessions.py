import datetime

from . import atomic, event_log, fm, paths, util
from .lock import FileLock

OPEN_MARKER = "(sesion en curso)"
HANDOFF_HEADING = "## Handoff"

SESSION_KEY_ORDER = ["id", "fecha", "agente", "tareas_tocadas", "resumen", "version_schema"]


def _next_seq_today():
    today = util.today()
    n = 0
    for f in paths.SESSIONS_DIR.glob(f"S-{today}-*.md"):
        n += 1
    return n + 1


def start_session(agente="agente"):
    with FileLock():
        paths.ensure_dirs()
        today = util.today()
        seq = _next_seq_today()
        sid = f"S-{today}-{seq:03d}"
        data = {
            "id": sid,
            "fecha": today,
            "agente": agente,
            "tareas_tocadas": [],
            "resumen": OPEN_MARKER,
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


def _handoff_block(siguiente, pendientes):
    """Structured handoff for the next session (read back by `pctl brief`)."""
    if not siguiente and not pendientes:
        return ""
    out = ["", HANDOFF_HEADING, ""]
    if siguiente:
        out.append("### Next steps")
        out += [f"- {x.strip()}" for x in siguiente if x.strip()]
        out.append("")
    if pendientes:
        out.append("### Open questions")
        out += [f"- {x.strip()}" for x in pendientes if x.strip()]
        out.append("")
    return "\n".join(out) + "\n"


def close_session(sid, resumen, tareas_tocadas=None, siguiente=None, pendientes=None):
    with FileLock():
        fpath = paths.SESSIONS_DIR / f"{sid}.md"
        if not fpath.exists():
            raise FileNotFoundError(f"sesion no encontrada: {sid}")
        data, body = fm.parse(fpath.read_text(encoding="utf-8"))
        data["resumen"] = resumen
        if tareas_tocadas:
            data["tareas_tocadas"] = tareas_tocadas
        if HANDOFF_HEADING in body:
            body = body.split("\n" + HANDOFF_HEADING)[0].rstrip("\n") + "\n"
        body += _handoff_block(siguiente or [], pendientes or [])
        atomic.write(fpath, fm.dump(data, body, SESSION_KEY_ORDER))
        event_log.log("session-closed", sid, {"resumen": resumen})
        return fpath


def is_open(data):
    return (data.get("resumen") or "") == OPEN_MARKER


def open_sessions():
    """Sessions started but never closed (newest first)."""
    out = []
    for f in sorted(paths.SESSIONS_DIR.glob("S-*.md"), reverse=True):
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if is_open(data):
            out.append(data.get("id") or f.stem)
    return out


def last_closed():
    """Most recent closed session: {"data", "next", "questions"} or None."""
    for f in sorted(paths.SESSIONS_DIR.glob("S-*.md"), reverse=True):
        data, body = fm.parse(f.read_text(encoding="utf-8"))
        if is_open(data):
            continue
        return {"data": data, **parse_handoff(body)}
    return None


def parse_handoff(body):
    nxt, qs, cur = [], [], None
    if HANDOFF_HEADING not in body:
        return {"next": nxt, "questions": qs}
    for line in body.split(HANDOFF_HEADING, 1)[1].splitlines():
        st = line.strip()
        if st.startswith("## "):
            break
        if st.lower().startswith("### next"):
            cur = nxt
        elif st.lower().startswith("### open"):
            cur = qs
        elif st.startswith("- ") and cur is not None:
            cur.append(st[2:])
    return {"next": nxt, "questions": qs}


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

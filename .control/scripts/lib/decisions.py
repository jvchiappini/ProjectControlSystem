import datetime
import re

from . import atomic, fm, paths, event_log
from .lock import FileLock

DECISION_KEY_ORDER = ["id", "titulo", "fecha", "estado", "reemplaza", "version_schema"]
ESTADOS = ["propuesta", "aceptada", "rechazada", "reemplazada"]

_TEMPLATE_BODY = """
## Contexto
(que problema forzo esta decision)

## Decision
(que se eligio, en una afirmacion clara)

## Consecuencias
(que se gana, que se pierde, que queda pendiente de revisar)
"""


def _today():
    return datetime.date.today().isoformat()


def _all_files():
    paths.DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(paths.DECISIONS_DIR.glob("D-*.md"))


def _next_id():
    max_n = 0
    for f in _all_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        m = re.match(r"^D-(\d+)$", data.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def new_decision(titulo, estado="aceptada", reemplaza=None):
    with FileLock():
        if estado not in ESTADOS:
            raise ValueError(f"estado invalido: {estado}")
        n = _next_id()
        did = f"D-{n:04d}"
        data = {
            "id": did, "titulo": titulo, "fecha": _today(), "estado": estado,
            "reemplaza": reemplaza or [], "version_schema": 1,
        }
        fpath = paths.DECISIONS_DIR / f"{did}.md"
        atomic.write_with_backup(fpath, fm.dump(data, _TEMPLATE_BODY, DECISION_KEY_ORDER))
        if reemplaza:
            for old_id in reemplaza:
                try:
                    _set_estado(old_id, "reemplazada")
                except FileNotFoundError:
                    pass
        event_log.log("decision-created", did, {"titulo": titulo, "estado": estado})
        return did, fpath


def _find(did):
    for f in _all_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if data.get("id") == did:
            return f, data
    raise FileNotFoundError(f"decision no encontrada: {did}")


def _set_estado(did, estado):
    fpath, data = _find(did)
    _, body = fm.parse(fpath.read_text(encoding="utf-8"))
    data["estado"] = estado
    atomic.write_with_backup(fpath, fm.dump(data, body, DECISION_KEY_ORDER))


def show(did):
    fpath, _ = _find(did)
    return fpath.read_text(encoding="utf-8")


def set_body(did, body):
    with FileLock():
        fpath, data = _find(did)
        atomic.write_with_backup(fpath, fm.dump(data, body, DECISION_KEY_ORDER))
        event_log.log("decision-body-edited", did)


def list_decisions(estado=None):
    out = []
    for f in _all_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if estado and data.get("estado") != estado:
            continue
        out.append(data)
    out.sort(key=lambda d: d.get("id", ""))
    return out

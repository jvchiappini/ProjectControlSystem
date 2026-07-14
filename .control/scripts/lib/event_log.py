"""Log de eventos persistente para SSE y coordinación entre procesos.

Cada operación de escritura apendea una línea NDJSON en
.control/.events.ndjson. El servidor SSE lee este archivo para enviar
eventos en tiempo real al frontend. pctl también lo escribe, así el
frontend se entera de cambios hechos desde el CLI.
"""
import datetime
import json
import os

from . import atomic, paths

EVENT_LOG = paths.CONTROL_ROOT / ".events.ndjson"

_MAX_EVENTS = 10000
_TRIM_FRAC = 2
_CACHE = []
_LAST_KNOWN_SIZE = 0


def log(event_type, entity_id=None, data=None):
    """Apendea un evento al log. Thread-safe vía lock."""
    entry = {
        "ts": datetime.datetime.now().isoformat(),
        "type": event_type,
        "id": entity_id,
        "data": data or {},
    }
    _CACHE.append(entry)
    _flush()


def _flush():
    try:
        entries = _CACHE[:]
        _CACHE.clear()
        content = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"
        with open(str(EVENT_LOG), "a", encoding="utf-8") as f:
            f.write(content)
    except OSError:
        pass
    _maybe_trim()


def _maybe_trim():
    if not EVENT_LOG.exists():
        return
    try:
        sz = EVENT_LOG.stat().st_size
        if sz < 50 * 1024:
            return
        lines = EVENT_LOG.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            keep = lines[-_MAX_EVENTS // _TRIM_FRAC:]
            EVENT_LOG.write_text("\n".join(keep) + "\n", encoding="utf-8")
    except OSError:
        pass


def read_since(last_pos=0):
    """Devuelve (nuevos_eventos, nueva_posición) desde last_pos en adelante."""
    if not EVENT_LOG.exists():
        return [], 0
    try:
        current_size = EVENT_LOG.stat().st_size
        if current_size == last_pos:
            return [], last_pos
        with open(str(EVENT_LOG), "r", encoding="utf-8") as f:
            f.seek(last_pos)
            content = f.read()
            new_pos = f.tell()
        if not content.strip():
            return [], new_pos
        lines = [l for l in content.splitlines() if l.strip()]
        events = []
        for l in lines:
            try:
                events.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return events, new_pos
    except OSError:
        return [], 0

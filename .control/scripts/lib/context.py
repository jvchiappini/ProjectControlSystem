import datetime

from . import atomic, fm, paths

CONTEXT_MD = paths.CONTROL_ROOT / "CONTEXT.md"
CONTEXT_KEY_ORDER = ["actualizado", "actualizado_por", "version_schema"]
MAX_BODY_LINES = 120


def _today():
    return datetime.date.today().isoformat()


def read():
    if not CONTEXT_MD.exists():
        return {}, ""
    return fm.parse(CONTEXT_MD.read_text(encoding="utf-8"))


def write(body, actualizado_por="agente"):
    data = {
        "actualizado": _today(),
        "actualizado_por": actualizado_por,
        "version_schema": 1,
    }
    atomic.write_with_backup(CONTEXT_MD, fm.dump(data, body, CONTEXT_KEY_ORDER))


def check_budget():
    if not CONTEXT_MD.exists():
        return None
    _, body = fm.parse(CONTEXT_MD.read_text(encoding="utf-8"))
    n = len([l for l in body.splitlines() if l.strip()])
    if n > MAX_BODY_LINES:
        return (
            f"CONTEXT.md tiene {n} lineas no vacias (limite sugerido "
            f"{MAX_BODY_LINES}). Promover lo estable a PROJECT.md, "
            f"architecture/ o decisions/, y podar el resto."
        )
    return None

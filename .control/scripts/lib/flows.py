import datetime
import re

from . import atomic, fm, paths, event_log
from .lock import FileLock
from .indexes import reindex as _reindex_tasks

FLOW_KEY_ORDER = [
    "id", "nombre", "estado", "dominios", "disparador", "padre",
    "creado", "actualizado", "version_schema",
]

ESTADOS = ["borrador", "vigente", "desactualizado"]

_TEMPLATE_BODY = """
## Resumen
(1-2 lineas: que hace este flujo de principio a fin)

## Pasos
1. (que pasa) — `ruta/archivo:linea-linea`
2. (que pasa) — `ruta/archivo:linea-linea`

## Diagrama
(referencia opcional a diagrams/flows/{fid}.mmd, secuencia)

## Dominios relacionados
{dominios_lista}

## Notas de mantenimiento
(cuando revisar este flujo de nuevo: ej. si cambia el sistema de input)
"""


def _today():
    return datetime.date.today().isoformat()


def _all_flow_files():
    paths.FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(paths.FLOWS_DIR.glob("F-*.md"))


def _next_id():
    max_n = 0
    for f in _all_flow_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        m = re.match(r"^F-(\d+)$", data.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def new_flow(nombre, dominios=None, disparador="", padre=None):
    with FileLock():
        dominios = dominios or []
        n = _next_id()
        fid = f"F-{n:04d}"
        today = _today()
        data = {
            "id": fid, "nombre": nombre, "estado": "borrador",
            "dominios": dominios, "disparador": disparador, "padre": padre,
            "creado": today, "actualizado": today, "version_schema": 1,
        }
        dominios_lista = "\n".join(f"- {d}" for d in dominios) or "- (completar)"
        body = _TEMPLATE_BODY.format(fid=fid, dominios_lista=dominios_lista)
        fpath = paths.FLOWS_DIR / f"{fid}.md"
        atomic.write_with_backup(fpath, fm.dump(data, body, FLOW_KEY_ORDER))
        reindex()
        event_log.log("flow-created", fid, {"nombre": nombre})
        return fid, fpath


def _find_flow_file(fid):
    for f in _all_flow_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if data.get("id") == fid:
            return f, data
    raise FileNotFoundError(f"flujo no encontrado: {fid}")


def show_flow(fid):
    fpath, _ = _find_flow_file(fid)
    return fpath.read_text(encoding="utf-8")


def get_data(fid):
    _, data = _find_flow_file(fid)
    return data


def set_body(fid, new_body):
    with FileLock():
        fpath, data = _find_flow_file(fid)
        data["actualizado"] = _today()
        atomic.write_with_backup(fpath, fm.dump(data, new_body, FLOW_KEY_ORDER))
        event_log.log("flow-body-edited", fid)


def touch_estado(fid, estado):
    with FileLock():
        if estado not in ESTADOS:
            raise ValueError(f"estado invalido: {estado}")
        fpath, data = _find_flow_file(fid)
        _, body = fm.parse(fpath.read_text(encoding="utf-8"))
        data["estado"] = estado
        data["actualizado"] = _today()
        atomic.write_with_backup(fpath, fm.dump(data, body, FLOW_KEY_ORDER))
        reindex()
        event_log.log("flow-status-changed", fid, {"estado": estado})
        return data


def _read_index_rows():
    if not paths.FLOWS_INDEX_MD.exists():
        return {}
    rows = {}
    for line in paths.FLOWS_INDEX_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("| Flujo") and not line.startswith("|---"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 4:
                rows[parts[0]] = {
                    "estado": parts[1], "dominios": parts[2], "disparador": parts[3],
                }
    return rows


def reindex():
    paths.ensure_dirs()
    rows = {}
    for f in _all_flow_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        fid = data.get("id", "")
        if fid:
            rows[fid] = {
                "estado": data.get("estado", "borrador"),
                "dominios": ", ".join(data.get("dominios") or []),
                "disparador": data.get("disparador", ""),
            }
    lines = [
        "# Indice de flujos",
        "",
        "(generado por `pctl reindex` — no editar a mano)",
        "",
        "| Flujo | Estado | Dominios | Disparador |",
        "|---|---|---|---|",
    ]
    for fid in sorted(rows):
        r = rows[fid]
        lines.append(f"| {fid} | {r['estado']} | {r['dominios']} | {r['disparador']} |")
    atomic.write(paths.FLOWS_INDEX_MD, "\n".join(lines) + "\n")


def list_flows(dominio=None, estado=None, padre="__any__"):
    out = []
    for f in _all_flow_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if dominio and dominio not in (data.get("dominios") or []):
            continue
        if estado and data.get("estado") != estado:
            continue
        if padre == "__any__":
            pass  # todos
        elif padre is None and data.get("padre"):
            continue
        elif padre is not None and data.get("padre") != padre:
            continue
        out.append(data)
    return out


def tree(fid, indent=0, visited=None, max_depth=5):
    if visited is None:
        visited = set()
    if fid in visited or indent > max_depth:
        return ""
    visited.add(fid)
    result = []
    prefix = "  " * indent
    try:
        data = get_data(fid)
    except FileNotFoundError:
        return prefix + f"! flujo no encontrado: {fid}\n"
    line = f"{prefix}{fid} — {data.get('nombre', '?')} [{data.get('estado', '?')}]\n"
    result.append(line)
    hijos = list_flows(padre=fid)
    for h in hijos:
        result.append(tree(h.get("id"), indent + 1, visited, max_depth))
    return "".join(result)

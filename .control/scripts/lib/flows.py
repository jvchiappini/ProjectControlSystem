import datetime
import re

from . import fm, paths

FLOW_KEY_ORDER = [
    "id", "nombre", "estado", "dominios", "disparador", "padre",
    "creado", "actualizado", "version_schema",
]

ESTADOS = ["borrador", "vigente", "desactualizado"]

FLOWS_DIR = paths.CONTROL_ROOT / "flows"
FLOWS_INDEX_MD = FLOWS_DIR / "_index.md"

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


def _ensure_dirs():
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)


def _all_flow_files():
    _ensure_dirs()
    return sorted(FLOWS_DIR.glob("F-*.md"))


def _next_id():
    max_n = 0
    for f in _all_flow_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        m = re.match(r"^F-(\d+)$", data.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def new_flow(nombre, dominios=None, disparador="", padre=None):
    _ensure_dirs()
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
    fpath = FLOWS_DIR / f"{fid}.md"
    fpath.write_text(fm.dump(data, body, FLOW_KEY_ORDER), encoding="utf-8")
    _reindex()
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
    fpath, data = _find_flow_file(fid)
    data["actualizado"] = _today()
    fpath.write_text(fm.dump(data, new_body, FLOW_KEY_ORDER), encoding="utf-8")


def touch_estado(fid, estado):
    if estado not in ESTADOS:
        raise ValueError(f"estado invalido: {estado}")
    fpath, data = _find_flow_file(fid)
    _, body = fm.parse(fpath.read_text(encoding="utf-8"))
    data["estado"] = estado
    data["actualizado"] = _today()
    fpath.write_text(fm.dump(data, body, FLOW_KEY_ORDER), encoding="utf-8")
    _reindex()
    return data


def list_flows(dominio=None, estado=None, padre="__any__"):
    out = []
    for f in _all_flow_files():
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if dominio and dominio not in (data.get("dominios") or []):
            continue
        if estado and data.get("estado") != estado:
            continue
        if padre != "__any__" and data.get("padre") != padre:
            continue
        out.append(data)
    out.sort(key=lambda d: d.get("id", ""))
    return out


def _reindex():
    _ensure_dirs()
    lines = [
        "# Indice de flujos", "",
        "(generado por pctl -- no editar a mano)", "",
        "| id | nombre | estado | dominios | disparador |",
        "|---|---|---|---|---|",
    ]
    for d in list_flows():
        dominios = ", ".join(d.get("dominios") or [])
        lines.append(
            f"| {d['id']} | {d['nombre']} | {d['estado']} | {dominios} | {d.get('disparador','')} |"
        )
    FLOWS_INDEX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def reindex():
    _reindex()

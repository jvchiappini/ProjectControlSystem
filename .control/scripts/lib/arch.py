import datetime

from . import paths

ESTADOS = ["sin_documentar", "parcial", "documentado"]

_DOMAIN_TEMPLATE = """# Dominio: {dominio}

## Proposito
(completar)

## Componentes clave
- Nombre — que hace, donde vive: `ruta/archivo:linea-linea`

## Diagrama
(agregar referencia a diagrams/{dominio}.mmd si aplica)

## Decisiones relevantes
- 

## Estado de documentacion
parcial — ultima verificacion: {fecha}
"""


def _today():
    return datetime.date.today().isoformat()


def _read_index_rows():
    paths.ARCH_INDEX_MD.parent.mkdir(parents=True, exist_ok=True)
    if not paths.ARCH_INDEX_MD.exists():
        return {}
    rows = {}
    for line in paths.ARCH_INDEX_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("| Dominio") and not line.startswith("|---"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 4:
                rows[parts[0]] = {
                    "estado": parts[1], "actualizado": parts[2], "archivo": parts[3]
                }
    return rows


def _write_index(rows):
    lines = [
        "# Dominios del sistema", "",
        "(generado por `pctl reindex` / `pctl arch touch` — no editar a mano)",
        "",
        "| Dominio | Estado | Ultima actualizacion | Archivo |",
        "|---|---|---|---|",
    ]
    for dominio in sorted(rows):
        r = rows[dominio]
        lines.append(f"| {dominio} | {r['estado']} | {r['actualizado']} | {r['archivo']} |")
    paths.ARCH_INDEX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def touch(dominio, estado="sin_documentar", crear_archivo=False):
    if estado not in ESTADOS:
        raise ValueError(f"estado invalido: {estado}")
    rows = _read_index_rows()
    archivo = "-"
    if crear_archivo or estado != "sin_documentar":
        fpath = paths.ARCH_DIR / f"{dominio}.md"
        if not fpath.exists():
            fpath.write_text(
                _DOMAIN_TEMPLATE.format(dominio=dominio, fecha=_today()),
                encoding="utf-8",
            )
        archivo = fpath.name
    rows[dominio] = {"estado": estado, "actualizado": _today(), "archivo": archivo}
    _write_index(rows)
    return rows[dominio]


def list_domains():
    return _read_index_rows()


def get_body(dominio):
    fpath = paths.ARCH_DIR / f"{dominio}.md"
    if not fpath.exists():
        return None
    return fpath.read_text(encoding="utf-8")


def set_body(dominio, content):
    paths.ARCH_DIR.mkdir(parents=True, exist_ok=True)
    fpath = paths.ARCH_DIR / f"{dominio}.md"
    fpath.write_text(content, encoding="utf-8")
    rows = _read_index_rows()
    estado = rows.get(dominio, {}).get("estado", "parcial")
    rows[dominio] = {"estado": estado, "actualizado": _today(), "archivo": fpath.name}
    _write_index(rows)

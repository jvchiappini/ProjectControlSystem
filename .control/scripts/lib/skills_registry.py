from . import paths

_HEADER = [
    "# Registro de skills y scripts", "",
    "(generado/actualizado por `pctl skill *` — no editar a mano)",
    "",
    "| id | nombre | tipo | estado | disparador | ubicacion | creado_por |",
    "|---|---|---|---|---|---|---|",
]


def _read_rows():
    if not paths.SKILLS_INDEX_MD.exists():
        return []
    rows = []
    for line in paths.SKILLS_INDEX_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("| SK-"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 7:
                rows.append(parts)
    return rows


def _write_rows(rows):
    paths.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    lines = list(_HEADER)
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    paths.SKILLS_INDEX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _next_id(rows):
    max_n = 0
    for r in rows:
        try:
            max_n = max(max_n, int(r[0].split("-")[1]))
        except (IndexError, ValueError):
            pass
    return max_n + 1


def propose(nombre, tipo, disparador, ubicacion, creado_por="agente"):
    if tipo not in ("skill", "script"):
        raise ValueError("tipo debe ser 'skill' o 'script'")
    rows = _read_rows()
    n = _next_id(rows)
    sid = f"SK-{n:04d}"
    rows.append([sid, nombre, tipo, "propuesta", disparador, ubicacion, creado_por])
    _write_rows(rows)
    return sid


def promote(sid):
    rows = _read_rows()
    found = False
    for r in rows:
        if r[0] == sid:
            if r[3] == "activa":
                raise ValueError(f"{sid} ya esta activa")
            r[3] = "activa"
            found = True
    if not found:
        raise ValueError(f"no existe {sid}")
    _write_rows(rows)
    return sid


def list_skills(estado=None):
    rows = _read_rows()
    if estado:
        rows = [r for r in rows if r[3] == estado]
    return rows

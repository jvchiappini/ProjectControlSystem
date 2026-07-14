import datetime

from . import atomic, fm, paths, event_log
from .lock import FileLock

_HEADER = [
    "# Registro de skills y scripts", "",
    "(generado/actualizado por `pctl skill-*` — no editar a mano salvo la",
    "carga inicial de fábrica)",
    "",
    "| id | nombre | tipo | estado | disparador | ubicacion | creado_por |",
    "|---|---|---|---|---|---|---|",
]


def _today():
    return datetime.date.today().isoformat()


def _read_rows():
    if not paths.SKILLS_INDEX_MD.exists():
        return []
    rows = []
    for line in paths.SKILLS_INDEX_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("| SK-"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 7:
                rows.append({
                    "id": parts[0],
                    "nombre": parts[1],
                    "tipo": parts[2],
                    "estado": parts[3],
                    "disparador": parts[4],
                    "ubicacion": parts[5],
                    "creado_por": parts[6],
                })
    return rows


def _write_rows(rows):
    paths.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    lines = list(_HEADER)
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['nombre']} | {r['tipo']} | {r['estado']} "
            f"| {r['disparador']} | {r['ubicacion']} | {r['creado_por']} |"
        )
    atomic.write(paths.SKILLS_INDEX_MD, "\n".join(lines) + "\n")


def _next_id(rows):
    max_n = 0
    for r in rows:
        try:
            max_n = max(max_n, int(r["id"].split("-")[1]))
        except (IndexError, ValueError):
            pass
    return max_n + 1


_SKILL_TEMPLATE = """# Skill: {nombre}

## Disparador
{disparador}

## Procedimiento
(completar)

## Output esperado
(qué produce o cómo se sabe que se completó correctamente)

## Notas
(advertencias, dónde no aplicar, dependencias con otras skills)
"""


def propose(nombre, tipo, disparador, ubicacion, creado_por="agente"):
    """Propone (o registra) una skill. Crea archivo individual .md.

    El estado por defecto es 'activa' (no 'propuesta'), para que toda
    skill esté disponible inmediatamente. Si se quiere mantener en
    'propuesta' hasta confirmación humana, se puede pasar manualmente.
    """
    with FileLock():
        if tipo not in ("skill", "script"):
            raise ValueError("tipo debe ser 'skill' o 'script'")
        rows = _read_rows()
        n = _next_id(rows)
        sid = f"SK-{n:04d}"

        if ubicacion and (paths.SKILLS_DIR / ubicacion).exists():
            fpath = paths.SKILLS_DIR / ubicacion
        else:
            fname = f"{sid}.md" if not ubicacion else ubicacion
            fpath = paths.SKILLS_DIR / fname

        if not fpath.exists():
            body = _SKILL_TEMPLATE.format(nombre=nombre, disparador=disparador)
            data = {
                "id": sid,
                "nombre": nombre,
                "tipo": tipo,
                "estado": "activa",
                "disparador": disparador,
                "ubicacion": str(fpath.relative_to(paths.SKILLS_DIR)),
                "creado_por": creado_por,
                "creado": _today(),
            }
            _write_skill_file(fpath, data, body)

        rel_path = f"skills/{fpath.name}"
        rows.append({
            "id": sid,
            "nombre": nombre,
            "tipo": tipo,
            "estado": "activa",
            "disparador": disparador,
            "ubicacion": rel_path,
            "creado_por": creado_por,
        })
        _write_rows(rows)
        event_log.log("skill-proposed", sid, {
            "nombre": nombre, "tipo": tipo, "estado": "activa",
        })
        return sid


_SKILL_META_ORDER = [
    "id", "nombre", "tipo", "estado", "disparador",
    "ubicacion", "creado_por", "creado",
]


def _write_skill_file(fpath, data, body):
    fpath.parent.mkdir(parents=True, exist_ok=True)
    atomic.write(fpath, fm.dump(data, body, _SKILL_META_ORDER))


def promote(sid, mover_desde_proposed=True):
    """Cambia el estado de una skill a 'activa'.

    Si la skill está en skills/proposed/, mueve el archivo a skills/.
    """
    with FileLock():
        rows = _read_rows()
        for r in rows:
            if r["id"] == sid:
                if r["estado"] == "activa":
                    raise ValueError(f"{sid} ya esta activa")

                r["estado"] = "activa"

                if mover_desde_proposed and "proposed/" in r["ubicacion"]:
                    old_rel = r["ubicacion"]
                    old_file = paths.CONTROL_ROOT / old_rel if not (paths.SKILLS_DIR / old_rel).exists() else paths.SKILLS_DIR / old_rel
                    new_name = old_rel.replace("proposed/", "").replace("skills/", "") if old_rel.startswith("skills/proposed/") else old_rel.replace("proposed/", "")
                    new_file = paths.SKILLS_DIR / new_name
                    if old_file.exists():
                        old_file.rename(new_file)
                    r["ubicacion"] = f"skills/{new_name}"

                _write_rows(rows)
                _update_skill_file_state(sid, "activa", ubicacion=r.get("ubicacion"))
                event_log.log("skill-promoted", sid)
                return sid
        raise ValueError(f"no existe {sid}")


def _update_skill_file_state(sid, new_state, ubicacion=None):
    """Actualiza el estado en el frontmatter del archivo de skill."""
    # Buscar por ubicación en el índice
    rows = _read_rows()
    for r in rows:
        if r["id"] == sid:
            loc = ubicacion or r["ubicacion"]
            fpath = paths.CONTROL_ROOT / loc if not (paths.SKILLS_DIR / loc.replace("skills/", "")).exists() else paths.SKILLS_DIR / loc.replace("skills/", "")
            if not fpath.exists():
                fpath = paths.SKILLS_DIR / loc
            if fpath.exists():
                data, body = fm.parse(fpath.read_text(encoding="utf-8"))
                data["estado"] = new_state
                atomic.write_with_backup(fpath, fm.dump(data, body, _SKILL_META_ORDER))
                return


def get_content(sid):
    """Devuelve (frontmatter, body) de una skill."""
    rows = _read_rows()
    for r in rows:
        if r["id"] == sid:
            fpath = paths.SKILLS_DIR / r["ubicacion"]
            if fpath.exists():
                return fm.parse(fpath.read_text(encoding="utf-8"))
            return r, None
    raise FileNotFoundError(f"skill no encontrada: {sid}")


def list_skills(estado=None):
    rows = _read_rows()
    if estado:
        rows = [r for r in rows if r["estado"] == estado]
    return rows

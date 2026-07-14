"""Herramientas de productividad para el agente.
context-init, session-continue, task-intake — todo en un solo lugar
para ahorrar tokens y comandos repetitivos al iniciar sesion.
"""
import datetime
import re
import subprocess

from . import fm, git, graph, paths, sessions, tasks


def _today():
    return datetime.date.today().isoformat()


def _try_git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True,
                           cwd=paths.CONTROL_ROOT.parent, check=False)
        if r.returncode != 0:
            return None
        return r.stdout.decode("utf-8", errors="replace").strip()
    except FileNotFoundError:
        return None


def _domain_names():
    names = []
    if paths.ARCH_INDEX_MD.exists():
        for line in paths.ARCH_INDEX_MD.read_text("utf-8").splitlines():
            if line.startswith("| ") and not line.startswith("| Dominio") and not line.startswith("|---"):
                parts = [p.strip() for p in line.strip("|").split("|")]
                if parts:
                    names.append(parts[0])
    return names


def _last_session():
    files = sorted(paths.SESSIONS_DIR.glob("S-*.md"), reverse=True)
    if not files:
        return None
    data, body = fm.parse(files[0].read_text(encoding="utf-8"))
    return {"data": data, "body": body}


def context_init():
    """Devuelve un resumen compacto (< 150 lineas) para arrancar sesion."""
    lines = []
    lines.append(f"# Context Init — {_today()}")
    lines.append("")

    # ── git ──
    branch = _try_git("rev-parse", "--abbrev-ref")
    if branch:
        dirty = _try_git("status", "--porcelain") or ""
        n_changed = len([l for l in dirty.splitlines() if l.strip()])
        recent = _try_git("log", "--oneline", "-5") or "(sin commits)"
        lines.append(f"## Git — branch: {branch} · {n_changed} archivo(s) sin commit")
        lines.append(f"   {recent}")
        lines.append("")

    # ── tareas en curso ──
    en_curso = tasks.list_tasks(estado="in_progress")
    bloqueadas = tasks.list_tasks(estado="blocked")
    if en_curso or bloqueadas:
        lines.append(f"## En curso ({len(en_curso)}), bloqueadas ({len(bloqueadas)})")
        for t in en_curso + bloqueadas:
            marca = " [BLOQUEADA]" if t.get("estado") == "blocked" else ""
            lines.append(f"   {t['id']} [{t.get('prioridad','')}] {t['titulo']}{marca}")
            if t.get("bloqueado_por"):
                lines.append(f"       motivo: {t['bloqueado_por']}")
        lines.append("")

    # ── ultima sesion ──
    ult = _last_session()
    if ult and ult["data"].get("resumen", "") != "(sesion en curso)":
        s = ult["data"]
        lines.append(f"## Ultima sesion — {s.get('id','')} ({s.get('fecha','')})")
        lines.append(f"   {s.get('resumen','')}")
        tareas = s.get("tareas_tocadas", [])
        if tareas:
            lines.append(f"   Tareas: {', '.join(tareas)}")
        lines.append("")

    # ── dominios con estado parcial/sin_documentar ──
    pendientes = [
        (n, d) for n, d in sorted(graph._domains().items())
        if d.get("estado") in ("sin_documentar", "parcial")
    ]
    if pendientes:
        lines.append(f"## Dominios pendientes de documentar ({len(pendientes)})")
        for n, d in pendientes:
            lines.append(f"   {n} ({d.get('estado')})")
        lines.append("")

    # ── flujos desactualizados ──
    from . import flows as fl
    desact = fl.list_flows(estado="desactualizado")
    if desact:
        lines.append(f"## Flujos desactualizados ({len(desact)})")
        for f in desact:
            lines.append(f"   {f['id']} {f.get('nombre','')}")
        lines.append("")

    return "\n".join(lines)


def session_continue():
    """Resume la ultima sesion y sugiere proximo paso."""
    ult = _last_session()
    if not ult:
        return "No hay sesiones previas. Empeza con `pctl session-start --agente <nombre>`."

    s = ult["data"]
    resumen = s.get("resumen", "")
    tareas_ids = s.get("tareas_tocadas", [])

    lines = [f"# Continuar sesion — ultima fue {s.get('id','')} ({s.get('fecha','')})"]
    if resumen and resumen != "(sesion en curso)":
        lines.append(f"  Resumen: {resumen}")
    lines.append("")

    if tareas_ids:
        lines.append("## Tareas de la sesion anterior")
        for tid in tareas_ids:
            try:
                t = tasks.get_data(tid)
                estado = t.get("estado", "?")
                lines.append(f"   {tid} [{estado}] {t.get('titulo','')}")
            except FileNotFoundError:
                lines.append(f"   {tid} (no encontrada)")
        lines.append("")

    # sugerir que hacer ahora
    en_curso = tasks.list_tasks(estado="in_progress")
    if en_curso:
        t = en_curso[0]
        lines.append(f"## Sugerencia")
        lines.append(f"   Continuar con {t['id']} — {t['titulo']}")
        lines.append(f"   Correr: `pctl task-show {t['id']}`")
    else:
        lines.append("## Sugerencia")
        lines.append("   No hay tareas en curso. Revisar backlog con `pctl task-list --estado backlog`")

    return "\n".join(lines)


def task_intake(raw_text):
    """Toma texto crudo del usuario, sugiere tipo/prioridad/dominio y crea tarea."""
    raw_lower = raw_text.lower()

    tipo = "feature"
    prioridad = "media"

    if any(w in raw_lower for w in ["bug", "error", "falla", "no funciona", "roto", "crash", "exception"]):
        tipo = "bug"
        prioridad = "alta"
    elif any(w in raw_lower for w in ["refactor", "mejorar", "limpiar", "reestructurar", "deuda"]):
        tipo = "refactor"
    elif any(w in raw_lower for w in ["investigar", "explorar", "investigacion", "spike", "probar"]):
        tipo = "investigacion"
    elif any(w in raw_lower for w in ["doc", "documentar", "readme", "chore"]):
        tipo = "chore"

    dominio = None
    for d in _domain_names():
        if d.lower() in raw_lower:
            dominio = d
            break

    tid, fpath = tasks.new_task(raw_text, prioridad=prioridad, tipo=tipo, dominio=dominio)

    similares = []
    for t in tasks.list_tasks(estado="backlog"):
        tt = t.get("titulo", "").lower()
        # overlap de 3+ palabras
        words = set(raw_lower.split())
        if len(words & set(tt.split())) >= 3:
            similares.append(t)
        if len(similares) >= 5:
            break

    return {
        "id": tid,
        "tipo": tipo,
        "prioridad": prioridad,
        "dominio": dominio,
        "archivo": str(fpath),
        "similares": [(s["id"], s["titulo"]) for s in similares],
    }

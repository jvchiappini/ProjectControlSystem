"""Mantenimiento de documentacion.
doc-update: actualiza architecture/<dominio>.md desde git diff.
ref-add: agrega referencias estructuradas a tasks o dominios.
"""
import re
import subprocess

from . import arch, fm, graph, paths, tasks

_REF_PATTERN = re.compile(r"`([\w./-]+:\d+(?:-\d+)?)`")


def _try_git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True,
                           cwd=paths.CONTROL_ROOT.parent, check=False)
        if r.returncode != 0:
            return None
        return r.stdout.decode("utf-8", errors="replace").strip()
    except FileNotFoundError:
        return None


def _extract_changed_refs():
    """Extrae referencias archivo:linea del git diff sin commit."""
    diff = _try_git("diff", "-U0")
    if not diff:
        return []

    refs = []
    current_file = None
    file_re = re.compile(r"^\+\+\+\ b/(.+)$")
    line_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    for line in diff.splitlines():
        m = file_re.match(line)
        if m:
            current_file = m.group(1)
        m = line_re.match(line)
        if m:
            if current_file and not current_file.startswith(".control/"):
                l1 = m.group(1)
                l2 = m.group(2)
                ref = f"{current_file}:{l1}" + (f"-{l2}" if l2 else "")
                refs.append(ref)
    return refs


def update(dominio):
    """Actualiza architecture/<dominio>.md desde el diff actual.
    1. Extrae referencias del diff
    2. Filtra las que coinciden con el dominio
    3. Las agrega a 'Componentes clave' del doc
    4. Marca flujos relacionados como desactualizados
    """
    refs = _extract_changed_refs()
    if not refs:
        return {"status": "ok", "message": "sin cambios sin commit para analizar", "nuevas": [], "flujos_marcados": []}

    # filtrar refs relevantes al dominio
    dlower = dominio.lower()
    domain_refs = [r for r in refs if dlower in r.lower()]

    # si no hay refs especificas del dominio, usar todas (el diff es pequeno)
    if not domain_refs:
        domain_refs = refs

    # asegurar que el archivo de dominio existe
    body = ""
    if not (paths.ARCH_DIR / f"{dominio}.md").exists():
        arch.touch(dominio, estado="parcial", crear_archivo=True)
        body = ""
    else:
        body = (paths.ARCH_DIR / f"{dominio}.md").read_text(encoding="utf-8")

    # parsear secciones existentes
    secciones = _parse_sections(body)
    existing = secciones.get("Componentes clave", "")
    existing_lines = set()
    for m in _REF_PATTERN.finditer(existing or ""):
        existing_lines.add(m.group(1))

    # nuevas refs que no existian
    nuevas = []
    for r in domain_refs:
        ref_file = r.split(":")[0]
        if ref_file not in {e.split(":")[0] for e in existing_lines}:
            nuevas.append(r)

    if nuevas:
        nuevas_block = "\n".join(f"- `{r}`" for r in nuevas)
        if "Componentes clave" in body:
            body = re.sub(
                r"(## Componentes clave\s*\n)",
                r"\1" + nuevas_block + "\n",
                body,
            )
        else:
            body += f"\n## Componentes clave\n{nuevas_block}\n"

        (paths.ARCH_DIR / f"{dominio}.md").write_text(body, encoding="utf-8")
        arch.touch(dominio, estado="parcial")

    # marcar flujos relacionados como desactualizados
    from . import flows as fl
    flujos_marcados = []
    for f in fl.list_flows():
        doms = f.get("dominios") or []
        if dominio in doms and f.get("estado") != "desactualizado":
            fl.touch_estado(f["id"], "desactualizado")
            flujos_marcados.append(f["id"])

    return {
        "status": "ok",
        "nuevas": nuevas,
        "flujos_marcados": flujos_marcados,
    }


def _parse_sections(body):
    """Parse sections from markdown body."""
    sections = {}
    m_iter = re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE)
    matches = list(m_iter)
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[title] = body[start:end].strip("\n")
    return sections


def ref_add(ref_text, task_id=None, dominio=None):
    """Agrega una referencia archivo:linea a una tarea o dominio.
    Valida que el archivo exista y la linea este en rango.
    """
    m = re.match(r"^([\w./-]+):(\d+)(?:-(\d+))?$", ref_text)
    if not m:
        raise ValueError(f"formato invalido. Usar: `archivo:linea` o `archivo:linea-linea`")

    path = m.group(1)
    line_start = int(m.group(2))
    line_end = int(m.group(3)) if m.group(3) else line_start

    target = paths.CONTROL_ROOT.parent / path
    if not target.exists():
        raise FileNotFoundError(f"no existe: {path}")

    n_lines = sum(1 for _ in target.open(encoding="utf-8", errors="ignore"))
    if line_end > n_lines:
        raise ValueError(f"linea {line_end} fuera de rango (archivo tiene {n_lines} lineas)")

    ref_formatted = f"`{ref_text}`"

    if task_id:
        try:
            fpath = paths.TASKS_DIR / f"{task_id}.md"
            if not fpath.exists():
                for f in sorted(paths.TASKS_DIR.rglob("*.md")):
                    data, _ = fm.parse(f.read_text(encoding="utf-8"))
                    if data.get("id") == task_id:
                        fpath = f
                        break
                else:
                    raise FileNotFoundError(f"tarea no encontrada: {task_id}")
            data, body = fm.parse(fpath.read_text(encoding="utf-8"))
            if ref_formatted not in body:
                body += f"\n- {ref_formatted}\n"
            data["actualizado"] = __import__("datetime").date.today().isoformat()
            from . import tasks as tsk
            tsk.set_body(task_id, body.split("---", 2)[-1].strip() if "---" in body else body)
        except Exception as e:
            raise ValueError(f"no se pudo agregar ref a tarea {task_id}: {e}")
    elif dominio:
        arch_body = ""
        if (paths.ARCH_DIR / f"{dominio}.md").exists():
            arch_body = (paths.ARCH_DIR / f"{dominio}.md").read_text(encoding="utf-8")
        if ref_formatted not in arch_body:
            arch_body += f"\n- {ref_formatted}\n"
        (paths.ARCH_DIR / f"{dominio}.md").write_text(arch_body, encoding="utf-8")
        arch.touch(dominio, estado="parcial")
    else:
        raise ValueError("especificar --task o --dominio")

    return ref_formatted

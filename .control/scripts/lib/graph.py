"""Grafo de relaciones entre items del proyecto.
Solo parsea frontmatter — sin carga de cuerpos completos.
Devuelve arboles de texto para el CLI y dicts para el frontend.
"""
from . import fm, paths

# IDs que un item puede referenciar (task, flow, decision, dominio)
_ID_PATTERN = __import__("re").compile(r"\b(T-\d+|F-\d+|D-\d+)\b")


def _all_entities():
    """Devuelve {id: {tipo, titulo, data}} de tasks, flows, decisions, dominios."""
    entities = {}

    for f in sorted(paths.TASKS_DIR.rglob("T-*.md")):
        d, _ = fm.parse(f.read_text(encoding="utf-8"))
        tid = d.get("id", "")
        if tid:
            entities[tid] = {"tipo": "tarea", "titulo": d.get("titulo", ""), "data": d}

    for f in sorted(paths.FLOWS_DIR.rglob("F-*.md")):
        d, _ = fm.parse(f.read_text(encoding="utf-8"))
        fid = d.get("id", "")
        if fid:
            entities[fid] = {"tipo": "flujo", "titulo": d.get("nombre", ""), "data": d}

    for f in sorted(paths.DECISIONS_DIR.rglob("D-*.md")):
        d, _ = fm.parse(f.read_text(encoding="utf-8"))
        did = d.get("id", "")
        if did:
            entities[did] = {"tipo": "decision", "titulo": d.get("titulo", ""), "data": d}

    for name, info in _domains().items():
        entities[name] = {"tipo": "dominio", "titulo": name, "data": info}

    return entities


def _domains():
    rows = {}
    if paths.ARCH_INDEX_MD.exists():
        for line in paths.ARCH_INDEX_MD.read_text("utf-8").splitlines():
            if line.startswith("| ") and not line.startswith("| Dominio") and not line.startswith("|---"):
                parts = [p.strip() for p in line.strip("|").split("|")]
                if parts:
                    rows[parts[0]] = {"estado": parts[1] if len(parts) > 1 else "", "archivo": parts[3] if len(parts) > 3 else ""}
    return rows


def _find_entity(eid):
    """Busca el id en tasks, flows, decisions, dominios."""
    for f in sorted(paths.TASKS_DIR.rglob("T-*.md")):
        d, _ = fm.parse(f.read_text(encoding="utf-8"))
        if d.get("id") == eid:
            return {"id": eid, "tipo": "tarea", "titulo": d.get("titulo", ""), "data": d}
    for f in sorted(paths.FLOWS_DIR.rglob("F-*.md")):
        d, _ = fm.parse(f.read_text(encoding="utf-8"))
        if d.get("id") == eid:
            return {"id": eid, "tipo": "flujo", "titulo": d.get("nombre", ""), "data": d}
    for f in sorted(paths.DECISIONS_DIR.rglob("D-*.md")):
        d, _ = fm.parse(f.read_text(encoding="utf-8"))
        if d.get("id") == eid:
            return {"id": eid, "tipo": "decision", "titulo": d.get("titulo", ""), "data": d}
    dominios = _domains()
    if eid in dominios:
        return {"id": eid, "tipo": "dominio", "titulo": eid, "data": dominios[eid]}
    return None


def relations(eid):
    """Devuelve dict de relaciones para un id: {directo: [...], inverso: [...]}."""
    entity = _find_entity(eid)
    if not entity:
        return {"error": f"'{eid}' no encontrado en tasks, flows, decisions ni dominios"}

    directo = []
    inverso = []
    d = entity["data"]

    if entity["tipo"] == "tarea":
        for dep in (d.get("depende_de") or []):
            directo.append({"id": dep, "rel": "depende_de"})
        dom = d.get("dominio") or ""
        if dom:
            directo.append({"id": dom, "rel": "dominio"})

    elif entity["tipo"] == "flujo":
        for dom in (d.get("dominios") or []):
            directo.append({"id": dom, "rel": "cruza_dominio"})
        padre = d.get("padre")
        if padre:
            directo.append({"id": padre, "rel": "subflujo_de"})

    elif entity["tipo"] == "decision":
        for old in (d.get("reemplaza") or []):
            directo.append({"id": old, "rel": "reemplaza_a"})
    elif entity["tipo"] == "dominio":
        pass

    entities = _all_entities()
    for oid, oinfo in entities.items():
        if oid == eid:
            continue
        od = oinfo["data"]
        if oinfo["tipo"] == "tarea":
            if eid in (od.get("depende_de") or []):
                inverso.append({"id": oid, "rel": "depende_de_mi"})
            if od.get("dominio") == eid:
                inverso.append({"id": oid, "rel": "tarea_del_dominio"})
        elif oinfo["tipo"] == "flujo":
            if eid in (od.get("dominios") or []):
                inverso.append({"id": oid, "rel": "flujo_que_me_cruza"})
            if od.get("padre") == eid:
                inverso.append({"id": oid, "rel": "subflujo"})
        elif oinfo["tipo"] == "decision":
            if eid in (od.get("reemplaza") or []):
                inverso.append({"id": oid, "rel": "reemplazado_por"})

    return {"entity": entity, "directo": directo, "inverso": inverso}


def tree(eid, indent=0, visited=None, max_depth=3):
    """Texto en arbol comenzando desde eid."""
    if visited is None:
        visited = set()
    if eid in visited or indent > max_depth:
        return ""
    visited.add(eid)

    r = relations(eid)
    if "error" in r:
        return "  " * indent + f"! {r['error']}\n"

    e = r["entity"]
    prefix = "  " * indent
    line = f"{prefix}{e['id']} ({e['tipo']}) — {e['titulo']}\n"
    result = [line]

    for link in r["directo"]:
        if link["id"] not in visited:
            child = tree(link["id"], indent + 1, visited, max_depth)
            if child:
                result.append("  " * indent + f"  ├── {link['rel']}:\n")
                result.append(child)

    for link in r["inverso"]:
        if link["id"] not in visited and indent < max_depth:
            child = tree(link["id"], indent + 1, visited, max_depth)
            if child:
                result.append("  " * indent + f"  └── {link['rel']}:\n")
                result.append(child)

    return "".join(result)

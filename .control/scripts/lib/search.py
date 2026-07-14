"""Búsqueda unificada sobre .control/.
Solo parsea frontmatter y grepea cuerpos — sin dependencias externas.
"""
import re

from . import fm, paths

SEARCH_DIRS = ["tasks", "architecture", "flows", "decisions", "sessions", "skills"]


def search(query, max_results=30):
    """Busca query (regex o literal) en todos los .md de .control/.
    Devuelve [(ruta_relativa, linea_num, linea_texto)].
    """
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    results = []
    for dname in SEARCH_DIRS:
        d = paths.CONTROL_ROOT / dname
        if not d.exists():
            continue
        for f in sorted(d.rglob("*.md")):
            if f.name.startswith("_"):
                continue
            rel = str(f.relative_to(paths.CONTROL_ROOT))
            lines = f.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    results.append((rel, i, line.strip()[:120]))
                    if len(results) >= max_results:
                        return results
    return results


def search_fm(query, max_results=30):
    """Busca solo en campos de frontmatter (id, titulo, nombre, etc)."""
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    results = []
    for dname in SEARCH_DIRS:
        d = paths.CONTROL_ROOT / dname
        if not d.exists():
            continue
        for f in sorted(d.rglob("*.md")):
            rel = str(f.relative_to(paths.CONTROL_ROOT))
            data, _ = fm.parse(f.read_text(encoding="utf-8"))
            for k, v in data.items():
                if isinstance(v, str) and pattern.search(v):
                    results.append((rel, k, str(v)[:120]))
                    if len(results) >= max_results:
                        return results
                    break
    return results

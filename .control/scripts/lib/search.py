"""Unified search over ALL of .control/ (stdlib only).

Designed for agents: find the right file and line without opening
files. Results are ranked per file and grouped, so a single call costs
a few hundred tokens instead of reading whole directories.

Ranking (per file):
  - match in frontmatter id/title/name   +10 per term
  - match in other frontmatter fields    +4
  - match in a markdown heading          +3
  - match in body line                   +1 (capped)
  - core memory files (CONTEXT, PROJECT, GOALS...) get a small bonus,
    sessions a small penalty (they are the noisiest, append-only log)

Query semantics:
  - plain words  -> every word must appear somewhere in the file (AND),
                    case-insensitive; quote a phrase to keep it together
  - --regex      -> the query is one regular expression
"""
import re
import shlex

from . import fm, paths

# area name -> path relative to CONTROL_ROOT ("" = top-level files only)
AREAS = {
    "core": "",
    "tasks": "tasks",
    "sessions": "sessions",
    "architecture": "architecture",
    "flows": "flows",
    "decisions": "decisions",
    "docs": "docs",
    "roadmaps": "roadmaps",
    "skills": "skills",
    "prompts": "prompts",
    "diagrams": "diagrams",
    "scripts": "scripts",
    "frontend": "frontend",
}
CODE_AREAS = {"scripts", "frontend"}
TEXT_EXT = {".md", ".mmd", ".txt", ".template", ".json"}
CODE_EXT = {".py", ".js", ".css", ".html"}
SKIP_DIRS = {".backups", "__pycache__", ".update", ".framework_base", "node_modules"}
GENERATED = {"BACKLOG.md", "IN_PROGRESS.md", "DONE.md", "_index.md"}
TITLE_KEYS = ("id", "titulo", "nombre", "title", "name")
CORE_BONUS = {"CONTEXT.md": 3, "PROJECT.md": 2, "GOALS.md": 2, "SYSTEM.md": 1, "SYSTEM.local.md": 2}


def _area_of(rel):
    parts = rel.split("/")
    return "core" if len(parts) == 1 else parts[0]


def iter_files(areas=None, include_code=False, include_generated=False):
    """Yield (path, rel_posix) for every searchable file."""
    root = paths.CONTROL_ROOT
    wanted = set(areas) if areas else set(AREAS) - (set() if include_code else CODE_AREAS)
    exts = TEXT_EXT | (CODE_EXT if include_code or (wanted & CODE_AREAS) else set())
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        parts = rel.split("/")
        if any(p in SKIP_DIRS for p in parts[:-1]):
            continue
        name = parts[-1]
        if name.startswith(".") and name != ".schema_version":
            continue  # runtime state (.events.ndjson, locks, caches)
        if _area_of(rel) not in wanted:
            continue
        suffix = ".template" if name.endswith(".template") else f.suffix
        if suffix not in exts:
            continue
        if not include_generated and name in GENERATED:
            continue
        yield f, rel


def _compile_terms(query, regex, case):
    flags = 0 if case else re.IGNORECASE
    if regex and isinstance(query, (list, tuple)):
        query = " ".join(query)
    if regex:
        try:
            return [re.compile(query, flags)]
        except re.error as e:
            raise ValueError(f"regex invalida: {e}")
    if isinstance(query, (list, tuple)):
        words = list(query)  # already split by the shell: each item is one term/phrase
    else:
        try:
            words = shlex.split(query)
        except ValueError:
            words = query.split()
    words = [w for w in words if w.strip()]
    if not words:
        raise ValueError("busqueda vacia")
    return [re.compile(re.escape(w), flags) for w in words]


def _score_file(text, rel, terms, fm_only):
    data, body = fm.parse(text) if text.startswith("---") else ({}, text)
    found = set()
    score = 0
    hits = []  # (line_no, line, weight)

    for k, v in data.items():
        sv = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
        for i, t in enumerate(terms):
            if t.search(sv):
                found.add(i)
                score += 10 if k in TITLE_KEYS else 4

    if not fm_only:
        offset = text.count("\n", 0, len(text) - len(body)) if body is not text else 0
        body_score = 0
        for n, line in enumerate(body.splitlines(), 1 + offset):
            matched = [i for i, t in enumerate(terms) if t.search(line)]
            if not matched:
                continue
            found.update(matched)
            w = 3 if line.lstrip().startswith("#") else 1
            body_score += w * len(matched)
            hits.append((n, line.strip(), w))
        score += min(body_score, 30)

    if len(found) < len(terms):
        return None  # AND semantics: every term must appear in the file
    name = rel.rsplit("/", 1)[-1]
    score += CORE_BONUS.get(name, 0)
    if rel.startswith("sessions/"):
        score -= 2
    hits.sort(key=lambda h: (-h[2], h[0]))
    return {"score": score, "data": data, "hits": hits}


def find(query, areas=None, estado=None, regex=False, case=False, fm_only=False,
         include_code=False, include_generated=False, max_files=15, hits_per_file=3):
    """Ranked search. Returns list of dicts sorted by relevance:
    {"path", "area", "score", "id", "title", "estado", "hits": [(line_no, text)], "total_hits"}
    """
    if areas:
        bad = [a for a in areas if a not in AREAS]
        if bad:
            raise ValueError(f"area desconocida: {', '.join(bad)} (validas: {', '.join(AREAS)})")
    terms = _compile_terms(query, regex, case)
    results = []
    for f, rel in iter_files(areas, include_code, include_generated):
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        r = _score_file(text, rel, terms, fm_only)
        if not r:
            continue
        data = r["data"]
        if estado and str(data.get("estado", "")).lower() != estado.lower():
            continue
        title = next((str(data[k]) for k in TITLE_KEYS[1:] if data.get(k)), "")
        results.append({
            "path": rel,
            "area": _area_of(rel),
            "score": r["score"],
            "id": data.get("id") or "",
            "title": title,
            "estado": data.get("estado") or "",
            "hits": [(n, t[:160]) for n, t, _ in r["hits"][:hits_per_file]],
            "total_hits": len(r["hits"]),
        })
    results.sort(key=lambda x: (-x["score"], x["path"]))
    return results[:max_files] if max_files else results


def format_results(results, files_only=False):
    if not results:
        return "sin resultados"
    out = []
    for r in results:
        meta = " | ".join(x for x in (r["id"], r["title"], r["estado"]) if x)
        head = f".control/{r['path']}" + (f"  [{meta}]" if meta else "")
        if files_only:
            out.append(head)
            continue
        n_hits = r["total_hits"]
        out.append(f"{head}  ({n_hits} hit{'s' if n_hits != 1 else ''})" if n_hits else f"{head}  (match in metadata)")
        for n, t in r["hits"]:
            out.append(f"    :{n}  {t}")
        extra = r["total_hits"] - len(r["hits"])
        if extra > 0:
            out.append(f"    ... {extra} more")
    return "\n".join(out)


# ---- backward-compatible API (used by frontend/server.py) ----

def search(query, max_results=30):
    """Flat list [(rel_path, line_no, line_text)] across all of .control/."""
    if not (query or "").strip():
        return []
    try:
        ranked = find(query, max_files=0, hits_per_file=10)
    except ValueError:
        return []
    flat = []
    for r in ranked:
        if not r["hits"]:
            flat.append((r["path"], 1, r["title"] or r["id"]))
        for n, t in r["hits"]:
            flat.append((r["path"], n, t))
            if len(flat) >= max_results:
                return flat
    return flat[:max_results]


def search_fm(query, max_results=30):
    """Frontmatter-only search: [(rel_path, id, title)]."""
    try:
        ranked = find(query, fm_only=True, max_files=max_results)
    except ValueError:
        return []
    return [(r["path"], r["id"], r["title"]) for r in ranked]

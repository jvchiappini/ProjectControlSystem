"""Lean mode: how hard the agent pushes for the smallest correct change.

The level is project data (`.control/lean.json`, committed, never touched by
updates). `PCTL_LEAN` overrides it for one shell. Rules live in
`skills/lean.md`; this module stores the level, renders the one line
`pctl brief` shows, and backs three helpers with compact output:

  reuse      what already exists (docs, code definitions, installed deps)
  new_deps   dependencies added to manifests vs a git ref
  debt_scan  `shortcut:` markers left in code -> backlog tasks
"""
import hashlib
import json
import os
import re

from . import fm, indexes, paths, search, tasks, util

LEVELS = ["off", "lite", "full", "strict"]
DEFAULT_LEVEL = "lite"
CONFIG = paths.CONTROL_ROOT / "lean.json"


def _read():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def level():
    env = os.environ.get("PCTL_LEAN", "").strip().lower()
    if env in LEVELS:
        return env
    lvl = _read().get("level")
    return lvl if lvl in LEVELS else DEFAULT_LEVEL


def set_level(new):
    if new not in LEVELS:
        raise ValueError(f"invalid level '{new}' (use: {', '.join(LEVELS)})")
    data = _read()
    data["level"] = new
    CONFIG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return new


def brief_line():
    lvl = level()
    if lvl == "off":
        return None
    return f"Lean mode: {lvl} - before writing code follow `.control/skills/lean.md` (`pctl lean <level>` to change)."


# ---- reuse: what already exists before writing new code ----

DEF_RX = re.compile(r"\b(?:def|class|function|func|fn|const|let|var|interface|type|"
                    r"struct|enum|trait|module|macro)\s+([A-Za-z_$][\w$]*)")


def _norm(s):
    return s.lower().replace("_", "").replace("-", "")


def reuse(words, limit=15):
    words = [_norm(w) for w in words if w.strip()]
    if not words:
        raise ValueError("give at least one word")
    out = []
    docs = search.find("|".join(re.escape(w) for w in words), regex=True,
                       areas=["architecture", "flows", "docs", "decisions"],
                       max_files=8, hits_per_file=2)
    docs = [d for d in docs if "template" not in d["path"].rsplit("/", 1)[-1]][:5]
    if docs:
        out += ["Docs (follow their file:line refs):", search.format_results(docs)]
    defs, deps = [], []
    for rel in util.project_files():
        manifest = is_manifest(rel)
        for n, line in enumerate(util.read_lines(rel), 1):
            if manifest:
                if any(w in _norm(line) for w in words):
                    deps.append(f"  {rel}:{n}  {line.strip()[:100]}")
                continue
            for m in DEF_RX.finditer(line):
                score = sum(w in _norm(m.group(1)) for w in words)
                if score:
                    defs.append((-score, rel, n, line.strip()[:100]))
    if defs:
        defs.sort()
        out.append("Definitions in code:")
        out += [f"  {rel}:{n}  {text}" for _, rel, n, text in defs[:limit]]
        if len(defs) > limit:
            out.append(f"  ... {len(defs) - limit} more (--limit N)")
    if deps:
        out += ["Installed dependencies:"] + deps[:limit]
    return "\n".join(out) if out else "nothing found - check stdlib / platform features next (skills/lean.md)"


# ---- deps: new dependencies vs a git ref ----

MANIFEST_NAMES = {"package.json", "composer.json", "pyproject.toml", "Pipfile",
                  "Cargo.toml", "go.mod", "Gemfile"}
REQ_RX = re.compile(r"^requirements[\w.-]*\.txt$")
JSON_SECTIONS = ("dependencies", "devDependencies", "peerDependencies",
                 "optionalDependencies", "require", "require-dev")
TOML_SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies", "packages", "dev-packages")
PKG_NAME_RX = re.compile(r"^\s*([A-Za-z0-9_.\-]+)")


def is_manifest(rel):
    name = rel.rsplit("/", 1)[-1]
    return name in MANIFEST_NAMES or bool(REQ_RX.match(name))


def _spec_names(specs):
    return {m.group(1).lower() for m in (PKG_NAME_RX.match(s) for s in specs) if m}


def _toml_deps(text):
    try:
        import tomllib
    except ImportError:  # Python < 3.11: names of `x = ...` lines under *dependencies* tables
        names, on = set(), False
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("["):
                on = "dependencies" in s or "packages" in s
            elif on and "=" in s and not s.startswith("#"):
                names.add(s.split("=", 1)[0].strip().strip('"').lower())
        return names
    try:
        d = tomllib.loads(text)
    except ValueError:
        return set()
    proj = d.get("project", {})
    names = _spec_names(proj.get("dependencies", []))
    for group in proj.get("optional-dependencies", {}).values():
        names |= _spec_names(group)
    poetry = d.get("tool", {}).get("poetry", {})
    tables = [poetry.get("dependencies", {}), poetry.get("dev-dependencies", {})]
    tables += [g.get("dependencies", {}) for g in poetry.get("group", {}).values()]
    tables += [d.get(k) for k in TOML_SECTIONS]
    for t in tables:
        if isinstance(t, dict):
            names |= {k.lower() for k in t}
    names.discard("python")
    return names


def manifest_deps(rel, text):
    """Set of dependency names declared in one manifest's text."""
    if not text:
        return set()
    name = rel.rsplit("/", 1)[-1]
    if name.endswith(".json"):
        try:
            d = json.loads(text)
        except ValueError:
            return set()
        return {k for s in JSON_SECTIONS if isinstance(d.get(s), dict) for k in d[s]}
    if name.endswith(".toml") or name == "Pipfile":
        return _toml_deps(text)
    if name == "go.mod":
        return set(re.findall(r"^\s*(?:require\s+)?([\w.\-]+\.[\w.\-/]+)\s+v", text, re.M))
    if name == "Gemfile":
        return set(re.findall(r"^\s*gem\s+['\"]([^'\"]+)", text, re.M))
    return _spec_names(s for s in (l.split("#", 1)[0].strip() for l in text.splitlines())
                       if s and not s.startswith("-"))  # requirements*.txt


def new_deps(base="HEAD"):
    """{manifest: sorted new dependency names}, working tree vs `base`."""
    found = {}
    for rel in util.project_files():
        if is_manifest(rel):
            before = manifest_deps(rel, util.git("show", f"{base}:{rel}", timeout=20) or "")
            added = sorted(manifest_deps(rel, "\n".join(util.read_lines(rel))) - before)
            if added:
                found[rel] = added
    return found


def deps_report(base="HEAD"):
    found = new_deps(base)
    if not found:
        return None
    need = "a one-line reason each" + (" + an ADR (decision-record.md)" if level() == "strict" else "")
    return "\n".join([f"New dependencies vs {base} (lean: {need}):"]
                     + [f"  {rel}: {', '.join(names)}" for rel, names in found.items()])


# ---- debt: `shortcut:` markers left in code -> backlog tasks ----

DEFAULT_MARKER = "shortcut"
DEBT_KEY_RX = re.compile(r"debt-key: `([0-9a-f]{10})`")
PROSE_EXT = (".md", ".txt", ".rst")


def marker():
    return _read().get("debt_marker") or DEFAULT_MARKER


def _scan_markers(mark):
    rx = re.compile(rf"(?:#|//|/\*|<!--|--|;|^\s*\*)\s*{re.escape(mark)}:\s*(.+?)\s*(?:\*/|-->)?\s*$", re.I)
    for rel in util.project_files():
        if rel.endswith(PROSE_EXT):
            continue
        for n, line in enumerate(util.read_lines(rel), 1):
            m = rx.search(line)
            if m:
                text = m.group(1)
                key = hashlib.sha1(f"{rel}|{text.lower()}".encode()).hexdigest()[:10]
                yield {"rel": rel, "line": n, "text": text, "key": key}


def tracked_keys(key_rx=DEBT_KEY_RX):
    """{key: (task id, estado)} for task bodies matching `key_rx` (one group: the key)."""
    out = {}
    for f in paths.TASKS_DIR.rglob("T-*.md"):
        text = f.read_text(encoding="utf-8")
        m = key_rx.search(text)
        if m:
            data, _ = fm.parse(text)
            out[m.group(1)] = (data.get("id"), data.get("estado"))
    return out


def debt_scan(mark=None, apply=False):
    mark = mark or marker()
    found = list(_scan_markers(mark))
    tracked = tracked_keys()
    present = {d["key"] for d in found}
    new = [d for d in found if d["key"] not in tracked]
    gone = [f"{tid} [{est}]" for key, (tid, est) in tracked.items() if key not in present and est != "done"]
    lines = []
    if new and apply:
        lines.append(f"Created {len(new)} debt task(s):")
        for d in new:
            tid, _ = tasks.new_task(f"Debt: {d['text'][:70]}", prioridad="baja", tipo="chore",
                                    creado_por="agente")
            tasks.set_body(tid, (
                f"\n## Contexto\n\nShortcut left in `{d['rel']}` (line {d['line']} when scanned): {d['text']}\n\n"
                f"debt-key: `{d['key']}`\n\n"
                "## Criterios de aceptacion\n- [ ] Shortcut resolved and its marker removed\n\n"
                "## Notas del agente\n\n"))
            lines.append(f"  {tid}  {d['rel']}:{d['line']}  {d['text'][:80]}")
        indexes.reindex()
    elif new:
        lines.append(f"Untracked `{mark}:` markers ({len(new)}) - `pctl debt-scan --apply` creates tasks:")
        lines += [f"  {d['rel']}:{d['line']}  {d['text'][:80]}" for d in new]
    if gone:
        lines.append("Marker removed, task still open (close it if resolved): " + ", ".join(gone))
    if len(found) > len(new):
        lines.append(f"{len(found) - len(new)} marker(s) already tracked by tasks.")
    return "\n".join(lines) or f"no `{mark}:` markers found"

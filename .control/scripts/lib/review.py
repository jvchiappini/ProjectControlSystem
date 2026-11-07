"""Review and audit maps: what an agent must read beyond the diff.

`review-context` turns a diff into a short reading list: docs whose
`file:line` refs point at the changed lines, symbols touched and where
they are used, duplicates and new dependencies. `audit-plan` ranks where
a whole-repo audit should start. Both print file:line, never code.
"""
import re

from . import arch, dupes, flows, lean, paths, util
from .validate import _REF_PATTERN

HUNK_RX = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
DOC_DIRS = (paths.ARCH_DIR, paths.FLOWS_DIR, paths.TASKS_DIR, paths.DOCS_DIR, paths.DECISIONS_DIR)
ENTRY_STEMS = {"main", "app", "server", "index", "cli", "manage", "wsgi", "asgi", "routes",
               "urls", "router", "api", "handler", "handlers", "__main__", "program", "startup"}
GENERATED = {"BACKLOG.md", "IN_PROGRESS.md", "DONE.md", "_index.md"}


def changed_hunks(base="HEAD"):
    """{rel: [(start, end), ...]} of changed lines (new side) vs `base`, untracked included."""
    hunks, cur = {}, None
    for line in (util.git("diff", "-U0", "--no-color", base, timeout=30) or "").splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
            if cur:
                hunks.setdefault(cur, [])
        elif cur and (m := HUNK_RX.match(line)):
            start, count = int(m.group(1)), int(m.group(2) or 1)
            hunks[cur].append((start, start + max(count, 1) - 1))
    for rel in (util.git("ls-files", "--others", "--exclude-standard") or "").splitlines():
        hunks.setdefault(rel, [(1, max(len(util.read_lines(rel)), 1))])
    return hunks


def _overlaps(a, b, ranges):
    return any(s <= b and a <= e for s, e in ranges)


def _doc_refs(hunks):
    """[(doc rel, [ref text + '*' if it overlaps a changed line])] for docs pointing at changed files."""
    out = []
    for d in DOC_DIRS:
        for md in sorted(d.rglob("*.md")):
            if md.name in GENERATED or "template" in md.name:
                continue
            refs = []
            for m in _REF_PATTERN.finditer(md.read_text(encoding="utf-8")):
                rel, a = m.group(1), int(m.group(2))
                if rel in hunks:
                    b = int(m.group(3) or a)
                    refs.append(m.group(0).strip("`") + ("*" if _overlaps(a, b, hunks[rel]) else ""))
            if refs:
                out.append((md.relative_to(paths.CONTROL_ROOT).as_posix(), sorted(set(refs))))
    return out


def _touched_symbols(hunks):
    """{name: (rel, def line)} for functions whose definition or body was changed."""
    out = {}
    for rel, ranges in hunks.items():
        if not any(rel.endswith(e) for e in dupes.CODE_EXT):
            continue
        defs = [(n, m.group(1) or m.group(2)) for n, l in enumerate(util.read_lines(rel), 1)
                if (m := dupes.FN_RX.search(l))]
        for s, e in ranges:
            inside = [d for d in defs if s <= d[0] <= e]
            above = [d for d in defs if d[0] < s][-1:]
            for n, name in inside + above:
                if len(name) >= 4 and name not in dupes.COMMON_NAMES:
                    out.setdefault(name, (rel, n))
    return out


def _usages(symbols, files):
    """{name: [file:line]} of calls (`name(`, `module.name(`) and imports of each symbol."""
    pats = {}
    for name, (rel, _) in symbols.items():
        stem = re.escape(rel.rsplit("/", 1)[-1].split(".")[0])
        n = re.escape(name)
        pats[name] = re.compile(rf"(?:(?<![\w.])|(?<=\b{stem}\.)){n}\s*\(|\bimport\b.*\b{n}\b")
    found = {k: [] for k in symbols}
    for rel in files:
        for i, line in enumerate(util.read_lines(rel), 1):
            for name, rx in pats.items():
                if symbols[name] != (rel, i) and rx.search(line):
                    found[name].append(f"{rel}:{i}")
    return found


def review_context(base="HEAD", per_name=4, max_symbols=8):
    hunks = changed_hunks(base)
    if not hunks:
        return f"no changes vs {base}"
    out = [f"Changed vs {base}: {len(hunks)} file(s), "
           f"{sum(len(v) for v in hunks.values())} hunk(s)."]
    refs = _doc_refs(hunks)
    if refs:
        out.append("Docs referencing changed files (* = points at changed lines: re-read, update or mark outdated):")
        out += [f"  {doc}: {', '.join(r)}" for doc, r in refs]
    files = dupes.scope_files(hunks)
    symbols = _touched_symbols(hunks)
    uses = _usages(symbols, files)
    # a symbol used only inside its own file is covered by reading that file
    used = {k: v for k, v in uses.items() if any(not w.startswith(symbols[k][0] + ":") for w in v)}
    if used:
        out.append("Touched symbols used in other files (check those callers still hold):")
        ranked = sorted(used.items(), key=lambda kv: -len(kv[1]))
        for name, where in ranked[:max_symbols]:
            rel, n = symbols[name]
            more = f" (+{len(where) - per_name})" if len(where) > per_name else ""
            out.append(f"  {name} ({rel}:{n}) x{len(where)}: {', '.join(where[:per_name])}{more}")
        if len(ranked) > max_symbols:
            out.append(f"  ... {len(ranked) - max_symbols} more symbol(s) with fewer uses")
    dup = _dupes_for(hunks, files)
    if dup:
        out.append(dup)
    deps = lean.deps_report(base)
    if deps:
        out.append(deps)
    return "\n".join(out)


def _dupes_for(hunks, files):
    changed = set(hunks)
    names = {k: v for k, v in dupes.same_name(files).items() if {r for r, _ in v} & changed}
    groups = [g for g in dupes.blocks(files) if {r for r, _, _ in g} & changed]
    lines = []
    if names:
        lines.append("Same name defined elsewhere (reuse or share one):")
        lines += [f"  {k}: " + ", ".join(f"{r}:{n}" for r, n in v[:5]) for k, v in list(names.items())[:5]]
    if groups:
        lines.append("Duplicated blocks involving changed files:")
        lines += ["  " + ", ".join(f"{r}:{s}-{e}" for r, s, e in g[:4]) for g in groups[:5]]
    return "\n".join(lines)


def audit_plan(limit=10, include=None):
    files = dupes._code_files(include)
    if not files:
        return "no code files found"
    sizes = {r: len(util.read_lines(r)) for r in files}
    entries = sorted((r for r in files if r.rsplit("/", 1)[-1].rsplit(".", 1)[0] in ENTRY_STEMS),
                     key=lambda r: (r.count("/"), r))
    churn = {}
    log = util.git("log", "--since=180.days", "--name-only", "--pretty=format:", timeout=30) or ""
    for rel in log.splitlines():
        if rel in sizes:
            churn[rel] = churn.get(rel, 0) + 1
    hot = sorted(churn, key=lambda r: -churn[r] * max(sizes[r], 1))[:limit]
    big = sorted(sizes, key=lambda r: -sizes[r])[:limit]
    out = [f"{len(files)} code files. Audit in this order; apply skills/code-review.md to each:"]
    if entries:
        out.append("1. Entry points (trace data flow and trust boundaries from here):")
        out += [f"  {r} ({sizes[r]} lines)" for r in entries[:limit]]
    if hot:
        out.append("2. Hotspots (changed often x size, last 180 days):")
        out += [f"  {r} ({churn[r]} commits, {sizes[r]} lines)" for r in hot]
    out.append("3. Largest files: " + ", ".join(f"{r} ({sizes[r]})" for r in big[:5]))
    n_dom, n_flow = len(arch.list_domains()), len(flows.list_flows())
    out.append(f"Map: {n_dom} domain(s) (`pctl arch-list`), {n_flow} flow(s) (`pctl flow-list`) - "
               "read the relevant flow before the files it crosses.")
    dn, dg = len(dupes.same_name(files)), len(dupes.blocks(files))
    if dn or dg:
        out.append(f"Duplication: {dn} repeated function name(s), {dg} duplicated block group(s) - `pctl dupes`.")
    return "\n".join(out)

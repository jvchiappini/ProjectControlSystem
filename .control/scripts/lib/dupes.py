"""`pctl dupes`: repeated code that should become one shared utility.

Two signals, both language-agnostic and stdlib-only:
  - same function name defined in 2+ files (likely copy-pasted helpers)
  - identical blocks of WINDOW+ normalized lines in 2+ places

Same name or same text is a hint, not proof: compare behaviour before
merging (see skills/lean.md, "Shared utilities").
"""
import hashlib
import re

from . import util

WINDOW = 6
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte",
            ".go", ".rs", ".java", ".kt", ".cs", ".rb", ".php", ".c", ".h", ".cpp",
            ".hpp", ".swift", ".scala", ".lua", ".sh", ".dart"}
FN_RX = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:pub(?:\([\w ]+\))?\s+)?(?:static\s+)?(?:async\s+)?"
                   r"(?:(?:def|function|func|fn)\s+([A-Za-z_$][\w$]*)|"
                   r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>)")
# names that are legitimately defined in many files
COMMON_NAMES = {"main", "__init__", "__repr__", "__str__", "__eq__", "setUp", "tearDown",
                "constructor", "render", "init", "run", "setup", "handler", "default"}
TRIVIAL_RX = re.compile(r"^(?:[\s{}()\[\];,]*|(?:#|//|/?\*).*|(?:import|from|package|using|#include|require)\b.*"
                        r"|(?:else|try|finally|except|return|pass|break|continue|end)\b:?;?)$")


def _code_files(include=None):
    return [r for r in util.project_files(include) if any(r.endswith(e) for e in CODE_EXT)
            and not r.endswith(".min.js")]


def scope_files(changed):
    """Code files of the project plus any .control/ dirs a change touches."""
    extra = sorted({r.rsplit("/", 1)[0] for r in changed if r.startswith(".control/") and "/" in r})
    return list(dict.fromkeys(_code_files() + (_code_files(extra) if extra else [])))


def same_name(files):
    """{name: [(rel, line)]} for function names defined in 2+ files."""
    seen = {}
    for rel in files:
        for n, line in enumerate(util.read_lines(rel), 1):
            for m in FN_RX.finditer(line):
                name = m.group(1) or m.group(2)
                if name in COMMON_NAMES or name.startswith("test"):
                    continue
                seen.setdefault(name, []).append((rel, n))
    return {k: v for k, v in seen.items() if len({r for r, _ in v}) > 1}


def _windows(rel):
    """Yield (hash, first_line, last_line) per window of normalized lines."""
    norm = [(n, " ".join(l.split())) for n, l in enumerate(util.read_lines(rel), 1)]
    norm = [(n, l) for n, l in norm if not TRIVIAL_RX.match(l)]
    for i in range(len(norm) - WINDOW + 1):
        chunk = norm[i:i + WINDOW]
        h = hashlib.sha1("\n".join(l for _, l in chunk).encode()).hexdigest()
        yield h, chunk[0][0], chunk[-1][0]


def blocks(files):
    """Groups of identical code blocks: [[(rel, start, end), ...], ...], biggest first."""
    locs = {}
    for rel in files:
        for h, a, b in _windows(rel):
            locs.setdefault(h, []).append((rel, a, b))
    dup = {h: v for h, v in locs.items() if len(v) > 1}
    # merge overlapping duplicated windows of one file into ranges
    ranges = []  # [rel, start, end, set(hashes)]
    by_file = {}
    for h, v in dup.items():
        for rel, a, b in v:
            by_file.setdefault(rel, []).append((a, b, h))
    for rel, wins in by_file.items():
        for a, b, h in sorted(wins):
            if ranges and ranges[-1][0] == rel and a <= ranges[-1][2]:
                ranges[-1][2] = max(ranges[-1][2], b)
                ranges[-1][3].add(h)
            else:
                ranges.append([rel, a, b, {h}])
    # ranges sharing any window hash are copies of each other (union-find)
    parent = list(range(len(ranges)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner = {}
    for i, r in enumerate(ranges):
        for h in r[3]:
            if h in owner:
                parent[root(i)] = root(owner[h])
            else:
                owner[h] = i
    groups = {}
    for i, r in enumerate(ranges):
        groups.setdefault(root(i), []).append((r[0], r[1], r[2]))
    out = [g for g in groups.values() if len(g) > 1]
    out.sort(key=lambda g: -max(e - s for _, s, e in g))
    return out


def report(include=None, only=None, limit=10):
    """Compact text report. `only`: keep findings touching these files."""
    files = _code_files(include) if include or only is None else scope_files(only)
    keep = (lambda rels: bool(set(rels) & set(only))) if only is not None else (lambda rels: True)
    lines = []
    names = {k: v for k, v in same_name(files).items() if keep([r for r, _ in v])}
    if names:
        lines.append("Same function name in several files (compare behaviour, then share one):")
        for name, where in sorted(names.items(), key=lambda kv: -len(kv[1]))[:limit]:
            lines.append(f"  {name} x{len(where)}: " + ", ".join(f"{r}:{n}" for r, n in where[:6])
                         + (" ..." if len(where) > 6 else ""))
        if len(names) > limit:
            lines.append(f"  ... {len(names) - limit} more names")
    groups = [g for g in blocks(files) if keep([r for r, _, _ in g])]
    if groups:
        lines.append(f"Identical blocks ({WINDOW}+ significant lines):")
        for g in groups[:limit]:
            size = max(e - s + 1 for _, s, e in g)
            lines.append(f"  ~{size} lines x{len(g)}: " + ", ".join(f"{r}:{s}-{e}" for r, s, e in g[:5])
                         + (" ..." if len(g) > 5 else ""))
        if len(groups) > limit:
            lines.append(f"  ... {len(groups) - limit} more groups")
    return "\n".join(lines) or "no duplicated code found"

"""Git integration for pctl.
Conventional Commits: <type>(<scope>): <desc>

Always ask before committing (print message, require --yes).
"""
import re
import subprocess

from . import paths, tasks, util

TYPE_MAP = {
    "feature": "feat", "bug": "fix", "refactor": "refactor",
    "investigacion": "docs", "chore": "chore",
}

BRANCH_PREFIX = {
    "feature": "feature", "bug": "fix", "refactor": "refactor",
    "investigacion": "investigate", "chore": "chore",
}


def status_line():
    branch = util.git("rev-parse", "--abbrev-ref", "HEAD") or "(no git)"
    dirty = util.git("status", "--porcelain") or ""
    n = len([l for l in dirty.splitlines() if l.strip()])
    return f"branch: {branch} · {n} archivo(s) sin commit"


def recent_commits(n=5):
    out = util.git("log", f"--max-count={n}", "--oneline")
    return out or "(sin commits)"


def branch_name(tid):
    data = tasks.get_data(tid)
    prefix = BRANCH_PREFIX.get(data.get("tipo", "feature"), "feature")
    titulo = data.get("titulo", "")
    safe = re.sub(r"[^a-z0-9]+", "-", titulo.lower().strip())[:40].strip("-")
    return f"{prefix}/{tid}-{safe}"


def build_commit_msg(tid, data=None):
    if data is None:
        data = tasks.get_data(tid)
    ctype = TYPE_MAP.get(data.get("tipo", "feature"), "chore")
    titulo = data.get("titulo", "")
    tid_display = data.get("id", tid)
    scope = data.get("dominio") or data.get("prefix") or ""

    desc = titulo[:72].lower().strip().rstrip(".")

    header = f"{ctype}({scope}): {desc}" if scope else f"{ctype}: {desc}"
    body = f"Closes {tid_display}"
    return f"{header}\n\n{titulo}\n\n{body}"


def commit(tid, yes=False, push=False):
    data = tasks.get_data(tid)
    msg = build_commit_msg(tid, data)

    if not yes:
        return msg

    branch = branch_name(tid)
    current = util.git("rev-parse", "--abbrev-ref", "HEAD") or ""

    if current != branch:
        util.git("checkout", "-b", branch, check=True)

    util.git("commit", "-m", msg, check=True)

    if push:
        util.git("push", "-u", "origin", branch, check=True)

    return msg


def detect_drift():
    diff = util.git("diff", "--name-only")
    if not diff:
        return []

    changed = set(diff.splitlines())
    refs = _all_refs()
    errors = []
    for ref_file, lines_str, source in refs:
        for ch in changed:
            if ref_file in ch or ch in ref_file:
                errors.append(f"{source}: referencia a `{ref_file}:{lines_str}` pero el archivo cambió en el working tree")
    return errors


def _all_refs():
    from . import validate as v
    refs = []
    for md in sorted(paths.TASKS_DIR.rglob("*.md")) + sorted(paths.FLOWS_DIR.rglob("*.md")) + sorted(paths.ARCH_DIR.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        for m in v._REF_PATTERN.finditer(text):
            ls = m.group(2) + (("-" + m.group(3)) if m.group(3) else "")
            refs.append((m.group(1), ls, str(md.relative_to(paths.CONTROL_ROOT))))
    return refs


def create_pr(tid, yes=False):
    data = tasks.get_data(tid)
    titulo = data.get("titulo", "")
    tid_display = data.get("id", tid)
    ctype = TYPE_MAP.get(data.get("tipo", "feature"), "chore")
    scope = data.get("dominio") or ""

    title = f"{ctype}({scope}): {titulo[:60].rstrip('.')}" if scope else f"{ctype}: {titulo[:60].rstrip('.')}"
    body = f"Closes {tid_display}\n\n{titulo}"

    if not yes:
        return f"gh pr create --title \"{title}\" --body \"{body}\""

    util.git("push", check=True)
    try:
        r = subprocess.run(["gh", "pr", "create", "--title", title, "--body", body], capture_output=True, cwd=paths.CONTROL_ROOT.parent, check=True)
        return r.stdout.decode("utf-8", errors="replace").strip() or "PR creado"
    except FileNotFoundError:
        raise ValueError("gh CLI no está disponible")

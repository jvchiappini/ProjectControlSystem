"""Shared helpers used across lib/. Check here before writing a new helper.

`scripts/update.py` must stay standalone (it runs from a fresh upstream
clone), so it never imports this module.
"""
import datetime
import re
import subprocess

from . import paths

PROJECT_ROOT = paths.CONTROL_ROOT.parent
SKIP_DIRS = {".git", ".control", "node_modules", ".venv", "venv", "__pycache__",
             "dist", "build", ".next", "target", "vendor"}
MAX_BYTES = 1_000_000


def today():
    return datetime.date.today().isoformat()


def git(*args, check=False, timeout=None):
    """Run git in the project root and return stripped stdout.

    check=False: None when git is missing, times out or exits non-zero.
    check=True: raise CalledProcessError, or ValueError if git is not installed.
    """
    try:
        r = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True,
                           timeout=timeout, check=check)
    except OSError:
        if check:
            raise ValueError("git no está disponible")
        return None
    except subprocess.SubprocessError:
        if check:
            raise
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="replace").strip()


def project_files(include=None):
    """Relative posix paths of project files, honouring .gitignore.

    Skips SKIP_DIRS (including .control/) unless a path under them is named
    explicitly in `include` (a list of path prefixes that also filters).
    """
    listed = git("ls-files", "--cached", "--others", "--exclude-standard", timeout=20)
    if listed is not None:
        rels = listed.splitlines()
    else:
        rels = [p.relative_to(PROJECT_ROOT).as_posix() for p in PROJECT_ROOT.rglob("*") if p.is_file()]
    prefixes = [p.replace("\\", "/").removeprefix("./").rstrip("/") for p in include or []]
    prefixes = [p for p in prefixes if p and p != "."]
    out = []
    for r in rels:
        if prefixes:
            if any(r == p or r.startswith(p + "/") for p in prefixes):
                out.append(r)
        elif not set(r.split("/")[:-1]) & SKIP_DIRS:
            out.append(r)
    return out


def read_lines(rel):
    """Lines of a project text file; [] for binary, huge or unreadable files."""
    p = PROJECT_ROOT / rel
    try:
        if p.stat().st_size > MAX_BYTES:
            return []
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [] if "\0" in text else text.splitlines()


def next_id(prefix, directory):
    """Next `PREFIX-NNNN` id from the `PREFIX-NNNN.md` files in `directory`."""
    highest = 0
    if directory.exists():
        for f in directory.iterdir():
            m = re.match(rf"^{re.escape(prefix)}-(\d+)\.md$", f.name)
            if m:
                highest = max(highest, int(m.group(1)))
    return f"{prefix}-{highest + 1:04d}"

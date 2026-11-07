#!/usr/bin/env python3
"""ProjectControl installer / updater - declarative, 3-way, never destructive.

SELF-CONTAINED: stdlib + git only. Never imports .control/ modules,
because it replaces them.

HOW IT DECIDES WHAT TO TOUCH
  Upstream ships `.control/framework.json`: the exhaustive list of
  framework files, each with a strategy and its sha256. Anything NOT
  listed there is user data and is never read, written or deleted.

  Locally, `.control/.framework_lock.json` records the hash of every
  framework file as it was installed. Comparing three hashes per file
  (local, installed base, new upstream) tells exactly who changed what:

    local == upstream                 -> already current
    local == base (or a known past    -> untouched by the user: replace
      upstream version)
    user edited, upstream unchanged   -> keep the user's file
    user edited, upstream changed     -> 3-way merge (git merge-file) using
                                         the pristine base copy; if it merges
                                         cleanly, apply it; if not, KEEP the
                                         user's file and stage the upstream
                                         version + a conflict-marked merge in
                                         .control/.update/ for review
    user deleted a framework file     -> respected, not restored
    file dropped by upstream          -> reported, never deleted

  Strategies: managed (rules above), create_only (only created if
  missing: opencode.json, CLAUDE.md, ...), skill_registry (merge rows by
  skill name into skills/_index.md, user rows untouched).

SAFETY
  - backup of every file it changes, `--rollback` restores the last one
  - atomic writes, nothing written in --check / --dry-run
  - the newest update.py always runs the update (self-bootstrap), so old
    installs get new migrations and fixes
  - upstream comes from framework.json `upstream.url` (never the user's
    own `origin` remote)

USAGE
  python .control/scripts/update.py --check          # is there an update? what changed?
  python .control/scripts/update.py --dry-run        # full per-file plan, no changes
  python .control/scripts/update.py                  # apply (asks once)
  python .control/scripts/update.py --yes            # apply without asking
  python .control/scripts/update.py --take-upstream .control/SYSTEM.md   # replace my edited copy
  python .control/scripts/update.py --resolved       # I fixed the staged conflicts
  python .control/scripts/update.py --rollback       # undo the last update
  python .control/scripts/update.py --source ../ProjectControlSystem     # local checkout as upstream

  Fresh install into any project (no .control/ yet):
    git clone --depth 1 <upstream-url> /tmp/pc
    python /tmp/pc/.control/scripts/update.py --source /tmp/pc --target .

  Maintainers (framework repo only):
    python .control/scripts/update.py --build-manifest --version 5.1.0
"""

import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_UPSTREAM = "https://github.com/jvchiappini/ProjectControlSystem.git"
DEFAULT_REF = "main"
MANIFEST_REL = ".control/framework.json"
LOCK_REL = ".control/.framework_lock.json"
BASE_REL = ".control/.framework_base"
STAGE_REL = ".control/.update"
BACKUPS_REL = ".control/.backups"
SCHEMA_REL = ".control/.schema_version"
HISTORY_KEEP = 20

# ---- maintainer spec: which files of this repo are the framework ----
# First matching group wins. Paths are project-root relative (posix).
SPEC = [
    ("skill_registry", [".control/skills/_index.md"]),
    ("create_only", [
        "opencode.json", "AGENTS.md", "CLAUDE.md", ".claude/settings.json",
        ".control/**/.gitkeep",
        ".control/docs/_index.md", ".control/roadmaps/_index.md", ".control/flows/_index.md",
        ".control/tasks/BACKLOG.md", ".control/tasks/IN_PROGRESS.md", ".control/tasks/DONE.md",
    ]),
    ("managed", [
        ".control/SYSTEM.md", ".control/CHANGELOG.md", ".control/*.template",
        ".control/prompts/*.md", ".control/skills/*.md",
        ".control/scripts/*.py", ".control/scripts/lib/*.py", ".control/scripts/lib/schema.md",
        ".control/frontend/server.py", ".control/frontend/static/*",
        ".control/docs/*/_template.md",
        ".control/roadmaps/phases/PHASE-XXXX.md",
        ".control/roadmaps/initiatives/INITIATIVE-XXXX.md",
        ".control/roadmaps/milestones/M-XXXX.md",
        ".opencode/agents/project-control.md",
    ]),
]
NEVER_SHIP = {MANIFEST_REL, LOCK_REL, SCHEMA_REL}

# create_only files the user already has: suggest (never apply) the integration line
INTEGRATION_HINTS = {
    "CLAUDE.md": "add a line '@AGENTS.md' so Claude Code loads the ProjectControl instructions",
    "AGENTS.md": "add: 'Session start: run `python .control/scripts/pctl.py brief`; rules in .control/SYSTEM.md'",
    ".claude/settings.json": "add a SessionStart hook with command "
                             "`python .control/scripts/pctl.py brief` (see README, 'Claude Code')",
    "opencode.json": "make sure 'instructions' includes '.control/SYSTEM.md'",
}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

class _C:
    on = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    @classmethod
    def c(cls, code, t):
        return f"\033[{code}m{t}\033[0m" if cls.on else t


def bold(t): return _C.c("1", t)
def red(t): return _C.c("31", t)
def green(t): return _C.c("32", t)
def yellow(t): return _C.c("33", t)
def faint(t): return _C.c("2", t)


def log(msg, level="info"):
    tag = {"ok": green("[ok]  "), "warn": yellow("[warn]"), "err": red("[err] "),
           "info": "[info]"}[level]
    print(f"  {tag} {msg}")


def header(title):
    print()
    print(bold("=" * 70))
    print("  " + bold(title))
    print(bold("=" * 70))


class Fatal(Exception):
    def __init__(self, msg, hint=None):
        super().__init__(msg)
        self.hint = hint


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def norm(data):
    """Line-ending agnostic content (hashes must not depend on autocrlf)."""
    return data.replace(b"\r\n", b"\n")


def sha(data):
    return hashlib.sha256(norm(data)).hexdigest()


def read_bytes(p):
    try:
        return p.read_bytes()
    except OSError:
        return None


def read_json(p, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def atomic_write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=f".{p.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, str(p))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(p, obj):
    atomic_write(p, (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def git(args, cwd=None, timeout=120):
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        return r.stdout, r.stderr.decode("utf-8", "replace").strip(), r.returncode
    except FileNotFoundError:
        return b"", "git is not installed or not in PATH", 127
    except subprocess.TimeoutExpired:
        return b"", "git timed out", 124


def glob_to_re(pattern):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


def classify(rel):
    if rel in NEVER_SHIP or "/proposed/" in rel or "__pycache__" in rel:
        return None
    for strategy, patterns in SPEC:
        if any(glob_to_re(p).match(rel) for p in patterns):
            return strategy
    return None


def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v or "0"))) or (0,)


def ask(prompt, choices, default):
    if not sys.stdin.isatty():
        return default
    while True:
        try:
            a = input(f"  {prompt} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "q" if "q" in choices else default
        if not a:
            return default
        if a[0] in choices:
            return a[0]


# ---------------------------------------------------------------------------
# Maintainer: build framework.json from the framework repo
# ---------------------------------------------------------------------------

def build_manifest(root, version):
    # tracked + new (untracked, not ignored) files, so a release can be built before committing
    out, err, rc = git(["ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root)
    if rc != 0:
        raise Fatal("--build-manifest must run inside the framework git repo", err)
    files = [f for f in out.decode("utf-8").split("\0") if f]
    existing = read_json(root / MANIFEST_REL, {}) or {}
    entries = {}
    for rel in sorted(set(files)):
        strategy = classify(rel)
        if not strategy or not (root / rel).is_file():
            continue
        current = sha((root / rel).read_bytes())
        # inherit history from the previous manifest (survives shallow clones/rewrites)
        prev = (existing.get("files") or {}).get(rel) or {}
        known = set(prev.get("known", [])) | ({prev["sha256"]} if prev.get("sha256") else set())
        log_out, _, _ = git(["log", "--format=%H", "--", rel], cwd=root)
        for commit in log_out.decode().split():
            blob, _, brc = git(["show", f"{commit}:{rel}"], cwd=root)
            if brc == 0:
                known.add(sha(blob))
        known.discard(current)
        entries[rel] = {"strategy": strategy, "sha256": current, "known": sorted(known)}
    manifest = {
        "name": "ProjectControl",
        "version": version,
        "schema": max(m[0] for m in MIGRATIONS),
        "upstream": existing.get("upstream") or {"url": DEFAULT_UPSTREAM, "ref": DEFAULT_REF},
        "generated": datetime.date.today().isoformat(),
        "files": entries,
    }
    write_json(root / MANIFEST_REL, manifest)
    counts = {}
    for e in entries.values():
        counts[e["strategy"]] = counts.get(e["strategy"], 0) + 1
    log(f"framework.json v{version}: {len(entries)} files {counts}", "ok")


# ---------------------------------------------------------------------------
# Schema migrations (run once each, in order, recorded in .schema_version)
# Every migration must be idempotent and must only touch what it names.
# ---------------------------------------------------------------------------

def _m1_dirs(ctl):
    for d in ["architecture", "tasks", "sessions", "decisions", "flows", "diagrams/flows",
              "skills/proposed", "scripts/lib/proposed", "prompts",
              "roadmaps/phases", "roadmaps/initiatives", "roadmaps/milestones"]:
        (ctl / d).mkdir(parents=True, exist_ok=True)


def _m2_noop(ctl):
    pass  # templates are shipped as managed files now


def _gitignore_edit(ctl, add=(), remove=()):
    gi = ctl.parent / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    changed = False
    for r in remove:
        if r in lines:
            lines = [l for l in lines if l != r]
            changed = True
            log(f".gitignore: removed '{r}'", "ok")
    missing = [a for a in add if a not in lines]
    if missing:
        marker = "# ProjectControl runtime state (added by update.py)"
        if marker not in lines:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(marker)
        lines += missing
        changed = True
    if changed:
        atomic_write(gi, ("\n".join(lines) + "\n").encode("utf-8"))


def _m3_gitignore(ctl):
    _gitignore_edit(ctl, add=[".control/.tasks_index.json", ".control/.events.ndjson",
                              ".control/.positions.json", ".control/.control.lock"])


def _m4_roadmaps(ctl):
    _m1_dirs(ctl)


def _m5_fix_gitignore(ctl):
    # v4 wrongly ignored the user's roadmaps; also ignore new runtime files
    _gitignore_edit(ctl, add=[".control/.backups/", ".control/.update/",
                              ".control/.update_check.json", "__pycache__/"],
                    remove=[".control/roadmaps/"])


MIGRATIONS = [
    (1, "Ensure standard directories", _m1_dirs),
    (2, "Templates (no-op, now shipped by manifest)", _m2_noop),
    (3, "Ignore runtime files in .gitignore", _m3_gitignore),
    (4, "Create roadmaps directories", _m4_roadmaps),
    (5, "Stop ignoring .control/roadmaps/; ignore update/backup state", _m5_fix_gitignore),
]


def run_migrations(ctl, target_schema):
    cur = (read_json(ctl.parent / SCHEMA_REL, {}) or {}).get("version", 0)
    ran = []
    for v, desc, fn in MIGRATIONS:
        if cur < v <= target_schema:
            fn(ctl)
            write_json(ctl.parent / SCHEMA_REL, {"version": v})
            ran.append(f"{v}: {desc}")
            log(f"migration {v}: {desc}", "ok")
    return ran


# ---------------------------------------------------------------------------
# Upstream acquisition
# ---------------------------------------------------------------------------

def acquire(source, ref, tmp_holder):
    """Return (path_to_upstream_checkout, commit_or_None, label)."""
    if source and Path(source).is_dir():
        p = Path(source).resolve()
        out, _, rc = git(["rev-parse", "HEAD"], cwd=p)
        return p, (out.decode().strip() if rc == 0 else None), str(p)
    url = source or DEFAULT_UPSTREAM
    tmp = Path(tempfile.mkdtemp(prefix="pctl-upstream-"))
    tmp_holder.append(tmp)
    log(f"downloading {url} ({ref})...")
    _, err, rc = git(["clone", "--depth", "1", "--branch", ref, "--quiet", url, str(tmp / "src")])
    if rc != 0:
        raise Fatal(f"could not download upstream: {err}",
                    "Check your connection, the URL in .control/framework.json, or pass --source.")
    out, _, _ = git(["rev-parse", "HEAD"], cwd=tmp / "src")
    return tmp / "src", out.decode().strip() or None, url


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def three_way(local, base, upstream):
    """Return (merged_bytes, clean). Needs git; (None, False) if unavailable."""
    with tempfile.TemporaryDirectory(prefix="pctl-merge-") as d:
        d = Path(d)
        for name, data in (("local", local), ("base", base), ("upstream", upstream)):
            (d / name).write_bytes(norm(data))
        out, _, rc = git(["merge-file", "-p", "-L", "yours", "-L", "base", "-L", "upstream",
                          str(d / "local"), str(d / "base"), str(d / "upstream")])
        # exit code: 0 clean, 1..127 number of conflicts, anything else = error
        if rc < 0 or rc > 127 or (rc in (124, 127) and not out):
            return None, False
        return out, rc == 0


def registry_merge(local, upstream):
    """Append upstream skill rows whose name is not registered locally."""
    def rows(text):
        return [l for l in text.splitlines() if l.startswith("| SK-")]

    def name(row):
        parts = [p.strip() for p in row.strip("|").split("|")]
        return parts[1] if len(parts) > 1 else ""

    ltext, utext = local.decode("utf-8"), upstream.decode("utf-8")
    lrows = rows(ltext)
    have = {name(r) for r in lrows}
    used = {int(m) for r in lrows for m in re.findall(r"^\| SK-(\d+)", r)}
    added = []
    for r in rows(utext):
        if name(r) in have:
            continue
        sid = int(re.findall(r"^\| SK-(\d+)", r)[0])
        if sid in used:
            sid = max(used) + 1
            r = re.sub(r"^\| SK-\d+", f"| SK-{sid:04d}", r)
        used.add(sid)
        added.append(r)
    if not added:
        return None, []
    lines = ltext.rstrip("\n").split("\n") + added
    return ("\n".join(lines) + "\n").encode("utf-8"), [name(r) for r in added]


def plan_updates(root, up_root, manifest, lock, take_upstream):
    base_dir = root / BASE_REL
    lock_files = (lock or {}).get("files", {})
    plan = []
    for rel, meta in sorted(manifest["files"].items()):
        strategy = meta.get("strategy", "managed")
        up = read_bytes(up_root / rel)
        if up is None:
            plan.append({"rel": rel, "action": "error", "why": "missing in upstream checkout"})
            continue
        up_h = sha(up)
        loc = read_bytes(root / rel)
        loc_h = sha(loc) if loc is not None else None
        item = {"rel": rel, "strategy": strategy, "data": up, "up_h": up_h}

        if strategy == "create_only":
            if loc is None:
                item.update(action="add", why="new")
            elif loc_h == up_h:
                item.update(action="current", why="already current")
            else:
                item.update(action="skip", why="exists (yours)")
                if rel in INTEGRATION_HINTS:
                    item["hint"] = INTEGRATION_HINTS[rel]
        elif strategy == "skill_registry":
            if loc is None:
                item.update(action="add", why="new")
            else:
                merged, names = registry_merge(loc, up)
                if merged:
                    item.update(action="registry", data=merged, why="register " + ", ".join(names))
                else:
                    item.update(action="skip", why="all skills registered")
        else:  # managed
            base_h = lock_files.get(rel)
            known = set(meta.get("known", [])) | ({base_h} if base_h else set())
            if loc is None:
                if base_h and rel not in take_upstream:
                    item.update(action="skip", why="you deleted it (kept deleted)")
                else:
                    item.update(action="add", why="new")
            elif loc_h == up_h:
                item.update(action="current", why="already current")
            elif rel in take_upstream:
                item.update(action="replace", why="--take-upstream")
            elif loc_h in known:
                item.update(action="replace", why="unmodified by you")
            elif base_h == up_h:
                item.update(action="keep", why="your edits; upstream unchanged")
            else:
                base = read_bytes(base_dir / rel)
                merged, clean = (None, False)
                if base is not None:
                    merged, clean = three_way(loc, base, up)
                if clean:
                    item.update(action="merge", data=merged, why="your edits + upstream merged cleanly")
                else:
                    item.update(action="conflict", merged=merged,
                                why="your edits conflict with upstream" if base is not None
                                else "edited by you (no install record to merge against)")
        plan.append(item)

    dropped = sorted(set(lock_files) - set(manifest["files"]))
    return plan, dropped


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

LABELS = {
    "add": (green, "+", "new files"),
    "replace": (green, "~", "updated (you had not modified them)"),
    "merge": (green, "M", "merged with your edits"),
    "registry": (green, "R", "skill registry entries added"),
    "conflict": (yellow, "!", "CONFLICTS - your file kept, upstream staged for review"),
    "keep": (faint, "=", "kept your edited version (upstream unchanged)"),
    "skip": (faint, "-", "left alone"),
    "current": (faint, ".", "already current"),
    "error": (red, "x", "errors"),
}


def print_plan(plan, dropped, verbose):
    by = {}
    for it in plan:
        by.setdefault(it["action"], []).append(it)
    for action in ["add", "replace", "merge", "registry", "conflict", "keep", "skip", "error", "current"]:
        items = by.get(action, [])
        if not items:
            continue
        color, mark, label = LABELS[action]
        print(color(f"  {mark} {len(items):3d} {label}"))
        always = action in ("conflict", "error", "merge", "registry", "keep")
        for it in items:
            if verbose and action != "current" or always or "deleted" in it["why"] or it.get("hint"):
                print(faint(f"        {it['rel']}  ({it['why']})"))
                if it.get("hint"):
                    print(yellow(f"          tip: {it['hint']}"))
    if dropped:
        print(yellow(f"  ? {len(dropped):3d} no longer part of the framework (kept; delete if unused):"))
        for rel in dropped:
            print(faint(f"        {rel}"))


def changelog_since(up_root, installed_version):
    p = up_root / ".control" / "CHANGELOG.md"
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^(?=## v)", text)
    keep = [s.strip() for s in parts[1:]
            if version_tuple(re.match(r"## v(\S+)", s).group(1)) > version_tuple(installed_version)]
    return "\n\n".join(keep)


def counts_line(plan):
    n = lambda a: sum(1 for i in plan if i["action"] == a)  # noqa: E731
    return (f"{n('add')} new, {n('replace')} updated, {n('merge')} merged, "
            f"{n('conflict')} conflicts, {n('keep') + n('skip')} left as you have them")


# ---------------------------------------------------------------------------
# Apply / rollback
# ---------------------------------------------------------------------------

def apply_plan(root, plan, dropped, manifest, commit, source_label, lock):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = root / BACKUPS_REL / f"update-{ts}"
    stage = root / STAGE_REL / ts
    changed, created, conflicts = [], [], []

    # 1. backup everything we are about to modify
    for it in plan:
        if it["action"] in ("replace", "merge", "registry"):
            src = root / it["rel"]
            dst = bdir / "files" / it["rel"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    bdir.mkdir(parents=True, exist_ok=True)
    for rel in (LOCK_REL, MANIFEST_REL, SCHEMA_REL):
        if (root / rel).exists():
            (bdir / "state" / Path(rel).name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, bdir / "state" / Path(rel).name)

    # 2. write
    for it in plan:
        a, rel = it["action"], it["rel"]
        try:
            if a in ("add", "replace", "merge", "registry"):
                atomic_write(root / rel, it["data"])
                (created if a == "add" else changed).append(rel)
            elif a == "conflict":
                atomic_write(stage / (rel + ".upstream"), it["data"])
                if it.get("merged") is not None:
                    atomic_write(stage / (rel + ".merged"), it["merged"])
                conflicts.append(rel)
        except OSError as e:
            log(f"{rel}: {e}", "err")
            raise Fatal(f"write failed on {rel}; run --rollback to restore", str(e))

    # 3. pristine base copies for future 3-way merges + new lock
    files = {}
    for it in plan:
        if it.get("strategy") != "managed" or it["action"] == "error":
            continue
        files[it["rel"]] = it["up_h"]
        atomic_write(root / BASE_REL / it["rel"], norm(read_bytes_from_plan(it)))
    history = (lock or {}).get("history", [])
    history.append({"date": datetime.datetime.now().isoformat(timespec="seconds"),
                    "from": (lock or {}).get("version"), "to": manifest.get("version"),
                    "commit": commit, "changed": len(changed), "added": len(created),
                    "conflicts": conflicts})
    write_json(root / LOCK_REL, {
        "version": manifest.get("version"), "schema": manifest.get("schema"),
        "commit": commit, "source": source_label,
        "installed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "files": files, "history": history[-HISTORY_KEEP:],
    })
    write_json(root / MANIFEST_REL, manifest)
    write_json(bdir / "changes.json", {"changed": changed, "created": created})

    pending = root / STAGE_REL / "pending.json"
    if conflicts:
        write_json(pending, {"date": ts, "dir": f"{STAGE_REL}/{ts}", "conflicts": conflicts})
    elif pending.exists():
        pending.unlink()
    for cache in (root / ".control" / ".update_check.json",):
        if cache.exists():
            cache.unlink()
    return bdir, stage, changed, created, conflicts


def read_bytes_from_plan(it):
    # base copy must be the UPSTREAM content (what "installed" means), not a merge result
    return it["up_data"] if "up_data" in it else it["data"]


def rollback(root, assume_yes):
    bdirs = sorted((root / BACKUPS_REL).glob("update-*"))
    if not bdirs:
        raise Fatal("no update backup found to roll back")
    b = bdirs[-1]
    changes = read_json(b / "changes.json", {}) or {}
    print(f"  Rolling back {b.name}: restore {len(changes.get('changed', []))} file(s), "
          f"remove {len(changes.get('created', []))} file(s) the update created.")
    if not assume_yes and ask("Proceed? [y/N]", "yn", "n") != "y":
        print("  Aborted (non-interactive: pass --yes).")
        return
    for rel in changes.get("changed", []):
        src = b / "files" / rel
        if src.exists():
            atomic_write(root / rel, src.read_bytes())
    for rel in changes.get("created", []):
        p = root / rel
        if p.exists():
            p.unlink()
    for name, rel in (("framework.json", MANIFEST_REL), (".framework_lock.json", LOCK_REL),
                      (".schema_version", SCHEMA_REL)):
        src = b / "state" / name
        if src.exists():
            atomic_write(root / rel, src.read_bytes())
    shutil.move(str(b), str(b.with_name(b.name + "-rolledback")))
    log("rollback complete", "ok")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(description="Install/update ProjectControl safely.",
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("USAGE", 1)[1])
    p.add_argument("--check", action="store_true", help="report whether an update exists and what changed")
    p.add_argument("--dry-run", action="store_true", help="show the full per-file plan, change nothing")
    p.add_argument("--yes", "-y", action="store_true", help="apply without asking")
    p.add_argument("--source", help="upstream git URL or local checkout (default: framework.json upstream)")
    p.add_argument("--ref", help="upstream branch/tag (default: framework.json upstream ref)")
    p.add_argument("--target", help="project root to install into (default: this script's project)")
    p.add_argument("--take-upstream", action="append", default=[], metavar="PATH",
                   help="replace your edited copy of PATH with upstream (repeatable)")
    p.add_argument("--resolved", action="store_true", help="mark staged conflicts as resolved")
    p.add_argument("--rollback", action="store_true", help="undo the last applied update")
    p.add_argument("--build-manifest", action="store_true", help="(maintainers) regenerate framework.json")
    p.add_argument("--version", dest="new_version", help="version for --build-manifest")
    p.add_argument("--no-bootstrap", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--no-color", action="store_true")
    # legacy flags from v4 (accepted, mapped)
    p.add_argument("--accept-all", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--reject-all", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    return p.parse_args(argv)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = parse_args(argv)
    if args.no_color:
        _C.on = False
    if args.accept_all:
        args.yes = True
    for stream in (sys.stdout, sys.stderr):
        try:
            # pipes (agents, hooks) get UTF-8; real consoles keep their encoding
            stream.reconfigure(errors="replace", **({} if stream.isatty() else {"encoding": "utf-8"}))
        except (AttributeError, ValueError):
            pass

    root = Path(args.target).resolve() if args.target else Path(__file__).resolve().parents[2]
    tmp_holder = []
    try:
        if args.build_manifest:
            if not args.new_version:
                raise Fatal("--build-manifest needs --version X.Y.Z")
            build_manifest(root, args.new_version)
            return 0
        if args.rollback:
            rollback(root, args.yes)
            return 0
        if args.resolved:
            pend = root / STAGE_REL / "pending.json"
            if pend.exists():
                pend.unlink()
            log("staged conflicts marked as resolved", "ok")
            return 0
        return run(args, argv, root, tmp_holder)
    except Fatal as e:
        print()
        print(red(f"  FATAL: {e}"))
        if e.hint:
            print(faint(f"  {e.hint}"))
        return 1
    except KeyboardInterrupt:
        print("\n  Interrupted. Nothing was written unless reported above.")
        return 130
    finally:
        for t in tmp_holder:
            shutil.rmtree(t, ignore_errors=True)


def run(args, argv, root, tmp_holder):
    local_manifest = read_json(root / MANIFEST_REL, {}) or {}
    lock = read_json(root / LOCK_REL)
    up_cfg = local_manifest.get("upstream") or {}
    ref = args.ref or up_cfg.get("ref") or DEFAULT_REF
    source = args.source or up_cfg.get("url") or DEFAULT_UPSTREAM

    up_root, commit, label = acquire(source, ref, tmp_holder)

    # Self-bootstrap: the NEWEST update.py performs the update.
    up_script = up_root / ".control" / "scripts" / "update.py"
    if not args.no_bootstrap and up_script.exists() and \
            sha(up_script.read_bytes()) != sha(Path(__file__).read_bytes()):
        log("running the updater shipped with the new version...")
        child, skip = [], False
        for a in argv:
            if skip:
                skip = False
                continue
            if a in ("--source", "--target"):
                skip = True
                continue
            if a.startswith(("--source=", "--target=")):
                continue
            child.append(a)
        cmd = [sys.executable, str(up_script), "--no-bootstrap", "--source", str(up_root),
               "--target", str(root)] + child
        if commit:
            os.environ["PCTL_UPSTREAM_COMMIT"] = commit
        os.environ["PCTL_UPSTREAM_LABEL"] = label
        return subprocess.call(cmd)
    commit = commit or os.environ.get("PCTL_UPSTREAM_COMMIT")
    label = os.environ.get("PCTL_UPSTREAM_LABEL", label)

    manifest = read_json(up_root / MANIFEST_REL)
    if not manifest or "files" not in manifest:
        raise Fatal("upstream has no .control/framework.json", "That upstream is older than v5 or not ProjectControl.")

    installed_v = (lock or {}).get("version") or local_manifest.get("version") or \
        str((read_json(root / SCHEMA_REL, {}) or {}).get("version", "0"))
    plan, dropped = plan_updates(root, up_root, manifest, lock, set(args.take_upstream))
    for it in plan:
        if it["action"] in ("merge", "registry"):
            it["up_data"] = read_bytes(up_root / it["rel"])

    mode = "check" if args.check else ("dry-run" if args.dry_run else "apply")
    header(f"PROJECTCONTROL {'UPDATE CHECK' if mode == 'check' else 'UPDATE'}")
    print(f"  Project:    {root}")
    print(f"  Installed:  v{installed_v}" + (f" ({lock['commit'][:10]})" if lock and lock.get("commit") else
                                              "  (no install record - first managed update)"))
    print(f"  Upstream:   v{manifest.get('version')} ({(commit or '?')[:10]}) from {label}")
    print()

    pending_work = [i for i in plan if i["action"] in ("add", "replace", "merge", "registry", "conflict")]
    schema_cur = (read_json(root / SCHEMA_REL, {}) or {}).get("version", 0)
    needs_migr = schema_cur < manifest.get("schema", 0)

    notes = changelog_since(up_root, installed_v)
    if mode == "check":
        _write_check_cache(root, lock, commit, manifest, bool(pending_work or needs_migr))
        if not pending_work and not needs_migr:
            print(green("  You are up to date."))
            return 0
        print(bold(f"  Update available: {counts_line(plan)}"))
        if notes:
            print()
            print(bold("  What's new:"))
            for line in notes.splitlines():
                print("    " + line)
        print()
        print(faint("  Preview: update.py --dry-run   Apply: update.py"))
        return 0

    print_plan(plan, dropped, verbose=(mode == "dry-run"))
    if needs_migr:
        print(f"  * schema migrations {schema_cur} -> {manifest.get('schema')}")
    if mode == "dry-run":
        print()
        print(yellow("  DRY RUN - nothing was written."))
        return 0
    if not pending_work and not needs_migr and lock and lock.get("commit") == commit:
        print()
        print(green("  Already up to date."))
        return 0

    print()
    if not args.yes:
        while True:
            a = ask("Apply this update? [y]es / [n]o / [d]iff of conflicts+merges >", "ynd", "n")
            if a == "d":
                for it in plan:
                    if it["action"] in ("merge", "conflict"):
                        _show_diff(root, it)
                continue
            if a != "y":
                print("  Nothing changed.")
                return 0
            break

    bdir, stage, changed, created, conflicts = apply_plan(root, plan, dropped, manifest, commit, label, lock)
    ran = run_migrations(root / ".control", manifest.get("schema", 0))

    pctl = root / ".control" / "scripts" / "pctl.py"
    if pctl.exists() and (root / ".control" / "PROJECT.md").exists():
        r = subprocess.run([sys.executable, str(pctl), "reindex"], cwd=root, capture_output=True, text=True)
        log("indexes regenerated" if r.returncode == 0 else f"reindex failed: {r.stderr.strip()[:200]}",
            "ok" if r.returncode == 0 else "warn")

    header("UPDATE COMPLETE")
    print(f"  {len(created)} added, {len(changed)} updated/merged, {len(ran)} migration(s).")
    print(faint(f"  Backup: {bdir}   (undo: update.py --rollback)"))
    if conflicts:
        print()
        print(yellow(f"  {len(conflicts)} file(s) need your review. Your versions were NOT changed."))
        print(f"  Staged in {stage}:")
        for rel in conflicts:
            print(f"    {rel}.upstream   <- new version")
            if (stage / (rel + ".merged")).exists():
                print(f"    {rel}.merged     <- merge attempt with conflict markers")
        print(faint("  Merge by hand, or take upstream: update.py --take-upstream <path>. "
                    "Then: update.py --resolved"))
    if notes:
        print()
        print(bold("  What's new:"))
        for line in notes.splitlines()[:40]:
            print("    " + line)
    return 0


def _write_check_cache(root, lock, commit, manifest, available):
    try:
        write_json(root / ".control" / ".update_check.json", {
            "status": "available" if available else "up_to_date",
            "installed": {"version": (lock or {}).get("version"), "commit": (lock or {}).get("commit")},
            "remote_commit": commit, "latest_version": manifest.get("version"),
            "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "message": "run `python .control/scripts/update.py`" if available else "",
        })
    except OSError:
        pass


def _show_diff(root, it):
    loc = (read_bytes(root / it["rel"]) or b"").decode("utf-8", "replace").splitlines(True)
    new = (it.get("merged") or it["data"]).decode("utf-8", "replace").splitlines(True)
    diff = list(difflib.unified_diff(loc, new, f"yours/{it['rel']}", f"result/{it['rel']}", n=2))
    print(bold(f"\n  --- {it['rel']} ({it['why']})"))
    for line in diff[:80]:
        line = line.rstrip("\n")
        print(green(line) if line.startswith("+") else red(line) if line.startswith("-") else line)
    if len(diff) > 80:
        print(faint(f"  ... {len(diff) - 80} more lines"))


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""ProjectControlSystem self-update - professional, safe, interactive.

SELF-CONTAINED: This script must NOT import any .control/ module (not
pctl.py, not lib/*). It relies ONLY on Python stdlib and git. This is
because it OVERWRITES those very files during the update, so importing
them would race against the file replacement or fail if the old version
had a different API.

It must also be backward-compatible: it must run correctly on ANY
previous version of the framework, including versions that:
  - Did not have an update.py script
  - Had a different directory structure
  - Had a different pctl.py or lib module API
  - Had no pctl.py at all

Safety guarantees:
  - User data is NEVER deleted or overwritten. Only files matching
    FRAMEWORK_GLOBS are candidates for update.
  - Before overwriting any existing file, the user is asked explicitly
    (unless --accept-all or --reject-all is used).
  - A full backup of .control/ is created before any mutation.
  - File writes are atomic (temp + rename).

Usage:
    python .control/scripts/update.py                  # interactive
    python .control/scripts/update.py --dry-run        # preview only
    python .control/scripts/update.py --accept-all     # auto-accept overwrites
    python .control/scripts/update.py --reject-all     # only add missing files
    python .control/scripts/update.py --ref=origin/main
"""

import argparse
import datetime
import difflib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTROL_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_DIR = CONTROL_ROOT / ".backups"
PROJECT_ROOT = CONTROL_ROOT.parent
SCHEMA_FILE = CONTROL_ROOT / ".schema_version"
CHANGELOG_FILE = CONTROL_ROOT / "CHANGELOG.md"

FRAMEWORK_GLOBS = [
    "SYSTEM.md",
    "ROADMAP.md.template",
    "PROJECT.md.template",
    "GOALS.md.template",
    "CONTEXT.md.template",
    "prompts/*.md",
    "skills/*.md",
    "scripts/pctl.py",
    "scripts/update.py",
    "scripts/lib/*.py",
    "frontend/server.py",
    "frontend/static/*",
    "docs/**/_template.md",
    "roadmaps/phases/PHASE-XXXX.md",
    "roadmaps/initiatives/INITIATIVE-XXXX.md",
    "roadmaps/milestones/M-XXXX.md",
    "roadmaps/_index.md",
    "docs/_index.md",
]

USER_DATA_GLOBS = [
    "PROJECT.md",
    "GOALS.md",
    "ROADMAP.md",
    "CONTEXT.md",
    "tasks/**/*",
    "sessions/**/*",
    "decisions/**/*",
    "architecture/**/*",
    "flows/**/*",
    "roadmaps/**/*",
    "docs/**/*.md",
    "skills/proposed/**/*",
    "scripts/lib/proposed/**/*",
]

BACKUP_EXCLUDE_NAMES = {
    ".backups", "__pycache__", ".tasks_index.json",
    ".events.ndjson", ".positions.json", ".control.lock",
    "CHANGELOG.md",
}


# ---------------------------------------------------------------------------
# Terminal colors (auto-disabled when not a TTY)
# ---------------------------------------------------------------------------

class _Colors:
    def __init__(self):
        self._enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def _c(self, code, text):
        return f"\033[{code}m{text}\033[0m" if self._enabled else text

    def bold(self, text): return self._c("1", text)
    def red(self, text): return self._c("31", text)
    def green(self, text): return self._c("32", text)
    def yellow(self, text): return self._c("33", text)
    def blue(self, text): return self._c("34", text)
    def faint(self, text): return self._c("2", text)


C = _Colors()


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _log(msg, level="info"):
    prefix = {
        "ok": C.green("  [ok] "),
        "warn": C.yellow("  [warn] "),
        "err": C.red("  [err] "),
        "info": C.blue("  [info] "),
    }.get(level, "  [info] ")
    print(prefix + msg)


def _print_header(title):
    print()
    print(C.bold("=" * 70))
    print("  " + C.bold(title))
    print(C.bold("=" * 70))


def _print_section(title):
    print()
    print(C.bold(title))
    print(C.bold("-" * len(title)))


def _fatal(msg, hint=None):
    print()
    print(C.red("FATAL: " + msg))
    if hint:
        print(C.faint(hint))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Git helpers (with robust error handling)
# ---------------------------------------------------------------------------

def _git(args, check=False, cwd=None, strip=True):
    """Run git. Returns (stdout, stderr, rc). Never raises."""
    cwd = cwd or PROJECT_ROOT
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=check,
            cwd=cwd,
        )
        out = r.stdout.strip() if strip else r.stdout
        err = r.stderr.strip() if strip else r.stderr
        return out, err, r.returncode
    except FileNotFoundError:
        return "", "git command not found", 127
    except Exception as e:
        return "", str(e), 1


def _require_git():
    _, _, rc = _git(["--version"])
    if rc != 0:
        _fatal("git is not installed or not in PATH.")


def _require_repo():
    _, _, rc = _git(["rev-parse", "--git-dir"])
    if rc != 0:
        _fatal("Not inside a git repository.",
               hint="Run this script from the project root.")


def _origin_url():
    out, _, rc = _git(["remote", "get-url", "origin"])
    return out if rc == 0 else None


def _current_branch():
    out, _, rc = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out if rc == 0 else "unknown"


def _has_uncommitted():
    out, _, rc = _git(["status", "--porcelain"])
    return bool(out.strip()) if rc == 0 else True


def _fetch(ref):
    _log("Fetching from origin...")
    # Fetch all refs from origin. The remote-tracking branch for the ref
    # (e.g. origin/main) will be updated.
    _, err, rc = _git(["fetch", "--tags", "origin"])
    if rc != 0:
        _log(f"Fetch failed: {err}", level="err")
        return False
    _log("Fetch OK", level="ok")
    return True


def _ls_remote(ref):
    """List all .control/ files from a git ref."""
    out, err, rc = _git(["ls-tree", "-r", "--name-only", ref, ".control/"])
    if rc != 0:
        _log(f"Could not list files at {ref}: {err}", level="err")
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _cat(ref, rel_path):
    """Read file content from a git ref.

    rel_path is the inner path (e.g. SYSTEM.md); git show needs the full
    repository path (.control/SYSTEM.md).
    """
    inner = Path(rel_path).as_posix()
    full_path = f".control/{inner}"
    out, err, rc = _git(["show", f"{ref}:{full_path}"], strip=False)
    if rc != 0:
        _log(f"Could not read {full_path} from {ref}: {err}", level="err")
        return None
    return out


def _diff_log(ref_from, ref_to="HEAD"):
    out, _, _ = _git(["log", "--oneline", f"{ref_from}..{ref_to}", "--", ".control/"])
    return out


def _merge_base(ref):
    out, _, rc = _git(["merge-base", ref, "HEAD"])
    return out if rc == 0 else None


def _is_git_modified(rel_path):
    """Check if a framework file has uncommitted local changes.

    rel_path is the inner path (e.g. SYSTEM.md); git status needs the
    project-relative path (.control/SYSTEM.md).
    """
    project_rel = f".control/{Path(rel_path).as_posix()}"
    out, _, rc = _git(["status", "--porcelain", "--", project_rel])
    return rc == 0 and bool(out.strip())


def _local_file_size(local_path):
    try:
        return local_path.stat().st_size
    except OSError:
        return None


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

def _glob_match(rel_posix, patterns):
    for pat in patterns:
        if Path(pat).match(rel_posix):
            return True
    return False


def _classify_files(file_list):
    framework, user_data, unknown = [], [], []
    prefix = ".control/"
    for f in file_list:
        posix = Path(f).as_posix()
        # Strip the .control/ prefix so patterns match (e.g. SYSTEM.md, not .control/SYSTEM.md)
        if posix.startswith(prefix):
            inner = posix[len(prefix):]
        else:
            inner = posix
        rel = Path(inner)
        if _glob_match(inner, FRAMEWORK_GLOBS):
            framework.append(rel)
        elif _glob_match(inner, USER_DATA_GLOBS):
            user_data.append(rel)
        else:
            unknown.append(rel)
    return framework, user_data, unknown


# ---------------------------------------------------------------------------
# Safe file operations
# ---------------------------------------------------------------------------

def _normalize_text(s):
    """Normalize line endings to LF for comparison."""
    return (s or "").replace("\r\n", "\n").replace("\r", "\n")


def _is_same_content(local_path, content):
    if not local_path.exists():
        return False
    try:
        local = local_path.read_text(encoding="utf-8")
        return _normalize_text(local) == _normalize_text(content)
    except Exception:
        return False


def _atomic_write(local_path, content):
    """Write content atomically: temp file then rename."""
    local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = local_path.with_suffix(local_path.suffix + ".update-tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(local_path)
        return True
    except OSError as e:
        _log(f"Failed to write {local_path}: {e}", level="err")
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _human_size(n):
    if n is None:
        return "?"
    for unit in ["B", "KB", "MB"]:
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} GB"


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _backup():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUPS_DIR / f"pre_update_{ts}"
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    def _ignore(src, names):
        return [n for n in names if n in BACKUP_EXCLUDE_NAMES or n == "__pycache__"]

    try:
        shutil.copytree(CONTROL_ROOT, dst, ignore=_ignore)
        _log(f"Backup created: {dst}", level="ok")
        return dst
    except Exception as e:
        _log(f"Backup failed: {e}", level="err")
        return None


def _restore_hint(backup_path):
    if backup_path and backup_path.exists():
        return f"To restore: cp -r {backup_path}/* .control/"
    return ""


# ---------------------------------------------------------------------------
# Diff display
# ---------------------------------------------------------------------------

def _show_diff(rel_path, local_content, remote_content, max_lines=40):
    diff = list(difflib.unified_diff(
        local_content.splitlines(keepends=True),
        remote_content.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
        n=2,
    ))
    if not diff:
        print("  (no textual diff)")
        return

    total = len(diff)
    shown = diff[:max_lines]
    print()
    for line in shown:
        line = line.rstrip("\n")
        if line.startswith("+"):
            print(C.green(line))
        elif line.startswith("-"):
            print(C.red(line))
        elif line.startswith("@@"):
            print(C.yellow(line))
        else:
            print(line)
    if total > max_lines:
        print(C.faint(f"  ... {total - max_lines} more lines (use git diff to see full)"))
    print()


# ---------------------------------------------------------------------------
# Interactive prompt
# ---------------------------------------------------------------------------

def _prompt_overwrite(rel_path, local_path, remote_content, locally_modified):
    """Ask the user what to do about an overwrite. Returns 'yes', 'no', 'all', or 'quit'."""
    local_size = _human_size(_local_file_size(local_path))
    remote_size = _human_size(len(remote_content.encode("utf-8")))

    print()
    if locally_modified:
        print(C.yellow("  ! WARNING: local file has uncommitted changes"))
        print(C.red(f"     {rel_path}"))
        print(f"     Local: {local_size}  |  Remote: {remote_size}")
        print(C.faint("     Overwriting will discard your local changes."))
    else:
        print(C.yellow("  ! About to overwrite existing framework file"))
        print(f"     {rel_path}")
        print(f"     Local: {local_size}  |  Remote: {remote_size}")

    opts = "[y]es  [n]o  [d]iff  [a]ll  [q]uit"
    while True:
        try:
            answer = input("  " + opts + "> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

        if not answer:
            continue
        if answer in ("y", "yes"):
            return "yes"
        if answer in ("n", "no"):
            return "no"
        if answer in ("a", "all"):
            return "all"
        if answer in ("q", "quit"):
            return "quit"
        if answer in ("d", "diff"):
            try:
                local_content = local_path.read_text(encoding="utf-8")
            except Exception:
                local_content = ""
            _show_diff(rel_path, local_content, remote_content)
            continue
        print("  Please enter y, n, d, a, or q.")


# ---------------------------------------------------------------------------
# Built-in migration engine
# ---------------------------------------------------------------------------

_MIGRATIONS = []


def _migration(from_v, to_v, description, fn):
    _MIGRATIONS.append((from_v, to_v, description, fn))


def _current_schema():
    if SCHEMA_FILE.exists():
        try:
            return json.loads(SCHEMA_FILE.read_text(encoding="utf-8")).get("version", 0)
        except (json.JSONDecodeError, OSError):
            return 0
    return 0


def _write_schema(version):
    SCHEMA_FILE.write_text(json.dumps({"version": version}, indent=2), encoding="utf-8")


def _run_migrations(start_version):
    ran = []
    sorted_migs = sorted(_MIGRATIONS, key=lambda m: m[0])
    for from_v, to_v, desc, fn in sorted_migs:
        if start_version >= to_v:
            continue
        if _current_schema() < to_v:
            _log(f"Running migration {from_v} -> {to_v}: {desc}")
            try:
                fn(CONTROL_ROOT)
                _write_schema(to_v)
                ran.append((from_v, to_v, desc))
                _log(f"Migration {from_v} -> {to_v}: OK", level="ok")
            except Exception as e:
                _log(f"Migration {from_v} -> {to_v} FAILED: {e}", level="err")
                raise
    return ran


# ---- Define migrations ----

def _migrate_ensure_dirs(root):
    dirs = [
        "architecture", "tasks", "sessions", "decisions", "flows",
        "diagrams", "diagrams/flows", "skills", "skills/proposed",
        "scripts", "scripts/lib", "scripts/lib/proposed",
        "prompts", "roadmaps", "roadmaps/phases", "roadmaps/initiatives",
        "roadmaps/milestones",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)


def _migrate_create_templates(root):
    templates = {
        "PROJECT.md.template": "# Project: <name>\n\n## Description\n\n## Type\n\n## Main stack\n\n## General status\n",
        "GOALS.md.template": "# Goals\n\n## Objective\n\n## Success criteria\n- [ ]\n\n## Out of scope\n",
        "CONTEXT.md.template": "# Context memory\n\n## What this project is\n\n## Tacit conventions\n\n## Things to watch out for\n\n## Perceived status\n\n## Last relevant session\n",
    }
    for name, content in templates.items():
        fpath = root / name
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")
            _log(f"Created missing template: {name}")


def _migrate_gitignore(root):
    gitignore = root.parent / ".gitignore"
    entries = [
        ".control/scripts/__pycache__/",
        ".control/.tasks_index.json",
        ".control/.events.ndjson",
        ".control/.positions.json",
        ".control/.control.lock",
        ".control/roadmaps/",
    ]
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8")
        additions = [e for e in entries if e not in existing]
        if additions:
            gitignore.write_text(existing + "\n" + "\n".join(additions) + "\n", encoding="utf-8")
    else:
        gitignore.write_text("\n".join(entries) + "\n", encoding="utf-8")


def _migrate_roadmaps_dir(root):
    for d in ["roadmaps", "roadmaps/phases", "roadmaps/initiatives", "roadmaps/milestones"]:
        (root / d).mkdir(parents=True, exist_ok=True)


_migration(0, 1, "Ensure standard directories", _migrate_ensure_dirs)
_migration(1, 2, "Create missing templates", _migrate_create_templates)
_migration(2, 3, "Add .gitignore entries", _migrate_gitignore)
_migration(3, 4, "Create roadmaps directories", _migrate_roadmaps_dir)


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------

def _append_changelog(new_version, migrations_ran, log_lines, deprecations=None):
    header = f"## v{new_version} ({datetime.date.today().isoformat()})"
    parts = [header, ""]
    if migrations_ran:
        parts.append("### Migrations")
        for from_v, to_v, desc in migrations_ran:
            parts.append(f"- `{from_v}->{to_v}`: {desc}")
        parts.append("")
    if deprecations:
        parts.append("### Deprecations")
        for d in deprecations:
            parts.append(f"- {d}")
        parts.append("")
    if log_lines:
        parts.append("### Changes since last update")
        for line in log_lines.strip().splitlines():
            parts.append(f"- {line}")
        parts.append("")
    entry = "\n".join(parts)

    if CHANGELOG_FILE.exists():
        current = CHANGELOG_FILE.read_text(encoding="utf-8")
        lines = current.splitlines()
        if lines and lines[0].startswith("# "):
            body = "\n".join(lines[1:]).strip()
            new_content = lines[0] + "\n\n" + entry + "\n" + body + "\n"
        else:
            new_content = entry + "\n" + current
    else:
        new_content = "# ProjectControl Changelog\n\n" + entry + "\n"

    CHANGELOG_FILE.write_text(new_content, encoding="utf-8")
    _log(f"Changelog updated -> v{new_version}")


# ---------------------------------------------------------------------------
# Update plan & execution
# ---------------------------------------------------------------------------

def _compute_plan(framework_files, ref):
    """Build the update plan: list of actions per file."""
    plan = []
    for rel in sorted(framework_files):
        local_path = CONTROL_ROOT / rel
        content = _cat(ref, rel)
        if content is None:
            plan.append({
                "rel": rel,
                "local_path": local_path,
                "action": "error",
                "reason": "could not read from remote",
            })
            continue

        if _is_same_content(local_path, content):
            plan.append({
                "rel": rel,
                "local_path": local_path,
                "action": "skip",
                "reason": "already current",
            })
            continue

        if not local_path.exists():
            plan.append({
                "rel": rel,
                "local_path": local_path,
                "action": "add",
                "content": content,
                "reason": "missing locally",
            })
            continue

        locally_modified = _is_git_modified(rel)
        plan.append({
            "rel": rel,
            "local_path": local_path,
            "action": "overwrite",
            "content": content,
            "locally_modified": locally_modified,
            "reason": "locally modified" if locally_modified else "remote differs",
        })
    return plan


def _execute_plan(plan, mode, dry_run=False):
    """Execute (or simulate) the plan. Returns (updated, skipped, errors, local_modified, aborted)."""
    updated, skipped, errors, local_modified = [], [], [], []
    accept_all = mode == "accept"
    reject_all = mode == "reject"

    for item in plan:
        action = item["action"]
        rel = item["rel"]
        local_path = item["local_path"]

        if action == "error":
            errors.append(f"{rel}: {item['reason']}")
            continue

        if action == "skip":
            skipped.append(rel)
            continue

        if action == "add":
            if dry_run:
                updated.append(rel)
                continue
            if _atomic_write(local_path, item["content"]):
                updated.append(rel)
                _log(f"Added: {rel}", level="ok")
            else:
                errors.append(f"{rel}: failed to write")
            continue

        if action == "overwrite":
            if accept_all:
                decision = "yes"
            elif reject_all:
                decision = "no"
            elif dry_run:
                # In dry-run, assume the user would confirm each overwrite
                # unless reject-all was requested.
                decision = "yes"
            else:
                decision = _prompt_overwrite(
                    rel, local_path, item["content"], item.get("locally_modified", False)
                )

            if decision == "quit":
                _log("Update aborted by user.", level="warn")
                return updated, skipped, errors, local_modified, True  # aborted
            if decision == "all":
                accept_all = True
                decision = "yes"

            if decision == "yes":
                if dry_run:
                    updated.append(rel)
                    if item.get("locally_modified"):
                        local_modified.append(rel)
                    continue
                if _atomic_write(local_path, item["content"]):
                    updated.append(rel)
                    if item.get("locally_modified"):
                        local_modified.append(rel)
                    status = " (overwrote local changes)" if item.get("locally_modified") else ""
                    _log(f"Overwritten: {rel}{status}", level="ok")
                else:
                    errors.append(f"{rel}: failed to write")
            else:
                skipped.append(rel)
                if not dry_run:
                    _log(f"Kept local: {rel}")

    return updated, skipped, errors, local_modified, False


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _report(plan, updated, skipped, errors, local_modified, aborted,
            dry_run, backup_path, log_lines):
    _print_header("PROJECTCONTROL UPDATE SUMMARY")

    counts = {"add": 0, "overwrite": 0, "skip": 0, "error": 0}
    for item in plan:
        counts[item["action"]] = counts.get(item["action"], 0) + 1

    print(f"  Plan items:       {len(plan)}")
    print(f"  New files:        {counts.get('add', 0)}")
    print(f"  Overwrites:       {counts.get('overwrite', 0)}")
    print(f"  Already current:  {counts.get('skip', 0)}")
    print(f"  Read errors:      {counts.get('error', 0)}")
    print()

    if dry_run:
        print(C.yellow("  DRY RUN - no files were changed."))
        print()

    if updated:
        print(C.green(f"  Updated ({len(updated)}):"))
        for rel in sorted(updated):
            print(f"    + {rel}")
        print()

    if local_modified and not dry_run:
        print(C.yellow(f"  Overwritten despite local changes ({len(local_modified)}):"))
        for rel in sorted(local_modified):
            print(f"    ! {rel}")
        print()

    if skipped:
        print(C.blue(f"  Kept local ({len(skipped)}):"))
        for rel in sorted(skipped):
            print(f"    - {rel}")
        print()

    if errors:
        print(C.red(f"  ERRORS ({len(errors)}):"))
        for e in errors:
            print(f"    x {e}")
        print()

    if log_lines:
        print("  Changes since last update:")
        for line in log_lines.strip().splitlines():
            print(f"    {line}")
        print()

    if aborted:
        print(C.yellow("  UPDATE ABORTED by user."))
    elif errors:
        print(C.yellow("  UPDATE COMPLETED WITH ERRORS."))
        hint = _restore_hint(backup_path)
        if hint:
            print(C.faint(f"  {hint}"))
    elif not dry_run:
        print(C.green("  UPDATE COMPLETE."))

    if backup_path and backup_path.exists() and not dry_run:
        print(C.faint(f"  Backup: {backup_path}"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _resolve_mode(args):
    """Resolve the interaction mode from CLI flags (ignoring dry-run)."""
    if args.accept_all:
        return "accept"
    if args.reject_all:
        return "reject"
    return "interactive"


def main():
    parser = argparse.ArgumentParser(
        description="Update ProjectControlSystem framework from a git remote safely.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Safety notes:
  - User data (tasks, sessions, docs, roadmaps, etc.) is NEVER touched.
  - Only framework files listed in FRAMEWORK_GLOBS can be updated.
  - Existing files are overwritten only after explicit confirmation,
    unless --accept-all is used.
  - A full backup of .control/ is created before any change.
        """,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying any file.")
    parser.add_argument("--accept-all", action="store_true",
                        help="Automatically overwrite all differing framework files.")
    parser.add_argument("--reject-all", action="store_true",
                        help="Skip all overwrites; only add missing files.")
    parser.add_argument("--force", action="store_true",
                        help="Proceed even with uncommitted local changes.")
    parser.add_argument("--ref", default="origin/main",
                        help="Remote ref to update from (default: origin/main).")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output.")
    args = parser.parse_args()

    if args.no_color:
        C._enabled = False

    if args.accept_all and args.reject_all:
        _fatal("--accept-all and --reject-all are mutually exclusive.")

    mode = _resolve_mode(args)
    dry_run = args.dry_run
    ref = args.ref

    _require_git()
    _require_repo()

    branch = _current_branch()
    origin = _origin_url()

    _print_header("PROJECTCONTROL UPDATE")
    print(f"  Source ref:       {ref}")
    print(f"  Current branch:   {branch}")
    print(f"  Remote origin:    {origin or C.red('(none)')}")
    print(f"  Interaction mode: {mode}{' (dry-run)' if dry_run else ''}")
    print()

    if not origin:
        _fatal(
            "No git remote 'origin' configured.",
            hint="Add a remote pointing to the ProjectControlSystem repository, e.g.:\n"
                 "  git remote add origin <url>",
        )

    # Uncommitted changes warning
    if _has_uncommitted() and not args.force and not dry_run:
        print(C.yellow("WARNING: You have uncommitted changes."))
        print(C.faint("Commit or stash them first, or use --force to proceed."))
        try:
            yn = input("Continue anyway? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)
        if yn != "y":
            print("Aborted.")
            sys.exit(0)

    # Fetch
    if not _fetch(ref):
        _fatal("Fetch failed.",
               hint="Check your connection and that the ref name is correct.")

    # Verify ref has .control/
    if _cat(ref, "SYSTEM.md") is None:
        print(C.red(f"ERROR: Ref '{ref}' does not exist or has no .control/ directory."))
        print("Available remote refs:")
        out, _, _ = _git(["ls-remote", "--heads", "origin"])
        for line in out.splitlines():
            print(f"  {line}")
        sys.exit(1)

    # Build file lists
    remote_files = _ls_remote(ref)
    if not remote_files:
        _fatal(f"No .control/ files found in ref '{ref}'.")

    framework_files, user_files, unknown = _classify_files(remote_files)
    _log(f"Found {len(framework_files)} framework + {len(user_files)} user files in {ref}")

    if unknown:
        _log(f"{len(unknown)} remote files are not classified as framework or user data; ignored",
             level="warn")

    # Compute plan
    plan = _compute_plan(framework_files, ref)

    # Preview in dry-run mode
    if mode == "dry-run":
        _print_section("Dry-run preview")
        for item in plan:
            rel = item["rel"]
            if item["action"] == "skip":
                continue
            marker = {
                "add": C.green("+"),
                "overwrite": C.yellow("~"),
                "error": C.red("x"),
            }.get(item["action"], "?")
            extra = ""
            if item["action"] == "overwrite" and item.get("locally_modified"):
                extra = C.red(" [local changes]")
            print(f"  {marker} {rel}{extra}")

    # Backup before any mutation (even if plan is empty; cheap)
    backup_path = None
    if not dry_run:
        backup_path = _backup()
        if backup_path is None:
            _fatal("Backup failed; aborting to protect your data.",
                   hint="Check disk space and permissions, then retry.")

    # Compute merge base for changelog
    base = _merge_base(ref)
    log_lines = _diff_log(base) if base else ""

    # Execute plan
    updated, skipped, errors, local_modified, aborted = _execute_plan(plan, mode, dry_run=dry_run)

    # Run migrations
    ran = []
    if not aborted and not dry_run and not errors:
        old_schema = _current_schema()
        try:
            ran = _run_migrations(old_schema)
        except Exception:
            _log("Migrations failed. Framework files were updated, but schema migrations may need manual repair.",
                 level="err")
            errors.append("Schema migrations failed - see log above")

    # Update changelog
    if not aborted and not dry_run and not errors:
        new_version = _current_schema()
        if updated or ran or log_lines:
            _append_changelog(
                new_version=new_version,
                migrations_ran=ran,
                log_lines=log_lines,
            )

    # Report
    _report(
        plan=plan,
        updated=updated,
        skipped=skipped,
        errors=errors,
        local_modified=local_modified,
        aborted=aborted,
        dry_run=dry_run,
        backup_path=backup_path,
        log_lines=log_lines,
    )

    if aborted or errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

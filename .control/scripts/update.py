#!/usr/bin/env python3
"""ProjectControlSystem self-update.

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

Usage:
    python .control/scripts/update.py
    python .control/scripts/update.py --dry-run
    python .control/scripts/update.py --force
    python .control/scripts/update.py --ref=origin/main
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CONTROL_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_DIR = CONTROL_ROOT / ".backups"
PROJECT_ROOT = CONTROL_ROOT.parent
SCHEMA_FILE = CONTROL_ROOT / ".schema_version"

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

CHANGELOG_FILE = CONTROL_ROOT / "CHANGELOG.md"

BACKUP_EXCLUDE_NAMES = {".backups", "__pycache__", ".tasks_index.json",
                        ".events.ndjson", ".positions.json", ".control.lock",
                        "CHANGELOG.md"}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(msg):
    print(f"  [update] {msg}")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(args, check=True, cwd=None):
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True,
                           check=check, cwd=cwd or PROJECT_ROOT)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip() if e.stdout else "", e.stderr.strip() if e.stderr else "", e.returncode
    except FileNotFoundError:
        _log("git not found. Is git installed?")
        sys.exit(1)


def _origin_url():
    out, _, rc = _git(["remote", "get-url", "origin"])
    return out if rc == 0 else None


def _current_branch():
    out, _, rc = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out if rc == 0 else "unknown"


def _has_uncommitted():
    out, _, rc = _git(["status", "--porcelain"])
    return bool(out.strip()) if rc == 0 else True


def _fetch():
    _log("Fetching from origin...")
    out, err, rc = _git(["fetch", "--tags", "origin"])
    if rc != 0:
        _log(f"Fetch failed: {err or out}")
        return False
    _log("Fetch OK")
    return True


def _ls_remote(ref):
    """List all .control/ files from a remote ref."""
    out, _, rc = _git(["ls-tree", "-r", "--name-only", ref, ".control/"])
    if rc != 0 or not out:
        return []
    return out.splitlines()


def _cat(ref, rel_path):
    """Read file content from a git ref."""
    posix = rel_path.as_posix().replace("\\", "/")
    out, _, rc = _git(["show", f"{ref}:{posix}"])
    return out if rc == 0 else None


def _diff_log(ref_from, ref_to="HEAD"):
    out, _, _ = _git(["log", "--oneline", f"{ref_from}..{ref_to}", "--", ".control/"])
    return out


def _merge_base(ref="origin/main"):
    out, _, rc = _git(["merge-base", ref, "HEAD"])
    return out if rc == 0 else None


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
    for f in file_list:
        rel = Path(f)
        posix = rel.as_posix()
        if _glob_match(posix, FRAMEWORK_GLOBS):
            framework.append(rel)
        elif _glob_match(posix, USER_DATA_GLOBS):
            user_data.append(rel)
        else:
            unknown.append(rel)
    return framework, user_data, unknown


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _backup():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUPS_DIR / f"pre_update_{ts}"
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    def _ignore(src, names):
        return [n for n in names if n in BACKUP_EXCLUDE_NAMES or n == "__pycache__"]

    shutil.copytree(CONTROL_ROOT, dst, ignore=_ignore)
    _log(f"Backup -> {dst.name}")
    return dst


# ---------------------------------------------------------------------------
# Safe update
# ---------------------------------------------------------------------------

def _update_file(local_path, content):
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding="utf-8")


def _is_same_content(local_path, content):
    if not local_path.exists():
        return False
    try:
        return local_path.read_text(encoding="utf-8") == content
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Built-in migration engine (self-contained, no dependency on pctl lib)
#
# Because we overwrite framework files, we cannot rely on pctl.py's migrate
# command — it may have been replaced already. Each migration is a simple
# (version_from, version_to, description, runnable) tuple.
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
            _log(f"Migration {from_v}->{to_v}: {desc}...")
            try:
                fn(CONTROL_ROOT)
                _write_schema(to_v)
                ran.append((from_v, to_v, desc))
            except Exception as e:
                _log(f"Migration {from_v}->{to_v} FAILED: {e}")
                raise
    return ran


def _append_changelog(new_version, migrations_ran, log_lines, deprecations=None):
    header = f"## v{new_version} ({datetime.date.today().isoformat()})"
    parts = [header, ""]
    if migrations_ran:
        parts.append("### Migrations")
        for from_v, to_v, desc in migrations_ran:
            parts.append(f"- `{from_v}→{to_v}`: {desc}")
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
        # Insert after the first line (title) so newest stays on top
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


# ---- Define migrations ----

def _migrate_ensure_dirs(root):
    """Ensure all standard directories exist (backward compat with very old versions)."""
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
    """Create template files if missing (backward compat)."""
    templates = {
        "PROJECT.md.template": "# Project: <name>\n\n## Description\n\n## Type\n\n## Main stack\n\n## General status\n",
        "GOALS.md.template": "# Goals\n\n## Objective\n\n## Success criteria\n- [ ]\n\n## Out of scope\n",
        "CONTEXT.md.template": "# Context memory\n\n## What this project is\n\n## Tacit conventions\n\n## Things to watch out for\n\n## Perceived status\n\n## Last relevant session\n",
    }
    for name, content in templates.items():
        fpath = root / name
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")
            _log(f"  Created missing template: {name}")


def _migrate_gitignore(root):
    """Add .control/ to .gitignore entries if not present."""
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
    """Create roadmaps/ subdirs if they didn't exist before."""
    for d in ["roadmaps", "roadmaps/phases", "roadmaps/initiatives", "roadmaps/milestones"]:
        (root / d).mkdir(parents=True, exist_ok=True)


_migration(0, 1, "Ensure standard directories", _migrate_ensure_dirs)
_migration(1, 2, "Create missing templates", _migrate_create_templates)
_migration(2, 3, "Add .gitignore entries", _migrate_gitignore)
_migration(3, 4, "Create roadmaps directories", _migrate_roadmaps_dir)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _report(updated, skipped, errors, local_modified, dry_run,
            framework_count, user_count, branch, origin, log_lines):
    print()
    print("=" * 62)
    print("  PROJECTCONTROL UPDATE SUMMARY")
    print("=" * 62)
    print(f"  Branch:           {branch}")
    print(f"  Remote:           {origin or '(none)'}")
    print(f"  Framework files:  {framework_count}")
    print(f"  User data files:  {user_count} (preserved)")
    print()

    if dry_run:
        print("  ** DRY RUN — no files changed **")
        print()

    if updated:
        print(f"  Updated ({len(updated)}):")
        for f in sorted(updated):
            print(f"    + {f}")
    if skipped:
        print(f"  Already current ({len(skipped)}): up to date")
    if local_modified:
        print(f"  Skipped (locally modified) ({len(local_modified)}):")
        for f in sorted(local_modified):
            print(f"    ! {f}")
        print("    Review and merge manually if needed.")
    if errors:
        print(f"  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    x {e}")

    if log_lines:
        print()
        print("  Changes since last update:")
        for line in log_lines.strip().splitlines():
            print(f"    {line}")

    if not dry_run and not errors:
        print()
        print("  Update complete.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Update ProjectControlSystem framework from git remote."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying files.")
    parser.add_argument("--force", action="store_true",
                        help="Proceed even with uncommitted changes (no prompt).")
    parser.add_argument("--ref", default="origin/main",
                        help="Remote ref to update from (default: origin/main).")
    args = parser.parse_args()

    dry_run = args.dry_run
    force = args.force
    ref = args.ref

    branch = _current_branch()
    origin = _origin_url()

    print(f"ProjectControlSystem Update")
    print(f"  Source ref:      {ref}")
    print(f"  Current branch:  {branch}")
    print()

    if not origin:
        print("ERROR: No git remote 'origin' configured.")
        print("This script requires a remote named 'origin' pointing")
        print("to the ProjectControlSystem repository.")
        sys.exit(1)

    # Uncommitted changes check
    if _has_uncommitted() and not force and not dry_run:
        print("WARNING: You have uncommitted changes.")
        print("Commit or stash them first, or use --force.")
        yn = input("Continue? [y/N]: ").strip().lower()
        if yn != "y":
            print("Aborted.")
            sys.exit(0)

    # Fetch
    if not _fetch():
        print("ERROR: Fetch failed. Check your connection or ref name.")
        sys.exit(1)

    # Verify ref exists
    test = _cat(ref, Path(".control/SYSTEM.md"))
    if test is None:
        print(f"ERROR: Ref '{ref}' does not exist or has no .control/ directory.")
        print("Available remote refs:")
        out, _, _ = _git(["ls-remote", "--heads", "origin"])
        for line in out.splitlines():
            print(f"  {line}")
        sys.exit(1)

    # Build file lists
    remote_files = _ls_remote(ref)
    if not remote_files:
        print(f"ERROR: No .control/ files found in ref '{ref}'.")
        sys.exit(1)

    framework_files, user_files, unknown = _classify_files(remote_files)
    _log(f"Found {len(framework_files)} framework + {len(user_files)} user files in {ref}")

    # Backup
    if not dry_run:
        _backup()

    # Compute merge base for changelog
    base = _merge_base(ref)
    log_lines = _diff_log(base) if base else ""

    # --- Update framework files ---
    updated, skipped, errors, local_modified = [], [], [], []
    for rel in sorted(framework_files):
        local_path = CONTROL_ROOT / rel
        content = _cat(ref, rel)
        if content is None:
            errors.append(f"{rel}: could not read from {ref}")
            continue

        if _is_same_content(local_path, content):
            skipped.append(rel)
            continue

        # Check local modifications
        if local_path.exists():
            out, _, _ = _git(["diff", "--", str(rel)])
            if out.strip():
                local_modified.append(rel)
                continue

        if dry_run:
            updated.append(rel)
            continue

        try:
            _update_file(local_path, content)
            updated.append(rel)
        except OSError as e:
            errors.append(f"{rel}: {e}")

    # NOTE: We do NOT delete files that exist locally but not in the remote.
    # User data and local additions are NEVER removed by the update. Framework
    # files that are no longer part of the distribution are simply left in
    # place; they become inert. A future migration can clean them up if needed.

    # --- Run built-in migrations ---
    ran = []
    if not dry_run and not errors:
        old_schema = _current_schema()
        try:
            ran = _run_migrations(old_schema)
            for from_v, to_v, desc in ran:
                _log(f"Migration {from_v}->{to_v}: {desc} [OK]")
        except Exception:
            _log("Migrations failed. Check backup and repair manually.")
            # Don't exit — the update itself succeeded

    # --- Update local changelog ---
    if not dry_run and not errors:
        new_version = _current_schema()
        if updated or ran or log_lines:
            _append_changelog(
                new_version=new_version,
                migrations_ran=ran,
                log_lines=log_lines,
            )

    # --- Report ---
    _report(
        updated=updated,
        skipped=skipped,
        errors=errors,
        local_modified=local_modified,
        dry_run=dry_run,
        framework_count=len(framework_files),
        user_count=len(user_files),
        branch=branch,
        origin=origin,
        log_lines=log_lines,
    )


if __name__ == "__main__":
    main()

"""Framework update detection (read-only).

Answers "is there a newer ProjectControl version upstream?" without
touching any file except a small cache. Applying an update is the job
of `scripts/update.py`, which is self-contained on purpose.

Files involved:
  framework.json          manifest shipped by upstream (version, upstream url, file list)
  .framework_lock.json    what is installed here (version, commit, file hashes)
  .update_check.json      cache of the last remote check (gitignored)
  .update/pending.json    conflicts left by the last update (gitignored)

Network: one `git ls-remote` with a short timeout, at most once every
CHECK_INTERVAL_H hours. Disable with env PCTL_NO_UPDATE_CHECK=1.
"""
import datetime
import json
import os
import subprocess

from . import paths

MANIFEST = paths.CONTROL_ROOT / "framework.json"
LOCK = paths.CONTROL_ROOT / ".framework_lock.json"
CACHE = paths.CONTROL_ROOT / ".update_check.json"
PENDING = paths.CONTROL_ROOT / ".update" / "pending.json"
CHECK_INTERVAL_H = 24


def _read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def installed():
    """{"version", "commit"} of the installed framework (values may be None)."""
    lock = _read_json(LOCK) or {}
    man = _read_json(MANIFEST) or {}
    return {
        "version": lock.get("version") or man.get("version"),
        "commit": lock.get("commit"),
    }


def upstream():
    man = _read_json(MANIFEST) or {}
    up = man.get("upstream") or {}
    return up.get("url"), up.get("ref", "main")


def pending_conflicts():
    data = _read_json(PENDING) or {}
    return data.get("conflicts", [])


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _ls_remote(url, ref, timeout):
    try:
        r = subprocess.run(
            ["git", "ls-remote", url, f"refs/heads/{ref}"],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.split()[0]


def check(force=False, timeout=4):
    """Return {"status", "installed", "remote_commit", "checked_at", "message"}.

    status: up_to_date | available | unknown | disabled | offline
    """
    inst = installed()
    url, ref = upstream()
    base = {"installed": inst, "remote_commit": None, "checked_at": None}

    if not url:
        return {**base, "status": "unknown", "message": "framework.json has no upstream url"}
    if os.environ.get("PCTL_NO_UPDATE_CHECK") == "1" and not force:
        return {**base, "status": "disabled", "message": "PCTL_NO_UPDATE_CHECK=1"}

    cache = _read_json(CACHE)
    if cache and not force:
        try:
            age = _now() - datetime.datetime.fromisoformat(cache["checked_at"])
            if age.total_seconds() < CHECK_INTERVAL_H * 3600 and cache.get("installed") == inst:
                return cache
        except (KeyError, ValueError, TypeError):
            pass

    remote = _ls_remote(url, ref, timeout)
    if remote is None:
        return {**base, "status": "offline", "message": f"could not reach {url}"}

    if not inst["commit"]:
        status, msg = "unknown", "no install record; run `python .control/scripts/update.py --check`"
    elif remote == inst["commit"]:
        status, msg = "up_to_date", ""
    else:
        status, msg = "available", "run `python .control/scripts/update.py --check` to see what changed"

    result = {**base, "status": status, "remote_commit": remote,
              "checked_at": _now().isoformat(), "message": msg}
    try:
        CACHE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    except OSError:
        pass
    return result

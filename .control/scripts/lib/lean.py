"""Lean mode: how hard the agent pushes for the smallest correct change.

The level is project data (`.control/lean.json`, committed, never touched by
updates). `PCTL_LEAN` overrides it for one shell. Rules live in
`skills/lean.md`; this module only stores the level and renders the one
line `pctl brief` shows, so the always-loaded cost stays one line.
"""
import json
import os

from . import paths

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

from pathlib import Path

CONTROL_ROOT = Path(__file__).resolve().parents[2]  # .control/

TASKS_DIR = CONTROL_ROOT / "tasks"
ARCH_DIR = CONTROL_ROOT / "architecture"
SESSIONS_DIR = CONTROL_ROOT / "sessions"
DECISIONS_DIR = CONTROL_ROOT / "decisions"
SKILLS_DIR = CONTROL_ROOT / "skills"
DIAGRAMS_DIR = CONTROL_ROOT / "diagrams"
FLOWS_DIR = CONTROL_ROOT / "flows"

BACKLOG_MD = TASKS_DIR / "BACKLOG.md"
IN_PROGRESS_MD = TASKS_DIR / "IN_PROGRESS.md"
DONE_MD = TASKS_DIR / "DONE.md"
ARCH_INDEX_MD = ARCH_DIR / "_index.md"
SKILLS_INDEX_MD = SKILLS_DIR / "_index.md"

TASK_STATES = ["backlog", "in_progress", "blocked", "done"]
TASK_PRIORITIES = ["baja", "media", "alta", "critica"]
TASK_TYPES = ["feature", "bug", "refactor", "investigacion", "chore"]

VALID_TRANSITIONS = {
    "backlog": {"in_progress"},
    "in_progress": {"blocked", "done", "backlog"},
    "blocked": {"in_progress"},
    "done": {"in_progress"},
}


def ensure_dirs():
    for d in [TASKS_DIR, ARCH_DIR, SESSIONS_DIR, DECISIONS_DIR,
              SKILLS_DIR, DIAGRAMS_DIR, FLOWS_DIR, DIAGRAMS_DIR / "flows",
              SKILLS_DIR / "proposed",
              CONTROL_ROOT / "scripts" / "lib" / "proposed"]:
        d.mkdir(parents=True, exist_ok=True)

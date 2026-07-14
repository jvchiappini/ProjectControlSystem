import json
import os
from pathlib import Path

CONTROL_ROOT = Path(__file__).resolve().parents[2]

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

TASKS_INDEX_JSON = CONTROL_ROOT / ".tasks_index.json"
EVENT_LOG = CONTROL_ROOT / ".events.ndjson"
POSITIONS_JSON = CONTROL_ROOT / ".positions.json"
LOCK_FILE = CONTROL_ROOT / ".control.lock"
BACKUPS_DIR = CONTROL_ROOT / ".backups"
FLOWS_INDEX_MD = FLOWS_DIR / "_index.md"

TASK_STATES = ["backlog", "in_progress", "blocked", "done"]
TASK_PRIORITIES = ["baja", "media", "alta", "critica"]
TASK_TYPES = ["feature", "bug", "refactor", "investigacion", "chore"]

VALID_TRANSITIONS = {
    "backlog": {"in_progress"},
    "in_progress": {"blocked", "done", "backlog"},
    "blocked": {"in_progress"},
    "done": {"in_progress"},
}


ROADMAPS_DIR = CONTROL_ROOT / "roadmaps"
ROADMAPS_PHASES_DIR = ROADMAPS_DIR / "phases"
ROADMAPS_INITIATIVES_DIR = ROADMAPS_DIR / "initiatives"
ROADMAPS_MILESTONES_DIR = ROADMAPS_DIR / "milestones"

DOCS_DIR = CONTROL_ROOT / "docs"
DOCS_CATEGORIES = ["guides", "api", "database", "reference", "tutorials"]


def ensure_dirs():
    dirs = [TASKS_DIR, ARCH_DIR, SESSIONS_DIR, DECISIONS_DIR,
            SKILLS_DIR, DIAGRAMS_DIR, FLOWS_DIR, DIAGRAMS_DIR / "flows",
            SKILLS_DIR / "proposed",
            CONTROL_ROOT / "scripts" / "lib" / "proposed",
            BACKUPS_DIR,
            ROADMAPS_DIR, ROADMAPS_PHASES_DIR,
            ROADMAPS_INITIATIVES_DIR, ROADMAPS_MILESTONES_DIR,
            DOCS_DIR]
    dirs += [DOCS_DIR / c for c in DOCS_CATEGORIES]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


# ---- tareas index incremental ----

def _read_tasks_index():
    if not TASKS_INDEX_JSON.exists():
        return {}
    try:
        return json.loads(TASKS_INDEX_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_tasks_index(index):
    TASKS_INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    TASKS_INDEX_JSON.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def _ensure_task_index_key(data):
    """Devuelve una entrada de índice a partir del frontmatter de una tarea."""
    return {
        "id": data.get("id"),
        "titulo": data.get("titulo"),
        "estado": data.get("estado"),
        "prioridad": data.get("prioridad"),
        "tipo": data.get("tipo"),
        "creado": data.get("creado"),
        "actualizado": data.get("actualizado"),
        "dominio": data.get("dominio"),
        "depende_de": data.get("depende_de"),
        "bloqueado_por": data.get("bloqueado_por"),
    }


def update_task_index(tid, data):
    """Actualiza una entrada en el índice incremental."""
    idx = _read_tasks_index()
    idx[tid] = _ensure_task_index_key(data)
    _write_tasks_index(idx)


def remove_task_index(tid):
    """Elimina una tarea del índice incremental."""
    idx = _read_tasks_index()
    idx.pop(tid, None)
    _write_tasks_index(idx)


def get_all_tasks_from_index():
    """Devuelve lista de tareas desde el índice, ordenadas."""
    idx = _read_tasks_index()
    out = list(idx.values())
    out.sort(key=lambda d: (
        {"critica": 0, "alta": 1, "media": 2, "baja": 3}.get(d.get("prioridad"), 9),
        d.get("id", ""),
    ))
    return out

"""roadmaps -- phase/initiative/milestone hierarchy management."""

import datetime
import re

from . import atomic, event_log, fm, paths
from .lock import FileLock

PHASES_DIR = paths.CONTROL_ROOT / "roadmaps" / "phases"
INITIATIVES_DIR = paths.CONTROL_ROOT / "roadmaps" / "initiatives"
MILESTONES_DIR = paths.CONTROL_ROOT / "roadmaps" / "milestones"
INDEX_MD = paths.CONTROL_ROOT / "roadmaps" / "_index.md"

PHASE_STATES = ["not_started", "in_progress", "completed", "blocked", "cancelled"]
INITIATIVE_STATES = ["backlog", "in_progress", "completed", "blocked", "cancelled"]
MILESTONE_STATES = ["backlog", "in_progress", "completed", "blocked", "cancelled"]

PHASE_TEMPLATE = """\
---
id: {id}
nombre: "{nombre}"
orden: {orden}
estado: not_started
inicio: {fecha}
fin_estimado: ""
fin_real: null
depende_de: []
responsable: agente
prioridad: media
---

# Phase: {nombre}

## Summary

(Describe what this phase delivers end-to-end.)

## Goals

- Goal 1
- Goal 2

## Scope

### In scope
-

### Out of scope
-

## Dependencies

- (list phase dependencies)

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|

## Success criteria

- [ ]

## Initiatives

(List of initiatives belonging to this phase)
"""

INITIATIVE_TEMPLATE = """\
---
id: {id}
nombre: "{nombre}"
phase: {phase}
estado: backlog
prioridad: media
tamano_estimado: medium
depende_de: []
creado: {fecha}
responsable: agente
---

# Initiative: {nombre}

## Description

(2-5 paragraphs explaining what this initiative entails.)

## Scope

### Deliverables
-

### Non-goals
-

## Technical approach

(High-level approach, point to architecture docs.)

## Dependencies

-

## Milestones

| Milestone | Description | Target date | Status |
|---|---|---|---|

## Tasks

- T-XXXX

## Acceptance criteria

- [ ]

## Notes
"""

MILESTONE_TEMPLATE = """\
---
id: {id}
nombre: "{nombre}"
initiative: {initiative}
phase: {phase}
estado: backlog
target_date: ""
completed_date: null
depende_de: []
creado: {fecha}
---

# Milestone: {nombre}

## Description

(1-2 paragraphs describing the concrete checkpoint this milestone represents.)

## Verification criteria

- [ ]

## Related tasks

- T-XXXX

## Dependencies

-

## Notes
"""


def _today():
    return datetime.date.today().isoformat()


def _next_id(prefix, directory):
    highest = 0
    if directory.exists():
        for f in directory.iterdir():
            m = re.match(rf"^{prefix}-(\d+)\.md$", f.name)
            if m:
                n = int(m.group(1))
                if n > highest:
                    highest = n
    return f"{prefix}-{highest + 1:04d}"


def new_phase(nombre, orden=1):
    pid = _next_id("PHASE", PHASES_DIR)
    fpath = PHASES_DIR / f"{pid}.md"
    content = PHASE_TEMPLATE.format(id=pid, nombre=nombre, orden=orden, fecha=_today())
    atomic.write_with_backup(fpath, content)
    reindex()
    event_log.log("phase-created", pid, {"nombre": nombre})
    return pid, fpath


def new_initiative(nombre, phase):
    iid = _next_id("INITIATIVE", INITIATIVES_DIR)
    fpath = INITIATIVES_DIR / f"{iid}.md"
    content = INITIATIVE_TEMPLATE.format(id=iid, nombre=nombre, phase=phase, fecha=_today())
    atomic.write_with_backup(fpath, content)
    reindex()
    event_log.log("initiative-created", iid, {"nombre": nombre, "phase": phase})
    return iid, fpath


def new_milestone(nombre, initiative, phase):
    mid = _next_id("M", MILESTONES_DIR)
    fpath = MILESTONES_DIR / f"{mid}.md"
    content = MILESTONE_TEMPLATE.format(id=mid, nombre=nombre, initiative=initiative, phase=phase, fecha=_today())
    atomic.write_with_backup(fpath, content)
    reindex()
    event_log.log("milestone-created", mid, {"nombre": nombre, "initiative": initiative})
    return mid, fpath


def list_phases(estado=None):
    return _list_items(PHASES_DIR, estado)


def list_initiatives(estado=None, phase=None):
    items = _list_items(INITIATIVES_DIR, estado)
    if phase:
        items = [i for i in items if i.get("phase") == phase]
    return items


def list_milestones(estado=None, initiative=None):
    items = _list_items(MILESTONES_DIR, estado)
    if initiative:
        items = [i for i in items if i.get("initiative") == initiative]
    return items


def _list_items(directory, estado=None):
    items = []
    if not directory.exists():
        return items
    for f in sorted(directory.iterdir()):
        if f.suffix != ".md" or f.name == "_index.md":
            continue
        if "XXXX" in f.name:
            continue
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        if not data.get("id"):
            continue
        if "XXXX" in str(data.get("id", "")):
            continue
        if estado and data.get("estado") != estado:
            continue
        items.append(data)
    return items


def show_item(item_id):
    for d in [PHASES_DIR, INITIATIVES_DIR, MILESTONES_DIR]:
        fpath = d / f"{item_id}.md"
        if fpath.exists():
            return fpath.read_text(encoding="utf-8")
    return None


def touch_estado(item_id, nuevo_estado):
    """Cambiar el estado de cualquier item del roadmap."""
    for d, estados in [(PHASES_DIR, PHASE_STATES), (INITIATIVES_DIR, INITIATIVE_STATES), (MILESTONES_DIR, MILESTONE_STATES)]:
        fpath = d / f"{item_id}.md"
        if fpath.exists():
            if nuevo_estado not in estados:
                raise ValueError(f"Estado '{nuevo_estado}' no valido para items en {d.name}. Validos: {estados}")
            with FileLock():
                data, body = fm.parse(fpath.read_text(encoding="utf-8"))
                data["estado"] = nuevo_estado
                atomic.write_with_backup(fpath, fm.dump(data, body, _key_order(data)))
                reindex()
                event_log.log("roadmap-state-changed", item_id, {"estado": nuevo_estado})
                return data
    raise ValueError(f"Item {item_id} no encontrado")


def _key_order(data):
    """Preserve key order in frontmatter."""
    preferred = ["id", "nombre", "orden", "phase", "initiative", "estado", "prioridad",
                  "inicio", "fin_estimado", "fin_real", "target_date", "completed_date",
                  "tamano_estimado", "depende_de", "creado", "responsable"]
    keys = [k for k in preferred if k in data]
    keys += [k for k in data if k not in preferred]
    return keys


def reindex():
    """Regenerate roadmaps/_index.md from all items."""
    phases = list_phases()
    initiatives = list_initiatives()
    milestones = list_milestones()

    lines = ["# Roadmap index", "",
             "(Generated by `pctl reindex` — do not edit manually)", "",
             "---", ""]

    # Phase table
    lines.append("## Phase overview")
    lines.append("")
    lines.append("| Phase | Status | Timeline | Initiatives | File |")
    lines.append("|---|---|---|---|---|")
    for p in sorted(phases, key=lambda x: x.get("orden", 999)):
        pid = p.get("id", "?")
        inicount = len([i for i in initiatives if i.get("phase") == pid])
        timeline = f"{p.get('inicio', '?')} - {p.get('fin_estimado', '?')}"
        lines.append(f"| {pid} | {p.get('estado', '?')} | {timeline} | {inicount} | phases/{pid}.md |")
    lines.append("")

    # Initiative table
    lines.append("## Initiative overview")
    lines.append("")
    lines.append("| Initiative | Phase | Status | Priority | Milestones | File |")
    lines.append("|---|---|---|---|---|---|")
    for i in sorted(initiatives, key=lambda x: x.get("id", "")):
        iid = i.get("id", "?")
        mcount = len([m for m in milestones if m.get("initiative") == iid])
        lines.append(f"| {iid} | {i.get('phase', '?')} | {i.get('estado', '?')} | {i.get('prioridad', '?')} | {mcount} | initiatives/{iid}.md |")
    lines.append("")

    # Milestone table
    lines.append("## Milestone overview")
    lines.append("")
    lines.append("| Milestone | Initiative | Target date | Status | File |")
    lines.append("|---|---|---|---|---|")
    for m in sorted(milestones, key=lambda x: x.get("id", "")):
        lines.append(f"| {m.get('id', '?')} | {m.get('initiative', '?')} | {m.get('target_date', '?')} | {m.get('estado', '?')} | milestones/{m.get('id', '?')}.md |")
    lines.append("")

    atomic.write(INDEX_MD, "\n".join(lines) + "\n")

    return {"phases": len(phases), "initiatives": len(initiatives), "milestones": len(milestones)}

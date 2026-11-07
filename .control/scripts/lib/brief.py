"""`pctl brief` - the single session-start digest.

Replaces reading ~10 files at session start. Everything an agent needs
to resume work, in one bounded output (default ~2k tokens):

  1. alerts (unclosed session, update conflicts, outdated flows/docs, update available)
  2. local rules (SYSTEM.local.md) - user overrides that survive updates
  3. handoff from the last closed session (next steps, open questions)
  4. tasks in progress / blocked (with acceptance progress) + top of backlog
  5. CONTEXT.md working memory (template guidance stripped) + inbox notes
  6. active roadmap phase, git state
  7. where to look next (commands, not file dumps)
The lean-mode level is one line under the header (omitted when off).

Sections are emitted in priority order; when the budget runs out, lower
priority sections are cut and a pointer to the full source is left.
"""
import datetime
import subprocess

from . import context, fm, lean, paths, sessions, tasks, updates

DEFAULT_BUDGET = 8000  # characters (~2k tokens)
LOCAL_RULES = paths.CONTROL_ROOT / "SYSTEM.local.md"
PRIORITY_ORDER = {"critica": 0, "alta": 1, "media": 2, "baja": 3}


def _git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True,
                           cwd=paths.CONTROL_ROOT.parent, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _project_name():
    p = paths.CONTROL_ROOT / "PROJECT.md"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].replace("Project:", "").strip()
    return None


def _strip_template_guidance(body):
    """Drop the template intro and '(...)' placeholder paragraphs."""
    out, para = [], []

    def flush():
        text = "\n".join(para).strip()
        if text and not (text.startswith("(") and text.endswith(")")):
            out.append("\n".join(para))
        para.clear()

    for line in body.splitlines():
        if line.startswith("#"):
            flush()
            out.append(line)
        elif not line.strip():
            flush()
        else:
            para.append(line)
    flush()
    # drop the H1 + intro paragraph of the template (up to the first ##)
    text = "\n".join(out)
    if "\n## " in text and text.lstrip().startswith("# "):
        text = "## " + text.split("\n## ", 1)[1]
    # drop headings left without content
    lines = text.splitlines()
    kept = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            nxt = next((l for l in lines[i + 1:] if l.strip()), "")
            if not nxt or nxt.startswith("## "):
                continue
        kept.append(line)
    return "\n".join(kept).strip()


def _newest_session_id():
    files = sorted(paths.SESSIONS_DIR.glob("S-*.md"))
    return files[-1].stem if files else None


def _criteria_progress(tid):
    try:
        crit = tasks.get_full(tid)["criterios"]
    except (FileNotFoundError, ValueError, KeyError):
        return ""
    crit = [c for c in crit if c.get("texto")]
    if not crit:
        return ""
    done = sum(1 for c in crit if c["checked"])
    return f" ({done}/{len(crit)} criteria)"


# ---- sections (each returns list of lines, or []) ----

def _sec_alerts(check_updates):
    lines = []
    open_s = sessions.open_sessions()
    # the newest open session started today is most likely the current one
    today = f"S-{datetime.date.today().isoformat()}"
    if open_s and open_s[0].startswith(today) and open_s[0] == _newest_session_id():
        current = open_s.pop(0)
        lines.append(f"- Current session: {current} (close it with `pctl session-close` + `--next`).")
    if open_s:
        lines.append(f"- Unclosed older session(s): {', '.join(open_s[:3])} - a previous agent "
                     f"did not finish. Review (`pctl session-summarize {open_s[0]}`) and close it.")
    conflicts = updates.pending_conflicts()
    if conflicts:
        lines.append(f"- Framework update left {len(conflicts)} file(s) for review "
                     f"(your local edits were kept): {', '.join(conflicts[:4])}"
                     f"{' ...' if len(conflicts) > 4 else ''}. See `.control/.update/`.")
    try:
        from . import flows
        stale = flows.list_flows(estado="desactualizado")
        if stale:
            lines.append(f"- Outdated flows: {', '.join(f['id'] for f in stale[:5])} - fix before relying on them.")
    except Exception:
        pass
    try:
        from . import docs
        stale_docs = docs.list_docs(estado="outdated")
        if stale_docs:
            lines.append(f"- Outdated docs: {', '.join(d['id'] for d in stale_docs[:5])}.")
    except Exception:
        pass
    if check_updates:
        u = updates.check()
        if u.get("status") == "available":
            v = u["installed"].get("version") or "?"
            lines.append(f"- ProjectControl update available (installed v{v}). Tell the user; "
                         f"preview with `python .control/scripts/update.py --check`.")
    inbox = context.inbox_items()
    if len(inbox) >= 10:
        lines.append(f"- CONTEXT.md inbox has {len(inbox)} unconsolidated notes - consolidate at session close.")
    return (["## Alerts"] + lines) if lines else []


def _sec_local_rules():
    if not LOCAL_RULES.exists():
        return []
    _, body = fm.parse(LOCAL_RULES.read_text(encoding="utf-8"))
    body = body.strip()
    return ["## Local rules (SYSTEM.local.md - override SYSTEM.md)", body] if body else []


def _sec_handoff():
    last = sessions.last_closed()
    if not last:
        return []
    d = last["data"]
    lines = [f"## Last session - {d.get('id', '?')} ({d.get('fecha', '')})",
             f"Summary: {d.get('resumen', '')}"]
    if d.get("tareas_tocadas"):
        lines.append(f"Tasks touched: {', '.join(d['tareas_tocadas'])}")
    if last["next"]:
        lines.append("Next steps:")
        lines += [f"- {x}" for x in last["next"]]
    if last["questions"]:
        lines.append("Open questions:")
        lines += [f"- {x}" for x in last["questions"]]
    return lines


def _sec_tasks():
    active = tasks.list_tasks(estado="in_progress")
    blocked = tasks.list_tasks(estado="blocked")
    backlog = sorted(tasks.list_tasks(estado="backlog"),
                     key=lambda t: (PRIORITY_ORDER.get(t.get("prioridad"), 9), t.get("id", "")))
    if not (active or blocked or backlog):
        return ["## Tasks", "(none yet)"]
    lines = ["## Tasks"]
    for t in active:
        lines.append(f"- [in_progress] {t['id']} [{t.get('prioridad', '')}] {t.get('titulo', '')}"
                     f"{_criteria_progress(t['id'])}")
    for t in blocked:
        lines.append(f"- [blocked] {t['id']} {t.get('titulo', '')} - reason: {t.get('bloqueado_por') or '?'}")
    if backlog:
        top = backlog[:3]
        lines.append(f"- backlog: {len(backlog)} task(s); top: "
                     + "; ".join(f"{t['id']} [{t.get('prioridad', '')}] {t.get('titulo', '')}" for t in top))
    return lines


def _sec_context():
    data, body = context.read()
    if not body.strip():
        return ["## Working memory (CONTEXT.md)", "(empty - create it when something worth remembering is learned)"]
    text = _strip_template_guidance(body)
    upd = data.get("actualizado", "?") if data else "?"
    text = "\n".join(("#" + l) if l.startswith("## ") else l for l in text.splitlines())
    return [f"## Working memory (CONTEXT.md, updated {upd})", text or "(only template placeholders)"]


def _sec_roadmap():
    try:
        from . import roadmaps
        active = [p for p in roadmaps.list_phases() if p.get("estado") == "in_progress"]
    except Exception:
        return []
    if not active:
        return []
    return ["## Roadmap", "Active phase(s): " + ", ".join(f"{p['id']} {p.get('nombre', '')}" for p in active)]


def _sec_git():
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if not branch:
        return []
    dirty = _git("status", "--porcelain") or ""
    n = len([l for l in dirty.splitlines() if l.strip()])
    recent = _git("log", "--oneline", "-3") or ""
    lines = ["## Git", f"Branch {branch}, {n} uncommitted file(s)."]
    lines += [f"- {l}" for l in recent.splitlines()]
    return lines


def _sec_next():
    return [
        "## How to load more (only when the task needs it)",
        "- One task: `pctl task-show <id>` | find anything: `pctl search <regex>`",
        "- Domain/flow maps: `pctl arch-list`, `pctl flow-list` | docs: `pctl doc-list`",
        "- Save a learning NOW (survives compaction): `pctl context-note \"...\" --tipo gotcha`",
    ]


def build(budget=DEFAULT_BUDGET, check_updates=True):
    header = f"# ProjectControl brief - {_project_name() or 'project'} - {datetime.date.today().isoformat()}"
    lean_line = lean.brief_line()
    if lean_line:
        header += "\n" + lean_line
    if not (paths.CONTROL_ROOT / "PROJECT.md").exists():
        return "\n".join([
            header, "",
            "No .control/PROJECT.md yet: ProjectControl is installed but the project is not set up.",
            "If the user wants to set it up (or asks what this project is), follow",
            "`.control/prompts/prompt_new_project.md` (skill `onboarding`). Otherwise just help with the request.",
        ])

    builders = [
        ("alerts", lambda: _sec_alerts(check_updates)),
        ("local rules", _sec_local_rules),
        ("handoff", _sec_handoff),
        ("tasks", _sec_tasks),
        ("context", _sec_context),
        ("roadmap", _sec_roadmap),
        ("git", _sec_git),
        ("next", _sec_next),
    ]
    out = [header]
    used = len(header)
    cut = []
    for name, fn in builders:
        try:
            lines = fn()
        except Exception as e:  # a broken section must never break session start
            lines = [f"## {name}", f"(could not build: {e})"]
        if not lines:
            continue
        block = "\n".join(lines)
        if used + len(block) > budget:
            room = budget - used - 120
            if name == "context" and room > 400:
                block = block[:room].rsplit("\n", 1)[0] + "\n... (truncated - `pctl context-show` for the rest)"
            else:
                cut.append(name)
                continue
        out += ["", block]
        used += len(block) + 1
    if cut:
        out += ["", f"(omitted for budget: {', '.join(cut)} - rerun with `--budget N`)"]
    return "\n".join(out)

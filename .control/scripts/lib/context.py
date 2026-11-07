
from . import atomic, fm, paths, util

CONTEXT_MD = paths.CONTROL_ROOT / "CONTEXT.md"
CONTEXT_KEY_ORDER = ["actualizado", "actualizado_por", "version_schema"]

def read():
    if not CONTEXT_MD.exists():
        return {}, ""
    return fm.parse(CONTEXT_MD.read_text(encoding="utf-8"))


def write(body, actualizado_por="agente"):
    data = {
        "actualizado": util.today(),
        "actualizado_por": actualizado_por,
        "version_schema": 1,
    }
    atomic.write_with_backup(CONTEXT_MD, fm.dump(data, body, CONTEXT_KEY_ORDER))


def check_budget():
    if not CONTEXT_MD.exists():
        return None
    _, body = fm.parse(CONTEXT_MD.read_text(encoding="utf-8"))
    n = len([l for l in body.splitlines() if l.strip()])
    if n > 500:
        return (
            f"CONTEXT.md tiene {n} lineas no vacias. Si el contenido es "
            f"estable, considera promoverlo a PROJECT.md, architecture/, "
            f"roadmaps/ o decisions/ y podar el resto."
        )
    return None


# ---- Inbox: incremental notes that survive crashes/compactions ----
#
# Agents often lose their conversation (compaction, crash, new chat)
# before reaching session close. `pctl context-note` saves a learning
# the moment it happens; session close consolidates the inbox into the
# proper sections and empties it.

INBOX_HEADING = "## Inbox (unconsolidated notes)"
NOTE_KINDS = ["fact", "gotcha", "convention", "todo", "decision"]


def add_note(text, kind="fact"):
    from .lock import FileLock
    text = " ".join((text or "").split())
    if not text:
        raise ValueError("la nota esta vacia")
    if kind not in NOTE_KINDS:
        raise ValueError(f"tipo invalido: {kind} (usar {', '.join(NOTE_KINDS)})")
    with FileLock():
        data, body = read()
        if not data and not body:
            tpl = paths.CONTROL_ROOT / "CONTEXT.md.template"
            _, body = fm.parse(tpl.read_text(encoding="utf-8")) if tpl.exists() else ({}, "# Context memory\n")
        line = f"- [{util.today()}] ({kind}) {text}"
        if INBOX_HEADING in body:
            head, tail = body.split(INBOX_HEADING, 1)
            rest = tail.split("\n## ", 1)
            section = rest[0].rstrip("\n")
            last = section.splitlines()[-1] if section.strip() else ""
            # keep notes as their own list, separate from any placeholder paragraph
            section += ("\n" if last.startswith("- ") else "\n\n") + line + "\n"
            after = ("\n## " + rest[1]) if len(rest) > 1 else ""
            body = head + INBOX_HEADING + section + after
        else:
            body = body.rstrip("\n") + "\n\n" + INBOX_HEADING + "\n\n" + line + "\n"
        write(body, actualizado_por=data.get("actualizado_por", "agente") if data else "agente")
    return line


def inbox_items():
    _, body = read()
    if INBOX_HEADING not in body:
        return []
    section = body.split(INBOX_HEADING, 1)[1].split("\n## ", 1)[0]
    return [l.strip()[2:] for l in section.splitlines() if l.strip().startswith("- ")]

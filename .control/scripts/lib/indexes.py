from . import paths, tasks

_ESTADO_TITULO = {
    "backlog": "# Backlog\n\n(generado por `pctl reindex` — no editar a mano)\n\n",
    "in_progress": "# En curso\n\n(generado por `pctl reindex` — no editar a mano)\n\n",
    "done": "# Completadas\n\n(generado por `pctl reindex` — no editar a mano)\n\n",
}

_TARGET_FILE = {
    "backlog": paths.BACKLOG_MD,
    "in_progress": paths.IN_PROGRESS_MD,
    "blocked": paths.IN_PROGRESS_MD,  # blocked se muestra junto a in_progress
    "done": paths.DONE_MD,
}


def _row(d):
    rel = d.get("id", "")
    marca = " (bloqueada)" if d.get("estado") == "blocked" else ""
    return (
        f"- **{rel}**{marca} — {d.get('titulo','')} "
        f"`[{d.get('prioridad','')}]` (actualizado {d.get('actualizado','')})"
    )


def reindex():
    paths.ensure_dirs()
    grouped = {"backlog": [], "in_progress": [], "done": []}
    for d in tasks.list_tasks():
        estado = d.get("estado")
        bucket = "in_progress" if estado == "blocked" else estado
        if bucket not in grouped:
            continue
        grouped[bucket].append(d)

    for estado, items in grouped.items():
        content = _ESTADO_TITULO[estado]
        if not items:
            content += "_sin tareas_\n"
        else:
            content += "\n".join(_row(d) for d in items) + "\n"
        _TARGET_FILE[estado].write_text(content, encoding="utf-8")

    return {k: len(v) for k, v in grouped.items()}

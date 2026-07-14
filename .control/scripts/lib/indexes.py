from . import atomic, paths, fm

_ESTADO_TITULO = {
    "backlog": "# Backlog\n\n(generado por `pctl reindex` — no editar a mano)\n\n",
    "in_progress": "# En curso\n\n(generado por `pctl reindex` — no editar a mano)\n\n",
    "done": "# Completadas\n\n(generado por `pctl reindex` — no editar a mano)\n\n",
}

_TARGET_FILE = {
    "backlog": paths.BACKLOG_MD,
    "in_progress": paths.IN_PROGRESS_MD,
    "blocked": paths.IN_PROGRESS_MD,
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
    """Regenera BACKLOG.md, IN_PROGRESS.md, DONE.md y _index.md de
    arquitectura desde los archivos fuente. Escritura atómica."""
    paths.ensure_dirs()
    grouped = {"backlog": [], "in_progress": [], "done": []}
    for d in paths.get_all_tasks_from_index():
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
        atomic.write(_TARGET_FILE[estado], content)

    return {k: len(v) for k, v in grouped.items()}


def add_task_to_index(data):
    """Inserta una tarea en el índice incremental y regenera índices."""
    paths.update_task_index(data.get("id"), data)
    reindex()


def update_task_in_index(tid, data):
    """Actualiza una tarea en el índice incremental."""
    paths.update_task_index(tid, data)
    reindex()


def remove_task_from_index(tid):
    """Elimina una tarea del índice y regenera."""
    paths.remove_task_index(tid)
    reindex()


def rebuild_index_from_files():
    """Reconstruye el índice JSON desde los archivos T-*.md en disco.
    Útil si el índice se corrompe o se usa --force-reindex."""
    idx = {}
    for f in sorted(paths.TASKS_DIR.rglob("T-*.md")):
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        tid = data.get("id")
        if tid:
            idx[tid] = paths._ensure_task_index_key(data)
    paths._write_tasks_index(idx)
    reindex()

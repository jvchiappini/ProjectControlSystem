"""pctl doctor — chequeo de integridad del proyecto."""

from . import fm, paths, search


def run_doctor():
    errores = []
    advertencias = []

    # 1. Indices vs archivos reales (tareas)
    _check_task_integrity(errores)

    # 2. Flujos: indice vs archivos reales
    _check_flow_integrity(errores)

    # 3. Referencias a archivo:linea rotas
    _check_refs(errores)

    # 4. IDs duplicados
    _check_duplicate_ids(errores)

    # 5. Estado del CONTEXT.md
    _check_context_budget(advertencias)

    # 6. Flujos desactualizados
    _check_stale_flows(advertencias)

    # 7. indices generados vs archivos
    _check_generated_indexes(errores, advertencias)

    return errores, advertencias


def _check_task_integrity(errores):
    """Verifica que todas las tareas en el TASKS_INDEX_JSON tengan
    su archivo T-*.md correspondiente y viceversa."""
    indexados = paths._read_tasks_index()
    archivos = {f.stem: f for f in paths.TASKS_DIR.rglob("T-*.md")}

    for tid in indexados:
        if tid not in archivos:
            errores.append(f"Indice tiene tarea '{tid}' pero no existe su archivo")

    for tid, fpath in archivos.items():
        if tid not in indexados:
            data, _ = fm.parse(fpath.read_text(encoding="utf-8"))
            paths.update_task_index(tid, data)


def _check_flow_integrity(errores):
    """Verifica que todos los flujos en el FS tengan índice."""
    from .flows import _all_flow_files
    archivos = {f.stem for f in _all_flow_files()}
    if paths.FLOWS_INDEX_MD.exists():
        for line in paths.FLOWS_INDEX_MD.read_text(encoding="utf-8").splitlines():
            if line.startswith("| F-"):
                fid = line.split("|")[1].strip()
                if fid not in archivos:
                    errores.append(f"Indice de flujos tiene '{fid}' pero no existe su archivo")


def _check_refs(errores):
    """Valida referencias `archivo:linea`."""
    from .validate import _validate_refs
    errores.extend(_validate_refs())


def _check_duplicate_ids(errores):
    seen = {}
    for f in sorted(paths.TASKS_DIR.rglob("T-*.md")):
        data, _ = fm.parse(f.read_text(encoding="utf-8"))
        tid = data.get("id")
        if tid in seen:
            errores.append(f"ID duplicado '{tid}' en {f} y {seen[tid]}")
        else:
            seen[tid] = f


def _check_context_budget(advertencias):
    from .context import check_budget
    aviso = check_budget()
    if aviso:
        advertencias.append(aviso)


def _check_stale_flows(advertencias):
    from .flows import list_flows
    desactualizados = list_flows(estado="desactualizado")
    for d in desactualizados:
        advertencias.append(f"Flujo desactualizado: {d.get('id')} — {d.get('nombre')}")


def _check_generated_indexes(errores, advertencias):
    """Verifica que los índices generados existan."""
    for p in [paths.BACKLOG_MD, paths.IN_PROGRESS_MD, paths.DONE_MD,
              paths.ARCH_INDEX_MD, paths.FLOWS_INDEX_MD]:
        if p and not p.exists():
            advertencias.append(f"Índice generado no existe: {p}. Ejecutá 'pctl reindex'")

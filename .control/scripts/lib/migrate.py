"""Migraciones de schema para los archivos markdown de .control/.

Cada version de schema se identifica con `version_schema` en el
frontmatter. Las migraciones transforman datos de una version a la
siguiente. Esto permite evolucionar el formato sin romper archivos
existentes.
"""
from . import fm, paths, skills_registry


CURRENT_SCHEMA_VERSION = 1


def _migrate_task(data, body, target_version=CURRENT_SCHEMA_VERSION):
    """Migra una tarea a la version objetivo (in place)."""
    v = data.get("version_schema", 0)
    while v < target_version:
        if v == 0:
            data["version_schema"] = 1
            data.setdefault("depende_de", [])
            data.setdefault("bloqueado_por", None)
        v = data.get("version_schema", target_version)
    return data, body


def _migrate_flow(data, body, target_version=CURRENT_SCHEMA_VERSION):
    v = data.get("version_schema", 0)
    while v < target_version:
        if v == 0:
            data["version_schema"] = 1
            data.setdefault("padre", None)
        v = data.get("version_schema", target_version)
    return data, body


def _migrate_decision(data, body, target_version=CURRENT_SCHEMA_VERSION):
    v = data.get("version_schema", 0)
    while v < target_version:
        if v == 0:
            data["version_schema"] = 1
        v = data.get("version_schema", target_version)
    return data, body


def migrate_all():
    """Recorre todos los archivos de tareas, flujos y decisiones,
    actualiza al schema actual y reescribe si cambiaron."""
    stats = {"tasks": 0, "flows": 0, "decisions": 0, "errors": []}

    key_order_t = ["id", "titulo", "estado", "prioridad", "tipo", "creado_por",
                   "asignado_a", "creado", "actualizado", "depende_de",
                   "bloqueado_por", "version_schema"]
    key_order_f = ["id", "nombre", "estado", "dominios", "disparador", "padre",
                   "creado", "actualizado", "version_schema"]
    key_order_d = ["id", "titulo", "fecha", "estado", "reemplaza", "version_schema"]

    for f in sorted(paths.TASKS_DIR.rglob("T-*.md")):
        try:
            data, body = fm.parse(f.read_text(encoding="utf-8"))
            if data.get("version_schema", 0) < CURRENT_SCHEMA_VERSION:
                data, body = _migrate_task(data, body)
                f.write_text(fm.dump(data, body, key_order_t), encoding="utf-8")
                stats["tasks"] += 1
        except Exception as e:
            stats["errors"].append(f"{f}: {e}")

    for f in sorted(paths.FLOWS_DIR.rglob("F-*.md")):
        try:
            data, body = fm.parse(f.read_text(encoding="utf-8"))
            if data.get("version_schema", 0) < CURRENT_SCHEMA_VERSION:
                data, body = _migrate_flow(data, body)
                f.write_text(fm.dump(data, body, key_order_f), encoding="utf-8")
                stats["flows"] += 1
        except Exception as e:
            stats["errors"].append(f"{f}: {e}")

    for f in sorted(paths.DECISIONS_DIR.rglob("D-*.md")):
        try:
            data, body = fm.parse(f.read_text(encoding="utf-8"))
            if data.get("version_schema", 0) < CURRENT_SCHEMA_VERSION:
                data, body = _migrate_decision(data, body)
                f.write_text(fm.dump(data, body, key_order_d), encoding="utf-8")
                stats["decisions"] += 1
        except Exception as e:
            stats["errors"].append(f"{f}: {e}")

    # Promover todas las skills pendientes a activas
    for s in skills_registry.list_skills(estado="propuesta"):
        try:
            skills_registry.promote(s["id"])
            stats.setdefault("skills_promoted", 0)
            stats["skills_promoted"] += 1
        except (ValueError, FileNotFoundError) as e:
            stats["errors"].append(f"{s['id']}: {e}")

    return stats

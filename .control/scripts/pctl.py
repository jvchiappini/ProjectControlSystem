#!/usr/bin/env python3
"""pctl -- project control CLI.

Unico punto de entrada para operar sobre .control/. Ver SYSTEM.md
seccion 1: todo agente con ejecucion de codigo disponible debe usar
esto en vez de editar tasks/BACKLOG.md, IN_PROGRESS.md, DONE.md o
architecture/_index.md a mano.

Uso: python pctl.py <comando> [opciones]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import arch, context, decisions, flows, indexes, paths, sessions, skills_registry, tasks, validate  # noqa: E402


def cmd_task_new(args):
    tid, fpath = tasks.new_task(
        titulo=args.titulo, prioridad=args.prioridad, tipo=args.tipo,
        creado_por=args.creado_por, asignado_a=args.asignado_a,
        prefix=args.prefix, dominio=args.dominio,
    )
    indexes.reindex()
    print(f"creada {tid} -> {fpath}")


def cmd_task_move(args):
    antes, despues = tasks.move_task(
        args.id, args.estado, motivo=args.motivo, force=bool(args.force)
    )
    indexes.reindex()
    print(f"{args.id}: {antes} -> {despues}")


def cmd_task_show(args):
    print(tasks.show_task(args.id))


def cmd_task_list(args):
    for d in tasks.list_tasks(estado=args.estado):
        print(f"{d['id']:14} [{d['prioridad']:8}] {d['estado']:12} {d['titulo']}")


def cmd_status(args):
    counts = indexes.reindex()
    flows.reindex()
    print("estado del proyecto:")
    for k in ["backlog", "in_progress", "done"]:
        print(f"  {k:12}: {counts.get(k, 0)}")
    en_curso = tasks.list_tasks(estado="in_progress")
    if en_curso:
        print("\nen curso (por prioridad):")
        for d in en_curso[:5]:
            print(f"  {d['id']} [{d['prioridad']}] {d['titulo']}")
    bloqueadas = tasks.list_tasks(estado="blocked")
    if bloqueadas:
        print("\nbloqueadas:")
        for d in bloqueadas:
            print(f"  {d['id']} {d['titulo']}")
    desactualizados = flows.list_flows(estado="desactualizado")
    if desactualizados:
        print("\nflujos desactualizados (revisar):")
        for d in desactualizados:
            print(f"  {d['id']} {d['nombre']}")


def cmd_reindex(args):
    counts = indexes.reindex()
    flows.reindex()
    print(f"indices regenerados: {counts}")


def cmd_validate(args):
    errores = validate.validate_all()
    if not errores:
        print("sin errores")
        return
    for e in errores:
        print(f"ERROR: {e}")
    sys.exit(1)


def cmd_doc_check_refs(args):
    errores = validate._validate_refs()
    if not errores:
        print("referencias ok")
        return
    for e in errores:
        print(f"REF ROTA: {e}")
    sys.exit(1)


def cmd_session_start(args):
    sid, fpath = sessions.start_session(agente=args.agente)
    print(f"sesion iniciada {sid} -> {fpath}")


def cmd_session_log(args):
    sessions.log_event(args.id, args.texto)
    print("evento registrado")


def cmd_session_close(args):
    tocadas = args.tareas.split(",") if args.tareas else []
    fpath = sessions.close_session(args.id, args.resumen, tareas_tocadas=tocadas)
    print(f"sesion cerrada -> {fpath}")


def cmd_arch_touch(args):
    r = arch.touch(args.dominio, estado=args.estado, crear_archivo=args.crear_archivo)
    print(f"{args.dominio}: {r}")


def cmd_arch_list(args):
    for dominio, r in arch.list_domains().items():
        print(f"{dominio:20} {r['estado']:16} {r['actualizado']}  {r['archivo']}")


def cmd_flow_new(args):
    dominios = [d.strip() for d in args.dominios.split(",")] if args.dominios else []
    fid, fpath = flows.new_flow(
        args.nombre, dominios=dominios, disparador=args.disparador or "", padre=args.padre
    )
    print(f"creado {fid} -> {fpath}")


def cmd_flow_show(args):
    print(flows.show_flow(args.id))


def cmd_flow_list(args):
    for d in flows.list_flows(dominio=args.dominio, estado=args.estado):
        dominios = ", ".join(d.get("dominios") or [])
        print(f"{d['id']:8} [{d['estado']:14}] {d['nombre']}  ({dominios})")


def cmd_flow_touch(args):
    d = flows.touch_estado(args.id, args.estado)
    print(f"{args.id}: estado -> {d['estado']}")


def cmd_context_show(args):
    data, body = context.read()
    if not data:
        print("no existe CONTEXT.md todavia (copiar CONTEXT.md.template)")
        return
    print(f"(actualizado {data.get('actualizado')} por {data.get('actualizado_por')})\n")
    print(body)


def cmd_context_write(args):
    text = args.body
    if args.file:
        text = open(args.file, encoding="utf-8").read()
    context.write(text, actualizado_por=args.actualizado_por)
    aviso = context.check_budget()
    print("CONTEXT.md actualizado")
    if aviso:
        print(f"AVISO: {aviso}")


def cmd_context_check(args):
    aviso = context.check_budget()
    print(aviso or "dentro del presupuesto")


def cmd_decision_new(args):
    reemplaza = args.reemplaza.split(",") if args.reemplaza else []
    did, fpath = decisions.new_decision(args.titulo, estado=args.estado, reemplaza=reemplaza)
    print(f"creada {did} -> {fpath}")


def cmd_decision_show(args):
    print(decisions.show(args.id))


def cmd_decision_list(args):
    for d in decisions.list_decisions(estado=args.estado):
        print(f"{d['id']:8} [{d['estado']:12}] {d['titulo']} ({d['fecha']})")


def cmd_skill_propose(args):
    sid = skills_registry.propose(
        nombre=args.nombre, tipo=args.tipo, disparador=args.disparador,
        ubicacion=args.ubicacion, creado_por=args.creado_por,
    )
    print(f"propuesta {sid} (estado: propuesta -- requiere 'pctl skill promote' con confirmacion del usuario)")


def cmd_skill_promote(args):
    sid = skills_registry.promote(args.id)
    print(f"{sid} promovida a activa")


def cmd_skill_list(args):
    for r in skills_registry.list_skills(estado=args.estado):
        print(" | ".join(r))


def build_parser():
    p = argparse.ArgumentParser(prog="pctl")
    sub = p.add_subparsers(dest="cmd", required=True)

    t_new = sub.add_parser("task-new", help="crear tarea nueva")
    t_new.add_argument("titulo")
    t_new.add_argument("--prioridad", default="media", choices=paths.TASK_PRIORITIES)
    t_new.add_argument("--tipo", default="feature", choices=paths.TASK_TYPES)
    t_new.add_argument("--creado-por", dest="creado_por", default="usuario", choices=["usuario", "agente"])
    t_new.add_argument("--asignado-a", dest="asignado_a", default="agente", choices=["usuario", "agente", "ambos"])
    t_new.add_argument("--prefix", default=None, help="prefijo de dominio para monorepo, ej PROD")
    t_new.add_argument("--dominio", default=None, help="subcarpeta en tasks/ para monorepo")
    t_new.set_defaults(func=cmd_task_new)

    t_move = sub.add_parser("task-move", help="mover tarea de estado")
    t_move.add_argument("id")
    t_move.add_argument("estado", choices=paths.TASK_STATES)
    t_move.add_argument("--motivo", default=None)
    t_move.add_argument("--force", nargs="?", const="sin motivo detallado", default=None)
    t_move.set_defaults(func=cmd_task_move)

    t_show = sub.add_parser("task-show", help="mostrar una tarea")
    t_show.add_argument("id")
    t_show.set_defaults(func=cmd_task_show)

    t_list = sub.add_parser("task-list", help="listar tareas")
    t_list.add_argument("--estado", default=None, choices=paths.TASK_STATES)
    t_list.set_defaults(func=cmd_task_list)

    st = sub.add_parser("status", help="resumen corto del proyecto")
    st.set_defaults(func=cmd_status)

    ri = sub.add_parser("reindex", help="regenerar indices derivados")
    ri.set_defaults(func=cmd_reindex)

    va = sub.add_parser("validate", help="validar integridad del proyecto")
    va.set_defaults(func=cmd_validate)

    dc = sub.add_parser("doc-check-refs", help="validar solo referencias archivo:linea")
    dc.set_defaults(func=cmd_doc_check_refs)

    s_start = sub.add_parser("session-start", help="iniciar sesion de trabajo")
    s_start.add_argument("--agente", default="agente")
    s_start.set_defaults(func=cmd_session_start)

    s_log = sub.add_parser("session-log", help="agregar evento a la sesion activa")
    s_log.add_argument("id")
    s_log.add_argument("texto")
    s_log.set_defaults(func=cmd_session_log)

    s_close = sub.add_parser("session-close", help="cerrar sesion de trabajo")
    s_close.add_argument("id")
    s_close.add_argument("resumen")
    s_close.add_argument("--tareas", default=None, help="ids separados por coma")
    s_close.set_defaults(func=cmd_session_close)

    a_touch = sub.add_parser("arch-touch", help="registrar/actualizar estado de un dominio")
    a_touch.add_argument("dominio")
    a_touch.add_argument("--estado", default="sin_documentar", choices=arch.ESTADOS)
    a_touch.add_argument("--crear-archivo", dest="crear_archivo", action="store_true")
    a_touch.set_defaults(func=cmd_arch_touch)

    a_list = sub.add_parser("arch-list", help="listar dominios")
    a_list.set_defaults(func=cmd_arch_list)

    f_new = sub.add_parser("flow-new", help="crear un flujo (comportamiento que cruza dominios)")
    f_new.add_argument("nombre")
    f_new.add_argument("--dominios", default=None, help="lista separada por coma")
    f_new.add_argument("--disparador", default=None, help="que dispara este flujo")
    f_new.add_argument("--padre", default=None, help="id del flujo padre, si este es un subflujo")
    f_new.set_defaults(func=cmd_flow_new)

    f_show = sub.add_parser("flow-show", help="mostrar un flujo")
    f_show.add_argument("id")
    f_show.set_defaults(func=cmd_flow_show)

    f_list = sub.add_parser("flow-list", help="listar flujos")
    f_list.add_argument("--dominio", default=None)
    f_list.add_argument("--estado", default=None, choices=flows.ESTADOS)
    f_list.set_defaults(func=cmd_flow_list)

    f_touch = sub.add_parser("flow-touch", help="cambiar estado de un flujo")
    f_touch.add_argument("id")
    f_touch.add_argument("estado", choices=flows.ESTADOS)
    f_touch.set_defaults(func=cmd_flow_touch)

    c_show = sub.add_parser("context-show", help="mostrar CONTEXT.md")
    c_show.set_defaults(func=cmd_context_show)

    c_write = sub.add_parser("context-write", help="reescribir CONTEXT.md completo")
    c_write.add_argument("body", nargs="?", default=None, help="texto directo (o usar --file)")
    c_write.add_argument("--file", default=None, help="leer el cuerpo nuevo desde un archivo")
    c_write.add_argument("--actualizado-por", dest="actualizado_por", default="agente", choices=["agente", "usuario"])
    c_write.set_defaults(func=cmd_context_write)

    c_check = sub.add_parser("context-check", help="verificar que CONTEXT.md no exceda el presupuesto de tamano")
    c_check.set_defaults(func=cmd_context_check)

    d_new = sub.add_parser("decision-new", help="crear un ADR")
    d_new.add_argument("titulo")
    d_new.add_argument("--estado", default="aceptada", choices=decisions.ESTADOS)
    d_new.add_argument("--reemplaza", default=None, help="ids separados por coma")
    d_new.set_defaults(func=cmd_decision_new)

    d_show = sub.add_parser("decision-show", help="mostrar un ADR")
    d_show.add_argument("id")
    d_show.set_defaults(func=cmd_decision_show)

    d_list = sub.add_parser("decision-list", help="listar ADRs")
    d_list.add_argument("--estado", default=None, choices=decisions.ESTADOS)
    d_list.set_defaults(func=cmd_decision_list)

    sk_prop = sub.add_parser("skill-propose", help="proponer skill/script nuevo (no lo activa)")
    sk_prop.add_argument("nombre")
    sk_prop.add_argument("--tipo", required=True, choices=["skill", "script"])
    sk_prop.add_argument("--disparador", required=True)
    sk_prop.add_argument("--ubicacion", required=True)
    sk_prop.add_argument("--creado-por", dest="creado_por", default="agente", choices=["usuario", "agente"])
    sk_prop.set_defaults(func=cmd_skill_propose)

    sk_promote = sub.add_parser("skill-promote", help="activar una skill propuesta (requiere confirmacion humana)")
    sk_promote.add_argument("id")
    sk_promote.set_defaults(func=cmd_skill_promote)

    sk_list = sub.add_parser("skill-list", help="listar skills/scripts registrados")
    sk_list.add_argument("--estado", default=None, choices=["propuesta", "activa", "deprecada"])
    sk_list.set_defaults(func=cmd_skill_list)

    return p


def main():
    paths.ensure_dirs()
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

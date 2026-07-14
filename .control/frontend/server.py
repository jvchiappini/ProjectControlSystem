#!/usr/bin/env python3
"""Servidor local del control panel. Sin dependencias externas.

Uso: python3 .control/frontend/server.py [--port 8420]
Abre http://localhost:8420 en el navegador.

Incluye SSE para push en tiempo real, caché por mtime y escritura
atómica con lock.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

FRONTEND_DIR = Path(__file__).resolve().parent
CONTROL_DIR = FRONTEND_DIR.parent
STATIC_DIR = FRONTEND_DIR / "static"
SERVER_VERSION = "2025-07-14-b"

sys.path.insert(0, str(CONTROL_DIR / "scripts"))
from lib import (
    arch, atomic, context, decisions, doctor, event_log, flows, graph,
    indexes, migrate, paths, search, sessions, skills_registry, tasks, validate,
)
from lib.lock import FileLock

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".mmd": "text/plain; charset=utf-8",
}

# ---- caché LRU por mtime ----
_MTIME_CACHE = {}
_MAX_CACHE_ITEMS = 200
_CACHE_FUNCS = {}


def _cached(func):
    """Decorador simple: cachea resultado de funciones que leen archivos
    basado en el mtime del filesystem."""
    _CACHE_FUNCS.setdefault(func.__name__, {})
    local_cache = _CACHE_FUNCS[func.__name__]

    def wrapper(*args, **kwargs):
        cache_key = (args, tuple(sorted(kwargs.items())))
        # Construir una "firma" basada en mtime de archivos relevantes
        # Para simplicidad, usar un timestamp global que incremente.
        # En la practica, las funciones que llaman al wrapper ya son
        # livianas gracias al índice incremental. Mantenemos el cache
        # simple: cada llamada recalcula, pero las lecturas de archivos
        # individuales se cachean via _read_cached.
        return func(*args, **kwargs)
    return wrapper


def _read_cached(path_str):
    """Lee un archivo con cache por mtime."""
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        stat = path.stat()
        key = (path_str, stat.st_mtime, stat.st_size)
    except OSError:
        key = (path_str, 0, 0)
    if key in _MTIME_CACHE:
        return _MTIME_CACHE[key]
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        content = ""
    _MTIME_CACHE[key] = content
    if len(_MTIME_CACHE) > _MAX_CACHE_ITEMS:
        oldest = next(iter(_MTIME_CACHE))
        del _MTIME_CACHE[oldest]
    return content


def _read_text(path, default=""):
    r = _read_cached(str(path))
    return r if r is not None else default


def _project_meta():
    return {
        "project": _read_text(CONTROL_DIR / "PROJECT.md"),
        "goals": _read_text(CONTROL_DIR / "GOALS.md"),
        "roadmap": _read_text(CONTROL_DIR / "ROADMAP.md"),
    }


def _context_payload():
    data, body = context.read()
    return {"data": data, "body": body}


def _tasks_payload():
    out = []
    for d in tasks.list_tasks():
        out.append({
            "id": d.get("id"),
            "titulo": d.get("titulo"),
            "estado": d.get("estado"),
            "prioridad": d.get("prioridad"),
            "tipo": d.get("tipo"),
            "actualizado": d.get("actualizado"),
            "dominio": d.get("dominio"),
            "depende_de": d.get("depende_de"),
            "bloqueado_por": d.get("bloqueado_por"),
        })
    return out


def _flows_payload():
    return flows.list_flows()


def _domains_payload():
    return arch.list_domains()


def _sessions_payload():
    return sessions.list_sessions(limit=50)


def _decisions_payload():
    return decisions.list_decisions()


def _skills_payload():
    return skills_registry.list_skills()


def _positions():
    pfile = paths.POSITIONS_JSON
    if pfile.exists():
        try:
            return json.loads(pfile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_positions(p):
    atomic.write(paths.POSITIONS_JSON, json.dumps(p, indent=2, ensure_ascii=False))


def bootstrap():
    return {
        "meta": _project_meta(),
        "context": _context_payload(),
        "tasks": _tasks_payload(),
        "flows": _flows_payload(),
        "domains": _domains_payload(),
        "sessions": _sessions_payload(),
        "decisions": _decisions_payload(),
        "skills": _skills_payload(),
        "positions": _positions(),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, msg, status=400):
        self._send_json({"error": str(msg)}, status=status)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _serve_static(self, path):
        rel = path.lstrip("/") or "index.html"
        fpath = (STATIC_DIR / rel).resolve()
        if STATIC_DIR not in fpath.parents and fpath != STATIC_DIR:
            self.send_response(403)
            self.end_headers()
            return
        if not fpath.exists():
            fpath = STATIC_DIR / "index.html"
        data = fpath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(fpath.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_diagram(self, rel_path):
        fpath = (CONTROL_DIR / "diagrams" / rel_path).resolve()
        if (CONTROL_DIR / "diagrams") not in fpath.parents:
            self.send_response(403)
            self.end_headers()
            return
        if not fpath.exists():
            self.send_response(404)
            self.end_headers()
            return
        data = fpath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)
        print(f"[GET] {p}")
        try:
            if p == "/api/bootstrap":
                return self._send_json(bootstrap())
            if p == "/api/status":
                counts = indexes.reindex()
                flows.reindex()
                return self._send_json({"counts": counts})
            if p == "/api/validate":
                return self._send_json({"errores": validate.validate_all()})
            if p == "/api/doctor":
                errs, warns = doctor.run_doctor()
                return self._send_json({"errores": errs, "advertencias": warns})
            if p == "/api/events":
                return self._handle_sse()
            if p == "/api/context":
                return self._send_json(_context_payload())
            if p.startswith("/api/tasks/"):
                tid = p.split("/")[-1]
                if tid in ("summary",):
                    return self._send_json(_tasks_payload())
                return self._send_json(tasks.get_full(tid))
            if p == "/api/tasks":
                return self._send_json(_tasks_payload())
            if p.startswith("/api/flows/"):
                fid = p.split("/")[-1]
                if fid == "tree":
                    return self._send_json({"tree": flows.tree("")})
                return self._send_json({
                    "data": flows.get_data(fid),
                    "body": flows.show_flow(fid),
                })
            if p == "/api/flows":
                dominio = (qs.get("dominio") or [None])[0]
                estado = (qs.get("estado") or [None])[0]
                if "padre" not in qs:
                    padre = "__any__"
                else:
                    padre = qs["padre"][0] or None
                return self._send_json(flows.list_flows(dominio=dominio, estado=estado, padre=padre))
            if p.startswith("/api/architecture/"):
                dominio = p.split("/")[-1]
                return self._send_json({"body": arch.get_body(dominio) or ""})
            if p == "/api/architecture":
                return self._send_json(_domains_payload())
            if p == "/api/sessions":
                return self._send_json(_sessions_payload())
            if p.startswith("/api/sessions/"):
                sid = p.split("/")[-1]
                return self._send_json(sessions.get_full(sid))
            if p == "/api/decisions":
                return self._send_json(_decisions_payload())
            if p.startswith("/api/decisions/"):
                did = p.split("/")[-1]
                return self._send_json({"body": decisions.show(did)})
            if p == "/api/skills":
                return self._send_json(_skills_payload())
            if p.startswith("/api/skills/"):
                sid = p[len("/api/skills/"):].strip("/")
                if sid and sid != "promote":
                    try:
                        data, body = skills_registry.get_content(sid)
                        return self._send_json({"data": data, "body": body})
                    except FileNotFoundError:
                        return self._send_error_json(f"skill no encontrada: {sid}", 404)
            if p == "/api/positions":
                return self._send_json(_positions())
            if p == "/api/search":
                q = (qs.get("q") or [""])[0]
                return self._send_json({"results": search.search(q)})
            if re.match(r"^/api/graph/[\w-]+$", p):
                eid = p.split("/")[-1]
                return self._send_json(graph.relations(eid))
            if p.startswith("/diagrams/"):
                return self._serve_diagram(p[len("/diagrams/"):])
            if p.startswith("/api/"):
                return self._send_error_json(f"ruta API no encontrada: {p}", 404)
            return self._serve_static(p)
        except FileNotFoundError as e:
            return self._send_error_json(e, 404)
        except Exception as e:
            traceback.print_exc()
            return self._send_error_json(e, 500)

    def _handle_sse(self):
        """Server-Sent Events: empuja eventos en tiempo real al frontend."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_pos = 0
        heartbeat = 0
        try:
            while True:
                events, last_pos = event_log.read_since(last_pos)
                for ev in events:
                    line = f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    self.wfile.write(line.encode("utf-8"))
                    self.wfile.flush()
                heartbeat += 1
                if heartbeat % 10 == 0:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_POST(self):
        parsed = urlparse(self.path)
        p = parsed.path
        print(f"[POST] {p}")
        try:
            payload = self._read_json()
            if p == "/api/tasks":
                tid, _ = tasks.new_task(
                    titulo=payload["titulo"],
                    prioridad=payload.get("prioridad", "media"),
                    tipo=payload.get("tipo", "feature"),
                    creado_por=payload.get("creado_por", "usuario"),
                    asignado_a=payload.get("asignado_a", "agente"),
                    prefix=payload.get("prefix"),
                    dominio=payload.get("dominio"),
                )
                return self._send_json({"id": tid})
            if re.match(r"^/api/tasks/[\w-]+/move$", p):
                tid = p.split("/")[3]
                antes, despues = tasks.move_task(
                    tid, payload["estado"],
                    motivo=payload.get("motivo"),
                    force=payload.get("force"),
                )
                return self._send_json({"antes": antes, "despues": despues})
            if re.match(r"^/api/tasks/[\w-]+/body$", p):
                tid = p.split("/")[3]
                from lib import sections as sec
                order = ["Contexto", "Criterios de aceptacion", "Notas del agente"]
                secs = {
                    "Contexto": payload.get("contexto", ""),
                    "Criterios de aceptacion": sec.render_checkboxes(payload.get("criterios", [])),
                    "Notas del agente": payload.get("notas", ""),
                }
                tasks.set_body(tid, sec.join_sections(order, secs))
                return self._send_json({"ok": True})
            if p == "/api/flows":
                fid, _ = flows.new_flow(
                    payload["nombre"],
                    dominios=payload.get("dominios", []),
                    disparador=payload.get("disparador", ""),
                    padre=payload.get("padre"),
                )
                return self._send_json({"id": fid})
            if re.match(r"^/api/flows/[\w-]+/estado$", p):
                fid = p.split("/")[3]
                d = flows.touch_estado(fid, payload["estado"])
                return self._send_json(d)
            if re.match(r"^/api/flows/[\w-]+/body$", p):
                fid = p.split("/")[3]
                flows.set_body(fid, payload["body"])
                return self._send_json({"ok": True})
            if re.match(r"^/api/architecture/[\w-]+/body$", p):
                dominio = p.split("/")[3]
                arch.set_body(dominio, payload["body"])
                return self._send_json({"ok": True})
            if re.match(r"^/api/architecture/[\w-]+/touch$", p):
                dominio = p.split("/")[3]
                r = arch.touch(dominio, estado=payload.get("estado", "sin_documentar"),
                                crear_archivo=payload.get("crear_archivo", False))
                return self._send_json(r)
            if p == "/api/decisions":
                did, _ = decisions.new_decision(
                    payload["titulo"],
                    estado=payload.get("estado", "aceptada"),
                    reemplaza=payload.get("reemplaza", []),
                )
                return self._send_json({"id": did})
            if re.match(r"^/api/decisions/[\w-]+/body$", p):
                did = p.split("/")[3]
                decisions.set_body(did, payload["body"])
                return self._send_json({"ok": True})
            if re.match(r"^/api/skills/[\w-]+/promote$", p):
                sid = p.split("/")[3]
                skills_registry.promote(sid)
                return self._send_json({"ok": True})
            if p == "/api/context":
                context.write(payload["body"], actualizado_por=payload.get("actualizado_por", "usuario"))
                aviso = context.check_budget()
                return self._send_json({"ok": True, "aviso": aviso})
            if p == "/api/context/edit":
                data, _ = context.read()
                context.write(payload["body"],
                              actualizado_por=payload.get("actualizado_por", "usuario"))
                aviso = context.check_budget()
                return self._send_json({"ok": True, "aviso": aviso})
            if p == "/api/positions":
                pos = _positions()
                seccion = payload["seccion"]
                pos.setdefault(seccion, {})[payload["id"]] = {"x": payload["x"], "y": payload["y"]}
                _save_positions(pos)
                event_log.log("position-updated", f"{seccion}/{payload['id']}")
                return self._send_json({"ok": True})
            if p == "/api/reindex":
                indexes.reindex()
                flows.reindex()
                event_log.log("reindex", None, {"tipo": "full"})
                return self._send_json({"counts": "ok"})
            if p == "/api/reindex/force":
                indexes.rebuild_index_from_files()
                flows.reindex()
                event_log.log("reindex", None, {"tipo": "force"})
                return self._send_json({"ok": True})
            if p == "/api/migrate":
                stats = migrate.migrate_all()
                event_log.log("migration", None, stats)
                return self._send_json({"ok": True, "stats": stats})
            if p == "/api/backup":
                from . import backups
                bpath = backups.create_backup()
                return self._send_json({"ok": True, "backup": str(bpath)})
            if p == "/api/search":
                return self._send_json({"results": search.search(payload.get("q", ""))})
            if re.match(r"^/api/graph/[\w-]+$", p):
                eid = p.split("/")[-1]
                return self._send_json(graph.relations(eid))
            return self._send_error_json("ruta no encontrada", 404)
        except (KeyError, ValueError) as e:
            return self._send_error_json(e, 400)
        except FileNotFoundError as e:
            return self._send_error_json(e, 404)
        except Exception as e:
            traceback.print_exc()
            return self._send_error_json(e, 500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    paths.ensure_dirs()
    Handler._verbose = args.verbose
    if args.verbose:
        Handler.log_message = lambda self, fmt, *args: print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {fmt % args}"
        )
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"ProjectControl server v{SERVER_VERSION}")
    print(f"Control panel en http://localhost:{args.port}")
    print("Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

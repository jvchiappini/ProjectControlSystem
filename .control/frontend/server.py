#!/usr/bin/env python3
"""Servidor local del control panel. Sin dependencias externas.

Uso: python3 .control/frontend/server.py [--port 8420]
Abre http://localhost:8420 en el navegador.

Sirve la SPA estatica en static/ y expone una API JSON en /api/* que
opera directamente sobre .control/ reusando los mismos modulos que
pctl.py -- por lo tanto el frontend y cualquier agente que use pctl
nunca se desincronizan: son la misma logica de negocio.
"""
import argparse
import json
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

FRONTEND_DIR = Path(__file__).resolve().parent
CONTROL_DIR = FRONTEND_DIR.parent
STATIC_DIR = FRONTEND_DIR / "static"
POSITIONS_FILE = FRONTEND_DIR / "positions.json"

sys.path.insert(0, str(CONTROL_DIR / "scripts"))
from lib import arch, context, decisions, flows, git, graph, indexes, paths, search, sessions, skills_registry, tasks, validate  # noqa: E402

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".mmd": "text/plain; charset=utf-8",
}


def _read_text(path, default=""):
    return path.read_text(encoding="utf-8") if path.exists() else default


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
        out.append(d)
    return out


def _flows_payload():
    return flows.list_flows()


def _domains_payload():
    return arch.list_domains()


def _sessions_payload():
    out = []
    for f in sorted(paths.SESSIONS_DIR.glob("S-*.md"), reverse=True):
        from lib import fm
        data, body = fm.parse(f.read_text(encoding="utf-8"))
        out.append({"data": data, "body": body})
    return out


def _decisions_payload():
    return decisions.list_decisions()


def _skills_payload():
    rows = skills_registry.list_skills()
    keys = ["id", "nombre", "tipo", "estado", "disparador", "ubicacion", "creado_por"]
    return [dict(zip(keys, r)) for r in rows]


def _positions():
    if POSITIONS_FILE.exists():
        return json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_positions(p):
    POSITIONS_FILE.write_text(json.dumps(p, indent=2), encoding="utf-8")


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
        pass  # silencioso; usar --verbose si hace falta debug

    # ---------- helpers ----------
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
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

    # ---------- routing ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)
        try:
            if p == "/api/bootstrap":
                return self._send_json(bootstrap())
            if p == "/api/status":
                counts = indexes.reindex()
                flows.reindex()
                return self._send_json({"counts": counts})
            if p == "/api/validate":
                return self._send_json({"errores": validate.validate_all()})
            if p == "/api/context":
                return self._send_json(_context_payload())
            if p.startswith("/api/tasks/"):
                tid = p.split("/")[-1]
                return self._send_json(tasks.get_full(tid))
            if p == "/api/tasks":
                return self._send_json(_tasks_payload())
            if p.startswith("/api/flows/"):
                fid = p.split("/")[-1]
                return self._send_json({"data": flows.get_data(fid), "body": flows.show_flow(fid)})
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
            if p == "/api/decisions":
                return self._send_json(_decisions_payload())
            if p.startswith("/api/decisions/"):
                did = p.split("/")[-1]
                return self._send_json({"body": decisions.show(did)})
            if p == "/api/skills":
                return self._send_json(_skills_payload())
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
            return self._serve_static(p)
        except FileNotFoundError as e:
            return self._send_error_json(e, 404)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._send_error_json(e, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        p = parsed.path
        try:
            payload = self._read_json()
            if p == "/api/tasks":
                tid, _ = tasks.new_task(
                    titulo=payload["titulo"], prioridad=payload.get("prioridad", "media"),
                    tipo=payload.get("tipo", "feature"), creado_por=payload.get("creado_por", "usuario"),
                    asignado_a=payload.get("asignado_a", "agente"), prefix=payload.get("prefix"),
                    dominio=payload.get("dominio"),
                )
                indexes.reindex()
                return self._send_json({"id": tid})
            if re.match(r"^/api/tasks/[\w-]+/move$", p):
                tid = p.split("/")[3]
                antes, despues = tasks.move_task(
                    tid, payload["estado"], motivo=payload.get("motivo"), force=payload.get("force")
                )
                indexes.reindex()
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
                    payload["nombre"], dominios=payload.get("dominios", []),
                    disparador=payload.get("disparador", ""), padre=payload.get("padre"),
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
                    payload["titulo"], estado=payload.get("estado", "aceptada"),
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
            if p == "/api/positions":
                pos = _positions()
                seccion = payload["seccion"]
                pos.setdefault(seccion, {})[payload["id"]] = {"x": payload["x"], "y": payload["y"]}
                _save_positions(pos)
                return self._send_json({"ok": True})
            if p == "/api/reindex":
                counts = indexes.reindex()
                flows.reindex()
                return self._send_json({"counts": counts})
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
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._send_error_json(e, 500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8420)
    args = parser.parse_args()
    paths.ensure_dirs()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Control panel en http://localhost:{args.port}")
    print("Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

"""panel.py — AG Launcher (puerto 8282): la tienda de AG Creations.

Enseña el catálogo (catalogo.json) con el estado real de cada app en este Mac (carpeta, entorno,
servicios de launchd, app de escritorio, versión en marcha, versión publicada en GitHub) y permite
instalar, actualizar, abrir, reiniciar y quitar. Las tareas largas corren en un hilo y van escribiendo
un registro que la interfaz lee en vivo. El motor está en agcore/tienda.py.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
WEB = BASE / "panel_web"
PUERTO = 8282

AG_CREATIONS = Path(os.environ.get("AG_CREATIONS", BASE.parent))
sys.path.insert(0, str(AG_CREATIONS))
from agcore import VERSION as AGCORE_VERSION, catalogo, version_de  # noqa: E402
from agcore import tienda  # noqa: E402
from agcore.acceso import Guardia  # noqa: E402

G = Guardia("ag-launcher", PUERTO, BASE)
TIPOS = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png"}

# ----------------------------------------------------------------- tareas
_tareas: dict[str, dict] = {}
_lock = threading.Lock()


def _app(app_id: str) -> dict | None:
    return next((a for a in catalogo() if a["id"] == app_id), None)


def _lanzar(app_id: str, accion: str) -> tuple[int, dict]:
    a = _app(app_id)
    if a is None:
        return 404, {"ok": False, "msg": "app desconocida"}
    fn = {"instalar": tienda.instalar, "actualizar": tienda.actualizar, "desinstalar": tienda.desinstalar,
          "reiniciar": lambda a, log: tienda.reiniciar_panel(a, log)}.get(accion)
    if fn is None:
        return 400, {"ok": False, "msg": "acción desconocida"}
    if app_id == "ag-launcher" and accion == "desinstalar":
        return 400, {"ok": False, "msg": "el launcher no se quita a sí mismo: bórralo desde Aplicaciones"}
    with _lock:
        if any(t["app"] == app_id and not t["fin"] for t in _tareas.values()):
            return 409, {"ok": False, "msg": "esa app ya tiene una tarea en marcha"}
        tid = f"{app_id}-{int(time.time() * 1000)}"
        t = _tareas[tid] = {"id": tid, "app": app_id, "accion": accion, "lineas": [], "fin": False, "ok": None, "inicio": time.time()}

    def correr():
        try:
            t["ok"] = bool(fn(a, lambda l: t["lineas"].append(l)))
        except Exception as e:
            t["lineas"].append(f"✗ error: {type(e).__name__}: {e}")
            t["ok"] = False
        t["fin"] = True
        tienda.invalidar()
        if app_id == "ag-launcher" and accion in ("actualizar", "reiniciar") and t["ok"]:
            threading.Timer(1.0, lambda: os._exit(0)).start()      # launchd (KeepAlive) lo vuelve a levantar
    threading.Thread(target=correr, daemon=True).start()
    with _lock:
        for k in [k for k, v in _tareas.items() if v["fin"] and time.time() - v["inicio"] > 3600]:
            _tareas.pop(k, None)
    return 200, {"ok": True, "tarea": tid}


def _accion(nombre: str, cuerpo: dict) -> tuple[int, dict]:
    app_id = str(cuerpo.get("app", ""))
    if nombre in ("instalar", "actualizar", "desinstalar", "reiniciar"):
        return _lanzar(app_id, nombre)
    a = _app(app_id)
    if nombre == "abrir":
        return (200, {"ok": True, "msg": tienda.abrir(a)}) if a else (404, {"ok": False, "msg": "app desconocida"})
    if nombre == "carpeta":
        return (200, {"ok": True, "msg": tienda.abrir_carpeta(a)}) if a else (404, {"ok": False, "msg": "app desconocida"})
    if nombre == "comprobar":
        tienda.invalidar()
        return 200, {"ok": True, "apps": tienda.estado(refrescar_remoto=True), "msg": "comprobado con GitHub"}
    return 404, {"ok": False, "msg": "acción desconocida"}


def _estatico(ruta: str) -> bool:
    f = (WEB / ("index.html" if ruta in ("/", "") else ruta.lstrip("/"))).resolve()
    return WEB.resolve() in f.parents and f.is_file()


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, cuerpo: bytes, tipo: str):
        self.send_response(code)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo)))
        G.cabeceras(self)
        self.end_headers()
        try:
            self.wfile.write(cuerpo)
        except BrokenPipeError:
            pass

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        try:
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            ruta = u.path
            if not G.host_ok(self) or G.get(self, ruta):
                return
            if not _estatico(ruta) and not G.exigir(self):
                return
            if ruta == "/estado":
                return self._json(200, {"apps": tienda.estado(), "agcore": AGCORE_VERSION, "launcher": version_de(BASE),
                                        "tareas": [t for t in _tareas.values() if not t["fin"] or time.time() - t["inicio"] < 120]})
            if ruta == "/tarea":
                t = _tareas.get(q.get("id", ""))
                return self._json(200, t) if t else self._json(404, {"error": "tarea desconocida"})
            if ruta == "/registro":
                a = _app(q.get("app", ""))
                return self._send(200, (tienda.registro(a) if a else "").encode("utf-8"), "text/plain; charset=utf-8")
            nombre = "index.html" if ruta in ("/", "") else ruta.lstrip("/")
            f = (WEB / nombre).resolve()
            if WEB.resolve() not in f.parents or not f.is_file():
                return self._send(404, b"no encontrado", "text/plain")
            return self._send(200, f.read_bytes(), TIPOS.get(f.suffix, "application/octet-stream"))
        except Exception as e:
            self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        try:
            u = urlparse(self.path)
            if not G.host_ok(self) or not G.post_ok(self) or G.post(self, u.path) or not G.exigir(self):
                return
            cuerpo = G.leer_cuerpo(self)
            if cuerpo is None:
                return
            if not u.path.startswith("/accion/"):
                return self._json(404, {"ok": False})
            code, obj = _accion(u.path[len("/accion/"):], cuerpo)
            return self._json(code, obj)
        except Exception as e:
            self._json(500, {"ok": False, "msg": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    (BASE / "logs").mkdir(exist_ok=True)
    print(f"AG Launcher en http://localhost:{PUERTO}")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()

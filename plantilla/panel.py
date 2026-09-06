"""panel.py — __NOMBRE__ (puerto __PUERTO__): una app de AG Creations.

Servidor local solo con librería estándar. La Guardia de agcore (~/ag-creations) pone la cuenta del
dispositivo, las cabeceras de seguridad y las rutas /ag/*. Añade tus rutas en do_GET/do_POST y tus
acciones en _accion().
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
WEB = BASE / "panel_web"
DATA = BASE / "data"
PUERTO = __PUERTO__

# ── AG Creations: cuenta del dispositivo, seguridad y versión (núcleo común en ~/ag-creations) ──
AG_CREATIONS = Path(os.environ.get("AG_CREATIONS", Path.home() / "ag-creations"))
sys.path.insert(0, str(AG_CREATIONS))
from agcore.acceso import Guardia  # noqa: E402
G = Guardia("__ID__", PUERTO, BASE)

TIPOS = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json"}


def _estado() -> dict:
    """Lo que la interfaz pinta cada pocos segundos. Cambia esto por tus datos."""
    f = DATA / "estado.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"mensaje": "¡Hola! Esta es __NOMBRE__. Aún no tiene datos: edita _estado() en panel.py.", "contador": 0}


def _accion(nombre: str, cuerpo: dict) -> tuple[int, dict]:
    """Las acciones (POST /accion/<nombre>) llegan aquí ya con sesión abierta."""
    if nombre == "contar":
        e = _estado()
        e["contador"] = int(e.get("contador", 0)) + 1
        DATA.mkdir(exist_ok=True)
        (DATA / "estado.json").write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
        return 200, {"ok": True, "msg": f"contador: {e['contador']}"}
    return 404, {"ok": False, "msg": "acción desconocida"}


def _estatico(ruta: str) -> bool:
    """La interfaz (html/css/js) es pública; todo lo demás exige sesión."""
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
            if not _estatico(ruta) and not G.exigir(self):      # los datos solo con sesión abierta
                return
            if ruta == "/estado":
                return self._json(200, _estado())
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
    print(f"__NOMBRE__ en http://localhost:{PUERTO}")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()

"""panel.py — AG Launcher (puerto 8282): la tienda de AG Creations.

Enseña el catálogo con el estado real de cada app en este ordenador (carpeta, entorno, servicios, acceso de
escritorio, versión en marcha, versión publicada) y permite instalar, actualizar, sincronizar, abrir,
reiniciar y quitar. Las tareas largas corren en un hilo y van escribiendo un registro que la interfaz lee
en vivo. El motor está en agcore/tienda.py; lo que depende del sistema, en agcore/so.py.

Rutas (todas con sesión, salvo la interfaz y /ag/*):
  GET  /estado                 apps, versiones, modo (propietario|amigo), so, invitación (solo amigo y fecha), sin_git
  GET  /tarea?id=              el registro en vivo de una tarea
  GET  /registro?app=          últimas líneas del log de una app
  POST /accion/instalar        {app, alpaca_key?, alpaca_secret?, flota?, acepta_ficticio?}  (las claves no se guardan
                               en la tarea ni se devuelven: van directas a .env de Bot Lab)
  POST /accion/actualizar | desinstalar | reiniciar | sincronizar | abrir | carpeta | comprobar   {app}
  POST /accion/invitacion      {codigo} guarda el código de invitación; {borrar: true} lo quita
  POST /accion/instalar_git    (Windows) winget install Git.Git
  POST /accion/relanzar        reinicia el propio launcher

En macOS el panel vive en launchd (com.ag.launcher-panel, KeepAlive): reiniciarlo es salir.
En Windows lo arranca la tarea «AG Creations\\com.ag.launcher-panel» (o el vigilante) con pythonw a través
de launcher_panel.py: aquí no hay KeepAlive, así que relanzarse es arrancar otro proceso y salir; el panel
nuevo espera a que el puerto quede libre. Una sola instancia por puerto.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
WEB = BASE / "panel_web"
PUERTO = int(os.environ.get("AG_LAUNCHER_PUERTO", "8282"))     # otro puerto solo para pruebas (una copia en modo amigo)

AG_CREATIONS = Path(os.environ.get("AG_CREATIONS", BASE.parent))
sys.path.insert(0, str(AG_CREATIONS))
from agcore import ES_WIN, VERSION as AGCORE_VERSION, version_de  # noqa: E402
from agcore import invitacion, tienda  # noqa: E402
from agcore import so as SO  # noqa: E402
from agcore.acceso import Guardia  # noqa: E402

G = Guardia("ag-launcher", PUERTO, BASE)
TIPOS = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png"}
LABEL = "AG Creations\\com.ag.launcher-panel" if ES_WIN else "com.ag.launcher-panel"

# ----------------------------------------------------------------- tareas
_tareas: dict[str, dict] = {}
_lock = threading.Lock()


def _app(app_id: str) -> dict | None:
    return tienda.app(app_id)


def _relanzar_pronto() -> None:
    threading.Timer(1.0, lambda: SO.relanzarme(LABEL, Path(sys.argv[0]).resolve())).start()


def _lanzar(app_id: str, accion: str, datos: dict | None = None) -> tuple[int, dict]:
    if accion == "instalar_git":
        a, fn = {"id": "git", "nombre": "git"}, lambda a, log: tienda.instalar_git(log)
    else:
        a = _app(app_id)
        if a is None:
            return 404, {"ok": False, "msg": "app desconocida"}
        fn = {"instalar": lambda a, log: tienda.instalar(a, log, datos), "actualizar": tienda.actualizar,
              "desinstalar": tienda.desinstalar, "sincronizar": tienda.sincronizar,
              "reiniciar": lambda a, log: tienda.reiniciar_panel(a, log)}.get(accion)
        if fn is None:
            return 400, {"ok": False, "msg": "acción desconocida"}
        if app_id == "ag-launcher" and accion == "desinstalar":
            return 400, {"ok": False, "msg": "el launcher no se quita a sí mismo: borra su carpeta y su acceso"}
        if app_id == "ag-launcher" and accion == "reiniciar":
            _relanzar_pronto()
            return 200, {"ok": True, "msg": "el launcher se reinicia; vuelve en unos segundos"}
    with _lock:
        if any(t["app"] == a["id"] and not t["fin"] for t in _tareas.values()):
            return 409, {"ok": False, "msg": "esa app ya tiene una tarea en marcha"}
        tid = f"{a['id']}-{int(time.time() * 1000)}"
        t = _tareas[tid] = {"id": tid, "app": a["id"], "accion": accion, "lineas": [], "fin": False, "ok": None, "inicio": time.time()}

    def correr():
        try:
            t["ok"] = bool(fn(a, lambda l: t["lineas"].append(l)))
        except Exception as e:
            t["lineas"].append(invitacion.enmascarar(f"✗ error: {type(e).__name__}: {e}"))
            t["ok"] = False
        t["fin"] = True
        tienda.invalidar()
        if a["id"] == "ag-launcher" and accion == "actualizar" and t["ok"]:
            _relanzar_pronto()
    threading.Thread(target=correr, daemon=True).start()
    with _lock:
        for k in [k for k, v in _tareas.items() if v["fin"] and time.time() - v["inicio"] > 3600]:
            _tareas.pop(k, None)
    return 200, {"ok": True, "tarea": tid}


def _accion(nombre: str, cuerpo: dict) -> tuple[int, dict]:
    app_id = str(cuerpo.get("app", ""))
    if nombre == "instalar":
        # las claves de Alpaca van a la tarea y de ahí a .env; nunca al registro ni a la respuesta
        datos = {k: cuerpo.get(k) for k in ("alpaca_key", "alpaca_secret", "flota", "acepta_ficticio")}
        return _lanzar(app_id, nombre, datos)
    if nombre in ("actualizar", "desinstalar", "reiniciar", "sincronizar", "instalar_git"):
        return _lanzar(app_id, nombre)
    if nombre == "invitacion":
        if cuerpo.get("borrar"):
            invitacion.borrar()
            tienda.invalidar()
            return 200, {"ok": True, "msg": "invitación borrada"}
        try:
            inv = invitacion.guardar(str(cuerpo.get("codigo", "")))
        except invitacion.ErrorInvitacion as e:
            return 400, {"ok": False, "msg": str(e)}
        tienda.invalidar()
        return 200, {"ok": True, "msg": f"invitación guardada: bienvenido, {inv['amigo']}", "invitacion": invitacion.publica(inv)}
    if nombre == "relanzar":
        _relanzar_pronto()
        return 200, {"ok": True, "msg": "el launcher se reinicia; vuelve en unos segundos"}
    if nombre == "comprobar":
        tienda.invalidar()
        return 200, {"ok": True, "apps": tienda.estado(refrescar_remoto=True), "msg": "comprobado con GitHub"}
    a = _app(app_id)
    if a is None:
        return 404, {"ok": False, "msg": "app desconocida"}
    if nombre == "abrir":
        return 200, {"ok": True, "msg": tienda.abrir(a)}
    if nombre == "carpeta":
        return 200, {"ok": True, "msg": tienda.abrir_carpeta(a)}
    return 404, {"ok": False, "msg": "acción desconocida"}


def _estado() -> dict:
    inv = invitacion.leer()
    return {"apps": tienda.estado(), "agcore": AGCORE_VERSION, "launcher": version_de(BASE), "so": "windows" if ES_WIN else "mac",
            "modo": tienda.modo(), "invitacion": invitacion.publica(inv) if tienda.modo() == "amigo" else None,
            "sin_git": SO.git() is None, "firmas": tienda.firmas.disponible(), "repo": next((a.get("repo") for a in tienda.catalogo() if a["id"] == "ag-launcher"), None),
            "raiz": str(AG_CREATIONS).replace(str(Path.home()), "~"), "python": sys.version.split()[0],
            "tareas": [t for t in _tareas.values() if not t["fin"] or time.time() - t["inicio"] < 120]}


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
        except (BrokenPipeError, ConnectionResetError):
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
                return self._json(200, _estado())
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
            self._json(500, {"ok": False, "msg": invitacion.enmascarar(f"{type(e).__name__}: {e}")})


def _puerto_libre(espera: float = 15.0) -> bool:
    """Una sola instancia por puerto. Tras relanzarse, el proceso viejo tarda un momento en soltarlo."""
    fin = time.time() + espera
    while True:
        try:
            with socket.create_connection(("127.0.0.1", PUERTO), timeout=0.3):
                pass
        except OSError:
            return True
        if time.time() > fin:
            return False
        time.sleep(0.5)


def _registro_a_fichero() -> None:
    """Sin consola (pythonw, tareas programadas) la salida va a logs/panel.log."""
    (BASE / "logs").mkdir(exist_ok=True)
    if ES_WIN or sys.stdout is None or sys.stderr is None:
        f = open(BASE / "logs" / "panel.log", "a", encoding="utf-8", errors="replace", buffering=1)
        sys.stdout = sys.stderr = f
    else:
        for s in (sys.stdout, sys.stderr):        # bajo launchd la salida es un fichero: que no se quede en el búfer
            try:
                s.reconfigure(line_buffering=True)
            except (AttributeError, ValueError):
                pass


def main() -> None:
    _registro_a_fichero()
    if not _puerto_libre():
        print(f"AG Launcher: el puerto {PUERTO} ya está ocupado (otro panel en marcha): salgo")
        return
    print(f"AG Launcher v{version_de(BASE)} en http://localhost:{PUERTO} · modo {tienda.modo()} · {time.strftime('%Y-%m-%d %H:%M:%S')}")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()


if __name__ == "__main__":
    main()

"""acceso.py — la Guardia: seguridad y acceso de un panel de AG Creations.

Cada panel (un BaseHTTPRequestHandler) crea una Guardia y la llama en cuatro sitios:

    G = Guardia("llm-lab", PUERTO, BASE)

    # al responder cualquier cosa:      G.cabeceras(self)       cabeceras de seguridad (CSP, nosniff…)
    # al principio de do_GET/do_POST:   if not G.host_ok(self): return       (DNS rebinding)
    #                                   if G.get(self, ruta): return          rutas /ag/* (acceso, términos, privacidad, licencia…)
    # en do_POST además:                if not G.post_ok(self): return        (cabecera X-AG + Origin: CSRF)
    #                                   if G.post(self, ruta): return         /ag/auth/*
    # en las rutas con datos:           cuenta = G.exigir(self); if not cuenta: return   (401)

La sesión va en una cookie HttpOnly + SameSite=Strict propia de cada app. Las cuentas son las
del dispositivo (agcore.cuentas): la misma cuenta abre todas las apps.
"""
from __future__ import annotations

import hashlib
import http.cookies as _cookies
import json
import time
from pathlib import Path

from . import EMPRESA, RAIZ, VERSION, app_del_catalogo, catalogo, cuentas

WEB = Path(__file__).resolve().parent / "web"
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self' data:; connect-src 'self'; "
       "worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
MAX_CUERPO = 64 * 1024
TIPOS = {".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
# Lo único del catálogo que sale por /ag/version y /ag/cuentas (SIN sesión): nada de carpetas, servicios,
# instaladores ni repositorios privados de catalogo.local.json. Es lo que usan acceso.js (menú y «Acerca de»)
# y tienda._version_viva (solo "version" del nivel superior).
CAMPOS_CATALOGO = ("id", "nombre", "icono", "puerto", "version", "descripcion")


class Guardia:
    def __init__(self, app: str, puerto: int, base: Path, terminos: str = "TERMINOS.md"):
        self.app, self.puerto, self.base = app, puerto, Path(base)
        self.terminos = self.base / terminos
        self.licencia = RAIZ / "LICENCIA.md"
        self.hosts = {f"localhost:{puerto}", f"127.0.0.1:{puerto}", f"[::1]:{puerto}"}
        self.origenes = {f"http://{h}" for h in self.hosts}
        self.cookie = "ag_" + app.replace("-", "_")

    # ------------------------------------------------------------ info
    @property
    def privacidad(self) -> Path:
        """PRIVACIDAD.md de la app si tiene una propia; si no, la común de ~/ag-creations."""
        propia = self.base / "PRIVACIDAD.md"
        return propia if propia.exists() else RAIZ / "PRIVACIDAD.md"

    def terminos_version(self) -> str:
        """Cambia sola cuando cambia TERMINOS.md o PRIVACIDAD.md: la app vuelve a pedir aceptarlos.

        Es el sha256 de los dos ficheros seguidos (si no hay PRIVACIDAD.md, solo de TERMINOS.md)."""
        try:
            h = hashlib.sha256(self.terminos.read_bytes())
        except OSError:
            return "sin-terminos"
        try:
            h.update(self.privacidad.read_bytes())
        except OSError:
            pass
        return h.hexdigest()[:12]

    def info(self) -> dict:
        a = app_del_catalogo(self.app)
        return {"app": self.app, "nombre": a.get("nombre", self.app), "icono": a.get("icono", "🧩"),
                "version": a.get("version") or "?", "empresa": EMPRESA, "agcore": VERSION,
                "terminos": self.terminos_version(),
                "catalogo": [{k: x[k] for k in CAMPOS_CATALOGO if k in x} for x in catalogo()]}

    # ------------------------------------------------------------ respuesta
    def cabeceras(self, h) -> None:
        h.send_header("X-Content-Type-Options", "nosniff")
        h.send_header("Referrer-Policy", "no-referrer")
        h.send_header("X-Frame-Options", "DENY")
        h.send_header("Content-Security-Policy", CSP)
        h.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    def _responder(self, h, code: int, cuerpo: bytes, tipo: str, cookie: str | None = None) -> None:
        h.send_response(code)
        h.send_header("Content-Type", tipo)
        h.send_header("Cache-Control", "no-store")
        h.send_header("Content-Length", str(len(cuerpo)))
        self.cabeceras(h)
        if cookie is not None:
            h.send_header("Set-Cookie", cookie)
        h.end_headers()
        try:
            h.wfile.write(cuerpo)
        except BrokenPipeError:
            pass

    def _json(self, h, code: int, obj, cookie: str | None = None) -> None:
        self._responder(h, code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"),
                        "application/json; charset=utf-8", cookie)

    def _cookie(self, token: str | None) -> str:
        if token:
            return f"{self.cookie}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={cuentas.DIAS_SESION * 86400}"
        return f"{self.cookie}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"

    # ------------------------------------------------------------ seguridad
    def host_ok(self, h) -> bool:
        host = (h.headers.get("Host") or "").strip().lower()
        if host in self.hosts:
            return True
        self._responder(h, 421, b"host no permitido", "text/plain; charset=utf-8")
        return False

    def post_ok(self, h) -> bool:
        """Toda petición POST debe venir de la propia app: cabecera X-AG y origen local."""
        if h.headers.get("X-AG") != "1":
            self._json(h, 403, {"ok": False, "error": "petición no válida (falta la cabecera de la app)"})
            return False
        origen = (h.headers.get("Origin") or "").strip().lower()
        if origen and origen not in self.origenes:
            self._json(h, 403, {"ok": False, "error": "origen no permitido"})
            return False
        return True

    def token(self, h) -> str | None:
        c = _cookies.SimpleCookie()
        try:
            c.load(h.headers.get("Cookie") or "")
        except _cookies.CookieError:
            return None
        return c[self.cookie].value if self.cookie in c else None

    def sesion(self, h) -> dict | None:
        return cuentas.sesion(self.token(h), self.app)

    def exigir(self, h) -> dict | None:
        """La cuenta de la sesión, o responde 401 y devuelve None."""
        s = self.sesion(h)
        if s is None:
            self._json(h, 401, {"ok": False, "error": "sesion"})
        return s

    def leer_cuerpo(self, h) -> dict | None:
        n = int(h.headers.get("Content-Length") or 0)
        if n > MAX_CUERPO:
            self._json(h, 413, {"ok": False, "error": "petición demasiado grande"})
            return None
        try:
            cuerpo = json.loads(h.rfile.read(n).decode("utf-8") or "{}") if n else {}
        except ValueError:
            cuerpo = None
        if not isinstance(cuerpo, dict):
            self._json(h, 400, {"ok": False, "error": "cuerpo no válido"})
            return None
        return cuerpo

    # ------------------------------------------------------------ rutas /ag/*
    def get(self, h, ruta: str) -> bool:
        if not ruta.startswith("/ag/"):
            return False
        if ruta == "/ag/yo":
            s = self.sesion(h)
            if not s:
                self._json(h, 401, {"cuenta": None, "error": "sesion"})
            else:
                self._json(h, 200, {"cuenta": s, "terminos_pendientes": s["terminos"].get(self.app) != self.terminos_version()})
        elif ruta == "/ag/cuentas":
            self._json(h, 200, {"cuentas": cuentas.listar(), "app": self.info()})
        elif ruta == "/ag/version":
            self._json(h, 200, self.info())
        elif ruta in ("/ag/terminos", "/ag/privacidad", "/ag/licencia"):
            f, titulo = {"/ag/terminos": (self.terminos, "Términos"), "/ag/privacidad": (self.privacidad, "Política de privacidad"),
                         "/ag/licencia": (self.licencia, "Licencia")}[ruta]
            try:
                cuerpo = f.read_bytes()
            except OSError:
                cuerpo = f"# {titulo} de {self.app}\n\n(esta app aún no tiene {f.name})".encode()
            self._responder(h, 200, cuerpo, "text/markdown; charset=utf-8")
        elif ruta in ("/ag/acceso.js", "/ag/acceso.css"):
            f = WEB / ruta[4:]
            self._responder(h, 200, f.read_bytes(), TIPOS[f.suffix])
        else:
            self._responder(h, 404, b"no encontrado", "text/plain; charset=utf-8")
        return True

    def post(self, h, ruta: str) -> bool:
        if not ruta.startswith("/ag/"):
            return False
        cuerpo = self.leer_cuerpo(h)
        if cuerpo is None:
            return True
        try:
            if ruta == "/ag/auth/crear":
                c = cuentas.crear(str(cuerpo.get("nombre", "")), str(cuerpo.get("apellido", "")), cuerpo.get("contrasena", ""),
                                  self.app, self.terminos_version(), bool(cuerpo.get("acepta_terminos")))
                token = cuentas.abrir_sesion(c["id"], self.app)
                self._json(h, 200, {"ok": True, "cuenta": cuentas.sesion(token, self.app)}, self._cookie(token))
            elif ruta == "/ag/auth/entrar":
                cid = str(cuerpo.get("id", ""))
                c = cuentas.comprobar(cid, cuerpo.get("contrasena", ""))
                if c is None:
                    time.sleep(0.4)
                    return self._json(h, 401, {"ok": False, "error": "contraseña incorrecta"}) or True
                if not cuentas.terminos_aceptados(cid, self.app, self.terminos_version()):
                    if not cuerpo.get("acepta_terminos"):
                        return self._json(h, 428, {"ok": False, "error": "terminos", "cuenta": c}) or True
                    cuentas.aceptar_terminos(cid, self.app, self.terminos_version())
                token = cuentas.abrir_sesion(cid, self.app)
                self._json(h, 200, {"ok": True, "cuenta": cuentas.sesion(token, self.app)}, self._cookie(token))
            elif ruta == "/ag/auth/aceptar":
                s = self.exigir(h)
                if s:
                    cuentas.aceptar_terminos(s["id"], self.app, self.terminos_version())
                    self._json(h, 200, {"ok": True})
            elif ruta == "/ag/auth/salir":
                cuentas.cerrar_sesion(self.token(h))
                self._json(h, 200, {"ok": True}, self._cookie(None))
            elif ruta == "/ag/auth/contrasena":
                s = self.exigir(h)
                if s:
                    cuentas.cambiar_contrasena(s["id"], cuerpo.get("actual", ""), cuerpo.get("nueva", ""))
                    self._json(h, 200, {"ok": True}, self._cookie(None))
            elif ruta == "/ag/auth/borrar":
                s = self.exigir(h)
                if s:
                    cuentas.borrar(s["id"], cuerpo.get("contrasena", ""))
                    self._json(h, 200, {"ok": True}, self._cookie(None))
            else:
                self._json(h, 404, {"ok": False, "error": "ruta desconocida"})
        except cuentas.ErrorCuenta as e:
            self._json(h, 400, {"ok": False, "error": str(e)})
        return True

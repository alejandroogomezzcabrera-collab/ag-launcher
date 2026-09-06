"""Tests de agcore: cuentas por dispositivo, términos por app y la Guardia HTTP."""
import json
import os
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


@pytest.fixture
def datos(tmp_path, monkeypatch):
    monkeypatch.setenv("AG_DATOS", str(tmp_path / "datos"))
    monkeypatch.setenv("AG_SIN_EXTERNAS", "1")
    from agcore import cuentas
    cuentas._fallos.clear()
    return cuentas


def test_cuenta_compartida_entre_apps(datos):
    c = datos.crear("Ana", "López", "secreta123", "app-a", "t1", True)
    assert c["id"] == "ana-lopez" and c["terminos"] == {"app-a": "t1"}
    assert datos.comprobar("ana-lopez", "secreta123")["nombre"] == "Ana"
    assert datos.comprobar("ana-lopez", "mal") is None
    # la misma cuenta aparece en otra app, pero aún no ha aceptado sus términos
    assert datos.listar()[0]["id"] == "ana-lopez"
    assert not datos.terminos_aceptados("ana-lopez", "app-b", "t9")
    datos.aceptar_terminos("ana-lopez", "app-b", "t9")
    assert datos.terminos_aceptados("ana-lopez", "app-b", "t9")
    assert not datos.terminos_aceptados("ana-lopez", "app-b", "t10")     # si cambian los términos, se vuelven a pedir


def test_sesiones_por_app(datos):
    datos.crear("Ana", "López", "secreta123", "app-a", "t1", True)
    tok = datos.abrir_sesion("ana-lopez", "app-a")
    assert datos.sesion(tok, "app-a")["id"] == "ana-lopez"
    assert datos.sesion(tok, "app-b") is None                              # el token es de una app
    datos.cerrar_sesion(tok)
    assert datos.sesion(tok, "app-a") is None
    guardado = json.loads((Path(os.environ["AG_DATOS"]) / "cuentas.json").read_text())
    assert "secreta123" not in json.dumps(guardado)


def test_validaciones(datos):
    with pytest.raises(datos.ErrorCuenta):
        datos.crear("A", "López", "secreta123", "x", "t", True)
    with pytest.raises(datos.ErrorCuenta):
        datos.crear("Ana", "López", "corta", "x", "t", True)
    with pytest.raises(datos.ErrorCuenta):
        datos.crear("Ana", "López", "secreta123", "x", "t", False)
    datos.crear("Ana", "López", "secreta123", "x", "t", True)
    with pytest.raises(datos.ErrorCuenta):
        datos.crear("ana", "lopez", "otra12345", "x", "t", True)          # misma id
    for _ in range(5):
        datos.comprobar("ana-lopez", "mal")
    with pytest.raises(datos.ErrorCuenta):
        datos.comprobar("ana-lopez", "secreta123")                         # bloqueada un rato


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("AG_DATOS", str(tmp_path / "datos"))
    monkeypatch.setenv("AG_SIN_EXTERNAS", "1")
    from agcore import cuentas
    from agcore.acceso import Guardia
    cuentas._fallos.clear()
    base = tmp_path / "app"; base.mkdir()
    (base / "TERMINOS.md").write_text("# Términos de prueba\n\nPertenece a AG Creations.\n", encoding="utf-8")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    puerto = srv.server_address[1]
    G = Guardia("prueba", puerto, base)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            if not G.host_ok(self): return
            if G.get(self, self.path): return
            if self.path == "/datos":
                if not G.exigir(self): return
                self.send_response(200); self.send_header("Content-Type", "application/json"); G.cabeceras(self); self.end_headers(); self.wfile.write(b'{"secreto":1}')
                return
            self.send_response(200); self.send_header("Content-Type", "text/html"); G.cabeceras(self); self.end_headers(); self.wfile.write(b"<html>")
        def do_POST(self):
            if not G.host_ok(self) or not G.post_ok(self): return
            if G.post(self, self.path): return
            if not G.exigir(self): return
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":true}')
    srv.RequestHandlerClass = H
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{puerto}", puerto
    srv.shutdown()


def pedir(url, metodo="GET", cuerpo=None, cabeceras=None, cookie=None):
    req = urllib.request.Request(url, method=metodo, data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    for k, v in (cabeceras or {}).items():
        req.add_header(k, v)
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


def test_guardia_http(servidor):
    url, puerto = servidor
    st, cuerpo, cab = pedir(url + "/")
    assert st == 200 and "frame-ancestors 'none'" in cab["Content-Security-Policy"] and cab["X-Frame-Options"] == "DENY"
    assert pedir(url + "/datos")[0] == 401                                          # sin sesión
    assert pedir(url + "/", cabeceras={"Host": "evil.com"})[0] == 421              # DNS rebinding
    assert pedir(url + "/ag/auth/crear", "POST", {})[0] == 403                     # sin cabecera X-AG
    assert pedir(url + "/ag/auth/crear", "POST", {}, {"X-AG": "1", "Origin": "http://evil.com"})[0] == 403
    st, cuerpo, cab = pedir(url + "/ag/auth/crear", "POST", {"nombre": "Ana", "apellido": "López", "contrasena": "secreta123", "acepta_terminos": True}, {"X-AG": "1", "Origin": f"http://localhost:{puerto}"})
    assert st == 200 and "HttpOnly" in cab["Set-Cookie"] and "SameSite=Strict" in cab["Set-Cookie"]
    cookie = cab["Set-Cookie"].split(";")[0]
    st, cuerpo, _ = pedir(url + "/ag/yo", cookie=cookie)
    assert st == 200 and json.loads(cuerpo)["cuenta"]["nombre"] == "Ana" and json.loads(cuerpo)["terminos_pendientes"] is False
    assert pedir(url + "/datos", cookie=cookie)[0] == 200
    assert json.loads(pedir(url + "/ag/cuentas")[1])["cuentas"][0]["id"] == "ana-lopez"
    assert json.loads(pedir(url + "/ag/version")[1])["empresa"] == "AG Creations"
    # entrar de nuevo con la misma cuenta (bienvenido de nuevo)
    st, cuerpo, _ = pedir(url + "/ag/auth/entrar", "POST", {"id": "ana-lopez", "contrasena": "secreta123"}, {"X-AG": "1"})
    assert st == 200
    # si cambian los términos, entrar exige aceptarlos
    (Path(url and servidor and __import__("os").environ["AG_DATOS"]).parent / "app" / "TERMINOS.md").write_text("# Términos nuevos\n\nAG Creations.\n", encoding="utf-8")
    st, cuerpo, _ = pedir(url + "/ag/auth/entrar", "POST", {"id": "ana-lopez", "contrasena": "secreta123"}, {"X-AG": "1"})
    assert st == 428 and json.loads(cuerpo)["error"] == "terminos"
    st, _, _ = pedir(url + "/ag/auth/entrar", "POST", {"id": "ana-lopez", "contrasena": "secreta123", "acepta_terminos": True}, {"X-AG": "1"})
    assert st == 200
    assert json.loads(pedir(url + "/ag/yo", cookie=cookie)[1])["terminos_pendientes"] is False
    # salir
    st, _, cab = pedir(url + "/ag/auth/salir", "POST", {}, {"X-AG": "1"}, cookie=cookie)
    assert st == 200 and "Max-Age=0" in cab["Set-Cookie"]
    assert pedir(url + "/datos", cookie=cookie)[0] == 401

"""cuentas.py — la cuenta AG Creations de este dispositivo.

Una sola lista de cuentas para todas las apps, en la carpeta de datos del usuario
(macOS: ~/Library/Application Support/AG Creations; Windows: %APPDATA%\\AG Creations):
  cuentas.json   nombre, apellido, HASH de la contraseña (scrypt + sal) y qué términos aceptó en cada app
  sesiones.json  sesiones abiertas: hash del token, cuenta, app y caducidad

No hay servidor de cuentas. Crear una cuenta no envía nada a ningún sitio.
La misma cuenta abre todas las apps: al entrar en otra app aparece «bienvenido de nuevo»
y solo hay que escribir la contraseña (y aceptar los términos de esa app la primera vez).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
import unicodedata
from datetime import datetime

from . import carpeta_datos

SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
MIN_CONTRASENA = 8
MAX_CONTRASENA = 200
DIAS_SESION = 30
MAX_FALLOS = 5
BLOQUEO_S = 60
MAX_SESIONES = 100

_fallos: dict[str, list] = {}


class ErrorCuenta(ValueError):
    pass


def _ruta(nombre: str):
    return carpeta_datos() / nombre


def _leer(nombre: str, defecto):
    r = _ruta(nombre)
    try:
        return json.loads(r.read_text(encoding="utf-8")) if r.exists() else defecto
    except ValueError:
        return defecto


def _escribir(nombre: str, datos) -> None:
    r = _ruta(nombre)
    tmp = r.with_suffix(r.suffix + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, r)


def _normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _nombre_valido(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    if not (2 <= len(s) <= 40) or not re.fullmatch(r"[^\W\d_]+(?:[ '\-][^\W\d_]+)*", s):
        raise ErrorCuenta("nombre y apellido: solo letras, entre 2 y 40 caracteres")
    return s


def _hash(contrasena: str, sal: bytes) -> bytes:
    return hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, **SCRYPT)


def _id_de(nombre: str, apellido: str) -> str:
    return _normalizar(nombre + " " + apellido).replace(" ", "-")


def _publica(c: dict) -> dict:
    return {"id": c["id"], "nombre": c["nombre"], "apellido": c["apellido"], "creada": c.get("creada"),
            "terminos": c.get("terminos", {}), "ultima": c.get("ultima", {})}


# ----------------------------------------------------------------- cuentas
def listar() -> list[dict]:
    """Las cuentas de este dispositivo, sin nada secreto (para «bienvenido de nuevo»)."""
    return [_publica(c) for c in _leer("cuentas.json", [])]


def hay_cuentas() -> bool:
    return bool(_leer("cuentas.json", []))


def _comprobar_contrasena_nueva(contrasena, nombre: str, apellido: str) -> None:
    if not isinstance(contrasena, str) or not (MIN_CONTRASENA <= len(contrasena) <= MAX_CONTRASENA):
        raise ErrorCuenta(f"la contraseña debe tener entre {MIN_CONTRASENA} y {MAX_CONTRASENA} caracteres")
    if _normalizar(contrasena) in (_normalizar(nombre), _normalizar(apellido), _normalizar(nombre + apellido),
                                   "12345678", "123456789", "contrasena", "password", "qwertyui"):
        raise ErrorCuenta("esa contraseña es demasiado fácil de adivinar")


def crear(nombre: str, apellido: str, contrasena: str, app: str, terminos_version: str, acepta_terminos: bool) -> dict:
    nombre, apellido = _nombre_valido(nombre), _nombre_valido(apellido)
    if not acepta_terminos:
        raise ErrorCuenta("hay que leer y aceptar los términos")
    _comprobar_contrasena_nueva(contrasena, nombre, apellido)
    cuentas = _leer("cuentas.json", [])
    cid = _id_de(nombre, apellido)
    if any(c["id"] == cid for c in cuentas):
        raise ErrorCuenta("ya existe una cuenta con ese nombre y apellido en este dispositivo: entra con ella")
    sal = secrets.token_bytes(16)
    ahora = datetime.now().isoformat(timespec="seconds")
    cuentas.append({"id": cid, "nombre": nombre, "apellido": apellido, "sal": sal.hex(),
                    "hash": _hash(contrasena, sal).hex(), "scrypt": SCRYPT, "creada": ahora,
                    "terminos": {app: terminos_version}, "ultima": {app: ahora}})
    _escribir("cuentas.json", cuentas)
    return _publica(cuentas[-1])


def _cuenta(cid: str) -> dict | None:
    return next((c for c in _leer("cuentas.json", []) if c["id"] == cid), None)


def comprobar(cid: str, contrasena: str) -> dict | None:
    """Cuenta pública si la contraseña es correcta; None si no. Bloqueo tras varios fallos."""
    ahora = time.time()
    n, hasta = _fallos.get(cid, [0, 0.0])
    if hasta > ahora:
        raise ErrorCuenta(f"demasiados intentos: espera {int(hasta - ahora) + 1} s")
    c = _cuenta(cid)
    ok = False
    if c is not None and isinstance(contrasena, str) and len(contrasena) <= MAX_CONTRASENA:
        calc = hashlib.scrypt(contrasena.encode("utf-8"), salt=bytes.fromhex(c["sal"]), **c.get("scrypt", SCRYPT))
        ok = hmac.compare_digest(calc, bytes.fromhex(c["hash"]))
    else:
        _hash(contrasena if isinstance(contrasena, str) else "", b"0" * 16)   # mismo tiempo aunque no exista
    if not ok:
        n += 1
        _fallos[cid] = [0 if n >= MAX_FALLOS else n, ahora + BLOQUEO_S if n >= MAX_FALLOS else 0.0]
        return None
    _fallos.pop(cid, None)
    return _publica(c)


def terminos_aceptados(cid: str, app: str, version: str) -> bool:
    c = _cuenta(cid)
    return bool(c) and c.get("terminos", {}).get(app) == version


def aceptar_terminos(cid: str, app: str, version: str) -> None:
    cuentas = _leer("cuentas.json", [])
    for c in cuentas:
        if c["id"] == cid:
            c.setdefault("terminos", {})[app] = version
    _escribir("cuentas.json", cuentas)


def _tocar(cid: str, app: str) -> None:
    cuentas = _leer("cuentas.json", [])
    for c in cuentas:
        if c["id"] == cid:
            c.setdefault("ultima", {})[app] = datetime.now().isoformat(timespec="seconds")
    _escribir("cuentas.json", cuentas)


def cambiar_contrasena(cid: str, actual: str, nueva: str) -> None:
    c = comprobar(cid, actual)
    if c is None:
        raise ErrorCuenta("la contraseña actual no es correcta")
    _comprobar_contrasena_nueva(nueva, c["nombre"], c["apellido"])
    cuentas = _leer("cuentas.json", [])
    for c in cuentas:
        if c["id"] == cid:
            sal = secrets.token_bytes(16)
            c["sal"], c["hash"], c["scrypt"] = sal.hex(), _hash(nueva, sal).hex(), SCRYPT
    _escribir("cuentas.json", cuentas)
    cerrar_todas(cid)


def borrar(cid: str, contrasena: str) -> None:
    """Borra la cuenta de este dispositivo (solo la cuenta: los datos de las apps no se tocan)."""
    if comprobar(cid, contrasena) is None:
        raise ErrorCuenta("la contraseña no es correcta")
    _escribir("cuentas.json", [c for c in _leer("cuentas.json", []) if c["id"] != cid])
    cerrar_todas(cid)


# ----------------------------------------------------------------- sesiones
def _sesiones() -> list[dict]:
    ahora = time.time()
    return [s for s in _leer("sesiones.json", []) if s.get("caduca", 0) > ahora]


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def abrir_sesion(cid: str, app: str) -> str:
    """Devuelve el token (solo viaja en la cookie de esa app). Se guarda su hash."""
    token = secrets.token_urlsafe(32)
    ses = _sesiones()
    ses.append({"h": _token_hash(token), "cuenta": cid, "app": app,
                "desde": datetime.now().isoformat(timespec="seconds"), "caduca": time.time() + DIAS_SESION * 86400})
    _escribir("sesiones.json", ses[-MAX_SESIONES:])
    _tocar(cid, app)
    return token


def sesion(token: str | None, app: str) -> dict | None:
    """La cuenta pública de un token válido para esta app, o None."""
    if not token or len(token) > 200:
        return None
    h = _token_hash(token)
    s = next((s for s in _sesiones() if s.get("app") == app and hmac.compare_digest(s["h"], h)), None)
    if s is None:
        return None
    c = _cuenta(s["cuenta"])
    if c is None:
        return None
    d = _publica(c)
    d["desde"] = s["desde"]
    return d


def cerrar_sesion(token: str | None) -> None:
    if not token:
        return
    h = _token_hash(token)
    _escribir("sesiones.json", [s for s in _sesiones() if s["h"] != h])


def cerrar_todas(cid: str) -> None:
    _escribir("sesiones.json", [s for s in _sesiones() if s["cuenta"] != cid])

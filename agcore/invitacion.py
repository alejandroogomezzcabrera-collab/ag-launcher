"""invitacion.py — el código de invitación con el que un amigo instala las apps privadas.

Alejandro genera el código en su Mac (`python3 agc.py invitar "Nombre"`): es un JSON en base64url
  {"v": 1, "amigo": "Nombre", "codigo": <token de solo lectura sobre bot_lab>,
   "buzon": <token de lectura/escritura sobre bot_lab-buzon>, "creada": "2026-09-07T…"}
El amigo lo pega en el launcher, que lo guarda en carpeta_datos()/invitacion.json (permisos 600).
Con él, el launcher clona los repositorios privados con la URL https://x-access-token:<token>@github.com/…
y escribe el buzon.json de Bot Lab. Los tokens NUNCA salen de esa carpeta ni aparecen en registros:
enmascarar() tapa cualquier x-access-token:…@ y los propios tokens de la invitación.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
from datetime import datetime
from pathlib import Path

from . import carpeta_datos

FICHERO = "invitacion.json"
MAX_CODIGO = 4000


class ErrorInvitacion(ValueError):
    pass


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _unb64(texto: str) -> bytes:
    texto = re.sub(r"\s+", "", texto)
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _token_ok(t) -> bool:
    return isinstance(t, str) and 8 <= len(t) <= 400 and re.fullmatch(r"[A-Za-z0-9_\-.]+", t) is not None


def generar(amigo: str, token_codigo: str, token_buzon: str) -> str:
    amigo = re.sub(r"\s+", " ", str(amigo or "")).strip()
    if not (1 <= len(amigo) <= 60):
        raise ErrorInvitacion("el nombre del amigo: entre 1 y 60 caracteres")
    if not _token_ok(token_codigo) or not _token_ok(token_buzon):
        raise ErrorInvitacion("los tokens no tienen pinta de tokens de GitHub")
    inv = {"v": 1, "amigo": amigo, "codigo": token_codigo.strip(), "buzon": token_buzon.strip(),
           "creada": datetime.now().isoformat(timespec="seconds")}
    return _b64(json.dumps(inv, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def validar(codigo: str) -> dict:
    """La invitación que hay dentro del código, o ErrorInvitacion."""
    if not isinstance(codigo, str) or not codigo.strip():
        raise ErrorInvitacion("pega el código de invitación")
    if len(codigo) > MAX_CODIGO:
        raise ErrorInvitacion("eso no es un código de invitación (demasiado largo)")
    try:
        inv = json.loads(_unb64(codigo.strip()).decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise ErrorInvitacion("el código no es válido: cópialo entero, tal cual te lo pasó Alejandro")
    if not isinstance(inv, dict) or inv.get("v") != 1:
        raise ErrorInvitacion("el código no es de esta versión del launcher")
    if not isinstance(inv.get("amigo"), str) or not inv["amigo"].strip():
        raise ErrorInvitacion("el código no lleva nombre de amigo")
    if not _token_ok(inv.get("codigo")) or not _token_ok(inv.get("buzon")):
        raise ErrorInvitacion("el código no lleva los tokens de acceso")
    return {"v": 1, "amigo": inv["amigo"].strip(), "codigo": inv["codigo"], "buzon": inv["buzon"],
            "creada": str(inv.get("creada") or "")}


def _ruta() -> Path:
    return carpeta_datos() / FICHERO


def leer() -> dict | None:
    try:
        inv = json.loads(_ruta().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        return validar(generar_desde(inv))
    except ErrorInvitacion:
        return None


def generar_desde(inv: dict) -> str:
    return _b64(json.dumps(inv, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def guardar(codigo: str) -> dict:
    inv = validar(codigo)
    r = _ruta()
    tmp = r.with_suffix(".tmp")
    tmp.write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, r)
    return inv


def borrar() -> None:
    try:
        _ruta().unlink()
    except OSError:
        pass


def publica(inv: dict | None) -> dict | None:
    """Lo que se puede enseñar: quién y cuándo. Nunca los tokens."""
    if not inv:
        return None
    return {"amigo": inv.get("amigo"), "creada": inv.get("creada")}


def url_con_token(repo: str, token: str) -> str:
    """https://github.com/o/r.git → https://x-access-token:<token>@github.com/o/r.git"""
    return re.sub(r"^https://(?:[^@/]+@)?", f"https://x-access-token:{token}@", repo.strip(), count=1)


def sin_token(url: str) -> str:
    return re.sub(r"^https://[^@/]+@", "https://", str(url or ""), count=1)


def enmascarar(texto: str, tokens: list[str] | None = None) -> str:
    """Tapa las URLs con token y los tokens sueltos en cualquier texto que vaya a un registro."""
    t = re.sub(r"x-access-token:[^@\s]+@", "x-access-token:***@", str(texto))
    t = re.sub(r"(github_pat_|ghp_|gho_|ghu_|ghs_)[A-Za-z0-9_]+", r"\1***", t)
    for tok in tokens or []:
        if tok and len(tok) >= 8:
            t = t.replace(tok, "***")
    return t

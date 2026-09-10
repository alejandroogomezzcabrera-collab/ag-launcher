"""recetas.py — los pasos particulares de cada app al instalarla desde el launcher.

Una receta tiene tres momentos (todos reciben `SO`, el módulo so.py o uno falso en los tests):
  validar(a, datos)                 → mensaje de error o None (antes de empezar nada)
  preparar(a, carpeta, datos, inv, log)   ANTES de crear el entorno: escribe lo que la app necesita
                                    encontrar para no preguntar por consola (.env, buzon.json, flota.json…)
  instalar(a, carpeta, log, SO)     DESPUÉS del entorno: servicios, comprobaciones, primer arranque
  extra_instalada(a, carpeta)       lo que, además de servicios y venv, debe existir para dar la app por instalada

Bot Lab (receta "bot-lab"), tal como la reparte Alejandro:
  .env         ALPACA_API_KEY / ALPACA_SECRET_KEY / ALPACA_BASE_URL (tres líneas ASCII). Con .env presente
               los instaladores de Bot Lab no preguntan nada. Las claves son de PAPER (dinero ficticio)
               y solo se guardan ahí; el launcher no las devuelve ni las registra nunca.
  buzon.json   {"buzon": "https://x-access-token:<token_buzon>@github.com/…/bot_lab-buzon.git"}
  flota.json   {"auto_codigo": true, "compartir": true, "nombre": "Flota de <amigo>", "instalada_por": "launcher"}
               (instalada_por: Bot Lab 3.17 lo usa como evidencia positiva de instalación de amigo; sin él, una
               copia sin la clave del propietario no se restaura ni se castiga)
  logs/ backups/ prodigios/
  mac          zsh instalar_mac.sh (no interactivo con .env): crea com.botlab.pasada (5 min),
               com.botlab.vigilante (60 s) y com.botlab.panel (KeepAlive) y abre el navegador.
  windows      windows/instalar.ps1 NO es headless (Read-Host): se reproducen sus pasos: venv, pip, .env,
               conexion.py, git config core.autocrlf false, 4 tareas (BotLab pasada /MO 5, BotLab vigilante
               /MO 1, BotLab actualizar /MO 10, BotLab panel ONLOGON → Run del registro si no se permite),
               puente_git.py --sincronizar y windows\\panel.bat.
Bot Lab se actualiza SOLA con su puente (puente_git.py, cada 10 min): el launcher nunca hace git pull ahí.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import invitacion

BUZON_BOT_LAB = "https://github.com/alejandroogomezzcabrera-collab/bot_lab-buzon.git"
ALPACA_PAPER = "https://paper-api.alpaca.markets"


def _clave_ok(s) -> bool:
    return isinstance(s, str) and 8 <= len(s) <= 200 and re.fullmatch(r"[A-Za-z0-9_\-./+=]+", s) is not None


# --------------------------------------------------------------------------- bot-lab
def _validar_bot_lab(a: dict, datos: dict, carpeta: Path) -> str | None:
    if (carpeta / ".env").exists():
        return None                                  # ya hay claves: no hacen falta otras
    if not datos.get("acepta_ficticio"):
        return "marca la casilla: son claves de dinero ficticio (paper)"
    if not _clave_ok(datos.get("alpaca_key")) or not _clave_ok(datos.get("alpaca_secret")):
        return "faltan la API Key y la Secret Key PAPER de Alpaca (app.alpaca.markets → Paper Trading → API Keys)"
    return None


def _preparar_bot_lab(a: dict, carpeta: Path, datos: dict, inv: dict | None, log) -> bool:
    carpeta.mkdir(parents=True, exist_ok=True)
    env = carpeta / ".env"
    if not env.exists():
        env.write_text(f"ALPACA_API_KEY={datos['alpaca_key'].strip()}\nALPACA_SECRET_KEY={datos['alpaca_secret'].strip()}\n"
                       f"ALPACA_BASE_URL={ALPACA_PAPER}\n", encoding="ascii")
        try:
            env.chmod(0o600)
        except OSError:
            pass
        log("✓ .env escrito con tus claves PAPER (solo en este ordenador)")
    else:
        log("   (.env ya existía: se conservan tus claves)")
    if inv and inv.get("buzon"):
        (carpeta / "buzon.json").write_text(json.dumps({"buzon": invitacion.url_con_token(BUZON_BOT_LAB, inv["buzon"])}, indent=1) + "\n", encoding="utf-8")
        try:
            (carpeta / "buzon.json").chmod(0o600)
        except OSError:
            pass
        log("✓ buzon.json (el buzón de prodigios de la flota)")
    elif not (carpeta / "buzon.json").exists():
        log("   (sin invitación: sin buzón; la flota no compartirá prodigios)")
    flota = carpeta / "flota.json"
    if not flota.exists():
        nombre = re.sub(r"\s+", " ", str(datos.get("flota") or "")).strip()[:60] or f"Flota de {(inv or {}).get('amigo') or 'amigo'}"
        flota.write_text(json.dumps({"auto_codigo": True, "compartir": True, "nombre": nombre, "instalada_por": "launcher"}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        log(f"✓ flota.json («{nombre}»)")
    for d in ("logs", "backups", "prodigios"):
        (carpeta / d).mkdir(exist_ok=True)
    return True


def _instalar_bot_lab(a: dict, carpeta: Path, log, SO) -> bool:
    from .tienda import _log_cmd
    venv = carpeta / str(a.get("venv") or "venv")
    py = SO.python_de(venv)
    log("▸ probando la conexión con Alpaca (paper)…")
    if not _log_cmd(log, SO.sh(py, "conexion.py", cwd=carpeta, timeout=120, utf8=True), "conectado a Alpaca paper"):
        log("✗ las claves no funcionan: borra .env de la carpeta (o vuelve a generar las claves en Alpaca) e inténtalo otra vez")
        return False
    if SO.git() and (carpeta / ".git").exists():
        SO.sh(SO.git(), "-C", carpeta, "config", "core.autocrlf", "false", timeout=20)
    if SO.ES_MAC:
        inst = carpeta / str(a.get("instalador_mac") or "instalar_mac.sh")
        if not inst.exists():
            log(f"✗ falta {inst.name} en la carpeta de Bot Lab")
            return False
        log(f"▸ ejecutando el instalador de Bot Lab ({inst.name}: servicios launchd y primera sincronización)…")
        return _log_cmd(log, SO.sh("/bin/zsh", inst, cwd=carpeta, timeout=2400, utf8=True), "Bot Lab instalada en launchd (com.botlab.*)")
    if SO.ES_WIN:
        w = carpeta / "windows"
        # Las tareas ejecutan pythonw.exe, no un .bat: pythonw es un programa de INTERFAZ y Windows
        # no le da consola nunca. Con un .bat (aunque vaya envuelto en wscript) basta un descuido
        # para que salte una ventana encima de lo que esté haciendo el usuario, y el vigilante
        # corre CADA MINUTO. windows/tarea.py hace lo mismo que hacían los .bat.
        entrada = w / "tarea.py"
        if not entrada.exists():
            log("✗ falta windows\\tarea.py en la carpeta de Bot Lab")
            return False
        pyw = venv / "Scripts" / "pythonw.exe"
        if not pyw.exists():
            pyw = SO.python_de(venv)
        log("▸ creando las tareas programadas de Bot Lab (sin ventanas de consola)…")
        ok = True
        for label, que, cada, logon in (("BotLab pasada", "pasada", 5, False), ("BotLab vigilante", "vigilante", 1, False),
                                        ("BotLab actualizar", "actualizar", 10, False), ("BotLab panel", "panel", None, True)):
            r = SO.instalar_servicio(label, [pyw, entrada, que], carpeta, cada_minutos=cada, al_iniciar_sesion=logon, keepalive=logon, log=log)
            log(("✓ " if r else "✗ ") + label + (f" (cada {cada} min)" if cada else " (al iniciar sesión)"))
            ok = ok and r
        if not ok:
            return False
        log("▸ primera sincronización con el buzón (puente_git.py --sincronizar)…")
        _log_cmd(log, SO.sh(py, "puente_git.py", "--sincronizar", cwd=carpeta, timeout=900, utf8=True), "puente sincronizado")
        log("▸ arrancando el panel…")
        SO.sh(pyw, entrada, "panel", "--sin-abrir", cwd=carpeta, timeout=120)
        return True
    log("✗ sistema no soportado para Bot Lab")
    return False


def _extra_bot_lab(a: dict, carpeta: Path) -> bool:
    return (carpeta / ".env").exists()


RECETAS = {"bot-lab": {"validar": _validar_bot_lab, "preparar": _preparar_bot_lab, "instalar": _instalar_bot_lab, "extra": _extra_bot_lab}}


# --------------------------------------------------------------------------- interfaz
def de(a: dict) -> dict | None:
    r = a.get("receta")
    return RECETAS.get(str(r)) if r else None


def validar(a: dict, datos: dict, carpeta: Path) -> str | None:
    r = de(a)
    return r["validar"](a, datos or {}, carpeta) if r else None


def preparar(a: dict, carpeta: Path, datos: dict, inv: dict | None, log) -> bool:
    r = de(a)
    return r["preparar"](a, carpeta, datos or {}, inv, log) if r else True


def instalar(a: dict, carpeta: Path, log, SO) -> bool | None:
    """True/False si la receta se ocupa de los servicios; None si la app no tiene receta."""
    r = de(a)
    return r["instalar"](a, carpeta, log, SO) if r else None


def extra_instalada(a: dict, carpeta: Path) -> bool:
    r = de(a)
    return r["extra"](a, carpeta) if r else True

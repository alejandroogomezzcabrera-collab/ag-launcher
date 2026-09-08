"""remoto.py — abrir el panel de una app a OTROS dispositivos de confianza (tu iPad, tu móvil).

Por defecto todos los paneles escuchan solo en 127.0.0.1: nadie fuera del ordenador los ve. Este
módulo permite abrirlos, de forma explícita y reversible, a una única dirección:

  acceso_remoto.json (en la carpeta de la app, nunca en git)
    {"activo": true, "modo": "tailscale"|"lan", "host": "0.0.0.0", "hosts": ["100.x.y.z:8484"]}

  - «tailscale»: la app solo responde a peticiones dirigidas a tu IP de Tailscale (una VPN privada
    y gratuita entre tus dispositivos). Es lo recomendado: funciona desde cualquier sitio y nadie
    más de la red puede ni ver el panel.
  - «lan»: responde a tu IP en la red de casa. Vale para el sofá, pero cualquiera conectado a esa
    wifi puede llegar a la pantalla de acceso (y necesitaría tu contraseña para entrar).

La sesión, la contraseña, la cabecera anti-CSRF y el resto de barreras siguen igual: esto solo
cambia POR QUÉ DIRECCIÓN se puede llegar, nunca quién puede entrar.
"""
from __future__ import annotations

import ipaddress
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path

FICHERO = "acceso_remoto.json"


def _leer(base: Path) -> dict:
    try:
        d = json.loads((Path(base) / FICHERO).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir(base: Path, d: dict) -> None:
    f = Path(base) / FICHERO
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass


def _valida(ip: str) -> str | None:
    try:
        return str(ipaddress.ip_address(ip.strip()))
    except ValueError:
        return None


def ip_tailscale() -> str | None:
    """La IP 100.x.y.z de este ordenador en tu red privada de Tailscale, si está instalada."""
    for exe in (shutil.which("tailscale"), "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
                r"C:\Program Files\Tailscale\tailscale.exe"):
        if not exe or not Path(exe).exists():
            continue
        try:
            r = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=10)
        except OSError:
            continue
        ip = _valida((r.stdout or "").splitlines()[0]) if r.returncode == 0 and r.stdout.strip() else None
        if ip:
            return ip
    return None


def ip_lan() -> str | None:
    """La IP de este ordenador en la red de casa (la que ve el router)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))          # dirección de documentación: no envía nada
        return _valida(s.getsockname()[0])
    except OSError:
        return None
    finally:
        s.close()


def direcciones() -> dict:
    return {"tailscale": ip_tailscale(), "lan": ip_lan(), "equipo": socket.gethostname()}


def estado(base: Path, puerto: int) -> dict:
    c = _leer(base)
    d = direcciones()
    activo = bool(c.get("activo"))
    ip = (c.get("hosts") or [""])[0].split(":")[0] if c.get("hosts") else None
    nombre = c.get("nombre")
    return {"activo": activo, "modo": c.get("modo"), "ip": ip, "puerto": puerto, "nombre": nombre,
            "url": f"http://{nombre or ip}:{puerto}/" if activo and (nombre or ip) else None,
            "url_ip": f"http://{ip}:{puerto}/" if activo and ip else None,
            "tailscale": d["tailscale"], "lan": d["lan"], "equipo": d["equipo"]}


def activar(base: Path, puerto: int, modo: str = "tailscale") -> tuple[bool, str]:
    """Abre el panel a tu iPad. Devuelve (ok, mensaje con la dirección)."""
    if modo not in ("tailscale", "lan"):
        return False, "modo desconocido: tailscale o lan"
    ip = ip_tailscale() if modo == "tailscale" else ip_lan()
    if not ip:
        return False, ("Tailscale no está instalado o no ha arrancado: instálalo (gratis) en el ordenador y en el iPad, "
                       "inicia sesión con la misma cuenta en los dos y vuelve a intentarlo") if modo == "tailscale" \
                      else "no encuentro la dirección de este ordenador en la red"
    hosts = [f"{ip}:{puerto}"]
    nombre = None
    if modo == "lan":
        nombre = socket.gethostname().split(".")[0] + ".local"
        hosts.append(f"{nombre}:{puerto}")
    _escribir(Path(base), {"activo": True, "modo": modo, "host": "0.0.0.0", "hosts": hosts, "nombre": nombre,
                           "nota": "lo escribió la app; para cerrarlo del todo pon activo en false o borra este fichero"})
    if nombre:                       # el nombre del ordenador no cambia aunque el router dé otra IP
        return True, f"http://{nombre}:{puerto}/   (o http://{ip}:{puerto}/ si el nombre no te funciona)"
    return True, f"http://{ip}:{puerto}/"


def desactivar(base: Path) -> tuple[bool, str]:
    _escribir(Path(base), {"activo": False})
    return True, "el panel vuelve a escuchar solo en este ordenador"


# ---------------------------------------------------------------- lo que usa el panel al arrancar
def host_escucha(base: Path, defecto: str = "127.0.0.1") -> str:
    c = _leer(Path(base))
    return str(c.get("host") or "0.0.0.0") if c.get("activo") else defecto


def hosts_permitidos(base: Path) -> set:
    """Cabeceras Host adicionales que se aceptan (además de localhost)."""
    c = _leer(Path(base))
    if not c.get("activo"):
        return set()
    return {str(x).strip().lower() for x in (c.get("hosts") or []) if str(x).strip()}

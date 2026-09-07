"""tienda.py — el motor del AG Launcher: qué está instalado, instalar, actualizar, abrir, quitar.

Una app de AG Creations «instalada» en este Mac tiene tres piezas:
  1. la carpeta del proyecto (catalogo.json → carpeta) con su entorno de Python (.venv o venv);
  2. sus servicios de launchd (catalogo.json → servicios; el panel siempre vivo y, si los hay, las tareas);
  3. la app de escritorio en /Applications/<nombre>.app: el bundle de Electron con Resources/app/{main.js,package.json,icon.png}.

Todo lo que hace deja un registro línea a línea (callback `log`) para enseñarlo en el launcher.
Solo macOS (launchctl, open, bundles). Solo librería estándar.
"""
from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import RAIZ, catalogo, version_de

APLICACIONES = Path("/Applications")
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLANTILLA_ELECTRON = [Path.home() / "accc-projects/paper-trading-bot/app/node_modules/electron/dist/Electron.app",
                      RAIZ / "launcher/app/node_modules/electron/dist/Electron.app"]
UID = os.getuid()
_cache: dict = {"t": 0.0, "estado": None}
_remoto_cache: dict[str, tuple[float, str | None]] = {}


def _sh(*args, cwd=None, timeout=600) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout)


def _vivo(puerto: int | None) -> bool:
    if not puerto:
        return False
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=0.25):
            return True
    except OSError:
        return False


def _version_viva(puerto: int | None) -> str | None:
    if not puerto:
        return None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/ag/version", timeout=0.6) as r:
            return json.loads(r.read()).get("version")
    except Exception:
        return None


def _servicio_cargado(label: str) -> bool:
    return _sh("launchctl", "print", f"gui/{UID}/{label}", timeout=10).returncode == 0


def _venv(carpeta: Path) -> Path | None:
    for v in (".venv", "venv"):
        if (carpeta / v / "bin" / "python").exists():
            return carpeta / v
    return None


def _necesita_venv(carpeta: Path) -> bool:
    return (carpeta / "requirements.txt").exists() or (carpeta / "pyproject.toml").exists()


def _bundle(a: dict) -> Path:
    return APLICACIONES / f"{a.get('app_nombre') or a['nombre']}.app"


def _hash_fichero(f: Path) -> str:
    try:
        return hashlib.sha256(f.read_bytes()).hexdigest()
    except OSError:
        return ""


def _app_desactualizada(a: dict, carpeta: Path) -> bool:
    b = _bundle(a)
    if not b.exists():
        return False
    for n in ("main.js", "package.json", "icon.png"):
        if (carpeta / "app" / n).exists() and _hash_fichero(carpeta / "app" / n) != _hash_fichero(b / "Contents/Resources/app" / n):
            return True
    return False


def _remoto(carpeta: Path) -> str | None:
    r = _sh("git", "-C", carpeta, "remote", "get-url", "origin", timeout=10)
    return r.stdout.strip() or None if r.returncode == 0 else None


def _ultima_etiqueta_remota(carpeta: Path, refrescar: bool) -> str | None:
    """La mayor etiqueta vX.Y.Z de origin (fetch como mucho cada 10 min, salvo que se pida)."""
    k = str(carpeta)
    t, v = _remoto_cache.get(k, (0.0, None))
    if not refrescar and time.time() - t < 600:
        return v
    _sh("git", "-C", carpeta, "fetch", "-q", "--tags", "origin", timeout=60)
    r = _sh("git", "-C", carpeta, "tag", "-l", "v[0-9]*", timeout=10)
    tags = [x for x in r.stdout.split() if re.fullmatch(r"v\d+\.\d+\.\d+", x)]
    v = max(tags, key=lambda x: tuple(int(p) for p in x[1:].split("."))) if tags else None
    _remoto_cache[k] = (time.time(), v)
    return v


def _mayor(a: str | None, b: str | None) -> bool:
    """a > b como versiones."""
    try:
        return tuple(int(p) for p in a.split(".")) > tuple(int(p) for p in b.split("."))
    except (AttributeError, ValueError):
        return False


# ----------------------------------------------------------------- estado
def estado_app(a: dict, refrescar_remoto: bool = False) -> dict:
    carpeta = Path(a["carpeta"]).expanduser()
    existe = carpeta.exists()
    servicios = a.get("servicios") or ([a["launchd"]] if a.get("launchd") else [])
    cargados = {s: _servicio_cargado(s) for s in servicios} if existe else {}
    version = version_de(carpeta) if existe else None
    viva = _version_viva(a.get("puerto")) if existe else None
    remoto = _remoto(carpeta) if existe else None
    etiqueta = _ultima_etiqueta_remota(carpeta, refrescar_remoto) if remoto else None
    bundle = _bundle(a)
    d = {"id": a["id"], "nombre": a["nombre"], "icono": a.get("icono", "🧩"), "descripcion": a.get("descripcion", ""),
         "carpeta": str(carpeta).replace(str(Path.home()), "~"), "existe": existe, "version": version, "puerto": a.get("puerto"),
         "vivo": _vivo(a.get("puerto")) if existe else False, "version_viva": viva,
         "venv": (bool(_venv(carpeta)) or not _necesita_venv(carpeta)) if existe else False, "servicios": cargados,
         "app": bundle.exists(), "app_ruta": str(bundle), "app_desactualizada": _app_desactualizada(a, carpeta) if existe else False,
         "remoto": remoto, "etiqueta_remota": etiqueta, "instalador": a.get("instalador"), "propia": a.get("id") == "ag-launcher"}
    d["instalada"] = existe and d["venv"] and all(cargados.values()) and bool(cargados) and d["app"]
    d["actualizacion"] = (etiqueta and version and _mayor(etiqueta[1:], version) and f"{etiqueta} en GitHub") \
        or (viva and version and viva != version and f"panel en v{viva}, carpeta en v{version}: reinicia") \
        or (d["app_desactualizada"] and "la app de escritorio no es la última") or None
    return d


def estado(refrescar_remoto: bool = False) -> list[dict]:
    if not refrescar_remoto and _cache["estado"] and time.time() - _cache["t"] < 4:
        return _cache["estado"]
    e = [estado_app(a, refrescar_remoto) for a in catalogo()]
    _cache.update(t=time.time(), estado=e)
    return e


def invalidar() -> None:
    _cache["t"] = 0.0


# ----------------------------------------------------------------- piezas
def _log_cmd(log, r: subprocess.CompletedProcess, ok="hecho") -> bool:
    salida = (r.stdout + r.stderr).strip()
    for l in salida.splitlines()[-12:]:
        log("   " + l)
    log(("✓ " + ok) if r.returncode == 0 else f"✗ falló (código {r.returncode})")
    return r.returncode == 0


def preparar_entorno(a: dict, log) -> bool:
    carpeta = Path(a["carpeta"]).expanduser()
    v = _venv(carpeta)
    if v is None and not _necesita_venv(carpeta):
        log("   (solo librería estándar: sin entorno que preparar)")
        return True
    if v is None:
        log("▸ creando el entorno de Python (.venv)…")
        if not _log_cmd(log, _sh(sys.executable if "venv" not in sys.executable else "python3", "-m", "venv", carpeta / ".venv", cwd=carpeta), "entorno creado"):
            return False
        v = carpeta / ".venv"
    pip = v / "bin" / "pip"
    if (carpeta / "requirements.txt").exists():
        log("▸ instalando dependencias (requirements.txt)…")
        return _log_cmd(log, _sh(pip, "install", "-q", "-r", "requirements.txt", cwd=carpeta, timeout=1800), "dependencias al día")
    if (carpeta / "pyproject.toml").exists():
        log("▸ instalando dependencias (pyproject.toml)…")
        return _log_cmd(log, _sh(pip, "install", "-q", "-e", ".", cwd=carpeta, timeout=1800), "dependencias al día")
    log("   (sin dependencias que instalar)")
    return True


def instalar_servicios(a: dict, log) -> bool:
    """El instalador propio de la app si lo tiene; si no, sus plists de launchd/."""
    carpeta = Path(a["carpeta"]).expanduser()
    inst = a.get("instalador")
    if inst and (carpeta / inst).exists():
        log(f"▸ ejecutando el instalador de la app ({inst})…")
        r = subprocess.run(["/bin/zsh", str(carpeta / inst)], cwd=str(carpeta), capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL)
        return _log_cmd(log, r, "servicios instalados")
    plists = sorted((carpeta / "launchd").glob("*.plist")) if (carpeta / "launchd").exists() else []
    if not plists:
        log("   (la app no trae servicios de launchd)")
        return True
    ok = True
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    for p in plists:
        label = p.stem
        log(f"▸ servicio {label}…")
        destino = LAUNCH_AGENTS / p.name
        destino.write_text(p.read_text(encoding="utf-8").replace("__CARPETA__", str(carpeta)), encoding="utf-8")
        _sh("launchctl", "bootout", f"gui/{UID}/{label}", timeout=20)
        r = _sh("launchctl", "bootstrap", f"gui/{UID}", destino, timeout=20)
        _sh("launchctl", "enable", f"gui/{UID}/{label}", timeout=20)
        ok = _log_cmd(log, r, f"{label} en marcha") and ok
    return ok


def quitar_servicios(a: dict, log) -> None:
    for s in a.get("servicios") or ([a["launchd"]] if a.get("launchd") else []):
        log(f"▸ parando {s}…")
        _sh("launchctl", "bootout", f"gui/{UID}/{s}", timeout=20)
        p = LAUNCH_AGENTS / f"{s}.plist"
        if p.exists():
            p.unlink()
        log(f"✓ {s} parado y retirado")


def reiniciar_panel(a: dict, log) -> bool:
    label = a.get("launchd")
    if not label:
        log("   (sin panel que reiniciar)")
        return True
    log(f"▸ reiniciando {label}…")
    r = _sh("launchctl", "kickstart", "-k", f"gui/{UID}/{label}", timeout=20)
    if r.returncode:
        return _log_cmd(log, r, "")
    for _ in range(30):
        time.sleep(0.3)
        if _vivo(a.get("puerto")):
            log(f"✓ panel vivo en http://localhost:{a.get('puerto')}")
            return True
    log("✗ el panel no responde tras reiniciar (mira logs/ en su carpeta)")
    return False


def construir_app(a: dict, log) -> bool:
    """/Applications/<nombre>.app = bundle de Electron + app/{main.js,package.json,icon.png} + icono + nombre."""
    carpeta = Path(a["carpeta"]).expanduser()
    origen = carpeta / "app"
    if not (origen / "main.js").exists():
        log("   (la app no trae app/main.js: sin app de escritorio)")
        return True
    plantilla = next((p for p in PLANTILLA_ELECTRON if p.exists()), None)
    if plantilla is None:
        log("✗ no encuentro un Electron.app de plantilla (npm install electron en launcher/app)")
        return False
    bundle = _bundle(a)
    nombre = a.get("app_nombre") or a["nombre"]
    log(f"▸ construyendo {bundle.name} a partir de {plantilla}…")
    tmp = bundle.with_name(bundle.name + ".nuevo")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(plantilla, tmp, symlinks=True)
    destino = tmp / "Contents" / "Resources" / "app"
    destino.mkdir(exist_ok=True)
    for n in ("main.js", "package.json", "icon.png", "preload.js"):
        if (origen / n).exists():
            shutil.copy2(origen / n, destino / n)
    if (origen / "icon.icns").exists():
        shutil.copy2(origen / "icon.icns", tmp / "Contents" / "Resources" / "electron.icns")
    info = tmp / "Contents" / "Info.plist"
    with info.open("rb") as fh:
        pl = plistlib.load(fh)
    pl["CFBundleDisplayName"] = pl["CFBundleName"] = nombre
    pl["CFBundleIdentifier"] = a.get("bundle_id") or "com.ag." + re.sub(r"[^a-z0-9]", "", a["id"].lower())
    pl["CFBundleShortVersionString"] = version_de(carpeta) or "0.0.0"
    with info.open("wb") as fh:
        plistlib.dump(pl, fh)
    if bundle.exists():
        shutil.rmtree(bundle)
    os.rename(tmp, bundle)
    _sh("xattr", "-cr", bundle, timeout=60)
    _sh("touch", bundle, timeout=10)                    # que Finder refresque el icono
    log(f"✓ {bundle}")
    return True


def quitar_app(a: dict, log) -> None:
    b = _bundle(a)
    if b.exists():
        shutil.rmtree(b)
        log(f"✓ {b.name} eliminada de Aplicaciones")


# ----------------------------------------------------------------- acciones
def instalar(a: dict, log) -> bool:
    carpeta = Path(a["carpeta"]).expanduser()
    log(f"{a.get('icono', '')} Instalando {a['nombre']} en {carpeta}")
    if not carpeta.exists():
        if a.get("repo"):
            log(f"▸ clonando {a['repo']}…")
            if not _log_cmd(log, _sh("git", "clone", "-q", a["repo"], carpeta, timeout=1800), "código descargado"):
                return False
        else:
            log("✗ no está la carpeta del proyecto y el catálogo no tiene repositorio del que clonarla")
            return False
    ok = preparar_entorno(a, log) and instalar_servicios(a, log) and construir_app(a, log)
    invalidar()
    log("✓ INSTALADA" if ok else "✗ la instalación no terminó bien: mira el registro")
    return ok


def actualizar(a: dict, log) -> bool:
    carpeta = Path(a["carpeta"]).expanduser()
    log(f"{a.get('icono', '')} Actualizando {a['nombre']}")
    if not carpeta.exists():
        log("✗ no está instalada")
        return False
    antes_req = _hash_fichero(carpeta / "requirements.txt") + _hash_fichero(carpeta / "pyproject.toml")
    if _remoto(carpeta):
        etiqueta = _ultima_etiqueta_remota(carpeta, True)
        log(f"▸ GitHub: última versión publicada {etiqueta or '—'} · aquí v{version_de(carpeta) or '?'}")
        sucio = _sh("git", "-C", carpeta, "status", "--porcelain", "--untracked-files=no", timeout=20).stdout.strip()
        if sucio:
            log("   hay cambios locales sin subir: se conservan (rebase --autostash)")
        r = _sh("git", "-C", carpeta, "pull", "-q", "--rebase", "--autostash", "--tags", "origin", "main", timeout=300)
        if not _log_cmd(log, r, f"código en v{version_de(carpeta) or '?'}"):
            return False
    else:
        log("   (sin repositorio remoto: se aplica la versión de la carpeta)")
    if antes_req != _hash_fichero(carpeta / "requirements.txt") + _hash_fichero(carpeta / "pyproject.toml"):
        if not preparar_entorno(a, log):
            return False
    if a.get("id") == "ag-launcher":
        log("   (el launcher se reinicia solo al terminar)")
        ok = construir_app(a, log)
    else:
        ok = instalar_servicios(a, log) if not all(_servicio_cargado(s) for s in (a.get("servicios") or [])) else reiniciar_panel(a, log)
        ok = construir_app(a, log) and ok
    invalidar()
    log("✓ ACTUALIZADA" if ok else "✗ la actualización no terminó bien")
    return ok


def desinstalar(a: dict, log) -> bool:
    log(f"{a.get('icono', '')} Quitando {a['nombre']} (los servicios y la app de escritorio; la carpeta y tus datos se quedan)")
    quitar_servicios(a, log)
    quitar_app(a, log)
    invalidar()
    log("✓ DESINSTALADA (para volver: Instalar)")
    return True


def abrir(a: dict) -> str:
    b = _bundle(a)
    if b.exists():
        _sh("open", "-a", b, timeout=20)
        return f"abriendo {b.name}"
    if a.get("puerto"):
        _sh("open", f"http://localhost:{a['puerto']}/", timeout=20)
        return f"abriendo http://localhost:{a['puerto']} en el navegador"
    return "no hay nada que abrir"


def abrir_carpeta(a: dict) -> str:
    _sh("open", Path(a["carpeta"]).expanduser(), timeout=20)
    return "carpeta abierta en Finder"


def registro(a: dict, n: int = 80) -> str:
    carpeta = Path(a["carpeta"]).expanduser() / "logs"
    ficheros = sorted(carpeta.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True) if carpeta.exists() else []
    if not ficheros:
        return "(sin registros)"
    f = ficheros[0]
    try:
        lineas = f.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return "(no pude leer el registro)"
    return f"— {f.name} —\n" + "\n".join(lineas)

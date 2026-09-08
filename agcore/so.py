"""so.py — todo lo que depende del sistema operativo, con la MISMA interfaz en macOS y Windows.

macOS:    servicios = LaunchAgents de launchd (~/Library/LaunchAgents/<label>.plist); acceso = una app en
          /Applications (bundle de Electron si hay plantilla; si no, un .app mínimo que abre la URL).
Windows:  servicios = Tareas programadas (schtasks; las del launcher bajo la carpeta «AG Creations\\»;
          si ONLOGON no está permitido, clave HKCU\\...\\Run); acceso = acceso directo .lnk en el Menú
          Inicio y el Escritorio que abre msedge --app=http://localhost:<puerto> (o chrome, o el navegador).
          Las tareas van sin /RU (usuario actual) y abrirían una consola cada vez que corren: los .bat se
          lanzan a través de windows/oculto.vbs (wscript, ventana 0) y los programas Python con pythonw.exe.
          Lo que lanza cada servicio se apunta en <carpeta>/logs/servicios.json para poder relanzarlo cuando
          «schtasks /Run» no puede (arranque en la clave Run).
          PowerShell: nunca se interpolan rutas ni nombres en un -Command; los datos van por un .ps1 temporal
          con literales pasados por _ps_str() (comilla simple doblada) o solo enteros.

Los nombres de servicio (label) se usan TAL CUAL: en Windows el catálogo ya trae «AG Creations\\com.ag…»
para las tareas del launcher y «BotLab pasada» (raíz) para las de Bot Lab, que las crea con esos nombres
exactos su propio instalador.

Toda salida de subprocess se decodifica con errors="replace" (las consolas de Windows no hablan UTF-8).
tienda.py y recetas.py no llaman nunca a subprocess directamente: pasan por aquí (SO.sh), de modo que
los tests inyectan un «so» falso y no tocan el sistema real.

Sin probar en Windows: escrito sin asunciones, pero solo se ha ejecutado en macOS.
"""
from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import ES_MAC, ES_WIN, RAIZ, EMPRESA

# --------------------------------------------------------------------------- constantes
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
APLICACIONES = [Path("/Applications"), Path.home() / "Applications"]
PLANTILLAS_ELECTRON = [RAIZ / "launcher/app/node_modules/electron/dist/Electron.app",
                       Path.home() / "accc-projects/paper-trading-bot/app/node_modules/electron/dist/Electron.app"]
CLAVE_RUN = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
# Valores de la clave Run que ya usa el instalador propio de una app (Bot Lab: instalar.ps1 y su puente
# registran BotLabPanel); para el resto, AG_<label sin símbolos>.
NOMBRES_RUN = {"BotLab panel": "BotLabPanel"}
OCULTO_VBS = RAIZ / "windows" / "oculto.vbs"
PATH_MAC = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_SUELTO = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | _SIN_VENTANA


# --------------------------------------------------------------------------- procesos
def sh(*args, cwd=None, timeout=600, env: dict | None = None, utf8: bool = False) -> subprocess.CompletedProcess:
    """Ejecuta y captura. Nunca abre una consola en Windows; nunca revienta por la codificación."""
    e = None
    if env or utf8:
        e = dict(os.environ)
        if utf8:
            e.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        if env:
            e.update(env)
    try:
        return subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None, capture_output=True,
                              stdin=subprocess.DEVNULL, timeout=timeout, env=e, creationflags=_SIN_VENTANA,
                              encoding="utf-8" if utf8 else None, errors="replace", text=True)
    except FileNotFoundError as ex:
        return subprocess.CompletedProcess(args, 127, "", f"no encuentro el programa: {ex}")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", f"se agotó el tiempo ({timeout} s)")


def suelto(args: list, cwd=None, env: dict | None = None) -> bool:
    """Arranca un proceso independiente (sin consola, sin esperar) y sigue."""
    e = dict(os.environ, PYTHONUTF8="1")
    if env:
        e.update(env)
    try:
        kw = dict(cwd=str(cwd) if cwd else None, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=e, close_fds=True)
        if ES_WIN:
            subprocess.Popen([str(a) for a in args], creationflags=_SUELTO, **kw)
        else:
            subprocess.Popen([str(a) for a in args], start_new_session=True, **kw)
        return True
    except OSError:
        return False


def vivo(puerto: int | None) -> bool:
    if not puerto:
        return False
    try:
        with socket.create_connection(("127.0.0.1", int(puerto)), timeout=0.25):
            return True
    except OSError:
        return False


def git() -> str | None:
    """La ruta de git, o None. En Windows mira también dónde lo deja el instalador oficial
    (por si se instaló después de arrancar el panel y el PATH del proceso aún no lo tiene)."""
    g = shutil.which("git")
    if g:
        return g
    if ES_WIN:
        for c in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "cmd" / "git.exe",
                  Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Git" / "cmd" / "git.exe"):
            if c.exists():
                return str(c)
    return None


def python_sistema() -> str | None:
    """Un Python 3.11+ con el que crear entornos. En Windows: el lanzador «py -3» o «python»."""
    candidatos = []
    if ES_WIN:
        for prog, extra in (("py", ["-3"]), ("python", []), ("python3", [])):
            if shutil.which(prog):
                candidatos.append([prog, *extra])
    else:
        candidatos.append([sys.executable])
        for prog in ("python3", "python3.13", "python3.12", "python3.11"):
            if shutil.which(prog):
                candidatos.append([prog])
    for c in candidatos:
        r = sh(*c, "-c", "import sys;print(sys.executable if sys.version_info>=(3,11) else '')", timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[-1]
    return None


def python_de(venv: Path) -> Path:
    v = Path(venv)
    return v / "Scripts" / "python.exe" if ES_WIN else v / "bin" / "python"


def pythonw_de(venv: Path) -> Path:
    """El Python sin consola de un venv (Windows); en macOS, el normal."""
    v = Path(venv)
    if ES_WIN:
        pw = v / "Scripts" / "pythonw.exe"
        return pw if pw.exists() else v / "Scripts" / "python.exe"
    return v / "bin" / "python"


def crear_venv(carpeta: Path, nombre: str) -> subprocess.CompletedProcess:
    py = python_sistema()
    if not py:
        return subprocess.CompletedProcess([], 1, "", "no encuentro Python 3.11 o más nuevo" +
                                           (" (instálalo desde python.org marcando «Add python.exe to PATH»)" if ES_WIN else ""))
    return sh(py, "-m", "venv", Path(carpeta) / nombre, cwd=carpeta, timeout=600)


# --------------------------------------------------------------------------- servicios
def _uid() -> int:
    return os.getuid() if hasattr(os, "getuid") else 0


def _nombre_run_generico(label: str) -> str:
    return "AG_" + re.sub(r"[^A-Za-z0-9]", "", label)[:60]


def _nombre_run(label: str) -> str:
    """Nombre del valor en HKCU\\...\\Run: el de la propia app si lo tiene (Bot Lab: BotLabPanel); si no,
    AG_<label solo con letras y números>."""
    return NOMBRES_RUN.get(label) or _nombre_run_generico(label)


def _nombres_run(label: str) -> list[str]:
    """El nombre actual y el histórico (versiones anteriores registraban AG_BotLabpanel): se aceptan los dos."""
    return list(dict.fromkeys([_nombre_run(label), _nombre_run_generico(label)]))


def tarea_existe(label: str) -> bool:
    """Windows: ¿existe la Tarea programada (sin contar la clave Run)?"""
    return ES_WIN and sh("schtasks", "/Query", "/TN", label, timeout=30).returncode == 0


def servicio_cargado(label: str) -> bool:
    if ES_MAC:
        return sh("launchctl", "print", f"gui/{_uid()}/{label}", timeout=10).returncode == 0
    if ES_WIN:
        if tarea_existe(label):
            return True
        return any(sh("reg", "query", CLAVE_RUN, "/v", n, timeout=15).returncode == 0 for n in _nombres_run(label))
    return False


def _wscript() -> str:
    return os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "wscript.exe")


def _tr(programa: list) -> str:
    """El /TR de schtasks. Un .bat va a través de windows/oculto.vbs (wscript, ventana 0): sin /RU la tarea
    abriría una consola cada vez que corre. Lo demás (pythonw.exe, que ya no tiene consola), cada pieza entre comillas."""
    p = [str(x) for x in programa]
    if len(p) == 1 and p[0].lower().endswith((".bat", ".cmd")):
        return f'"{_wscript()}" "{OCULTO_VBS}" "{p[0]}"'
    return " ".join(f'"{x}"' if (" " in x or not x.startswith("-")) else x for x in p)


def _fichero_servicios(carpeta) -> Path:
    return Path(carpeta) / "logs" / "servicios.json"


def _leer_servicios(carpeta) -> dict:
    try:
        d = json.loads(_fichero_servicios(carpeta).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _guardar_programa(label: str, programa: list, carpeta: Path) -> None:
    """Windows: apunta qué lanza cada servicio ({label: {"programa": [...], "cwd": ...}} en <carpeta>/logs/servicios.json)
    para poder relanzarlo cuando «schtasks /Run» no puede (ONLOGON no permitido: el arranque quedó en la clave Run)."""
    d = _leer_servicios(carpeta)
    d[label] = {"programa": [str(x) for x in programa], "cwd": str(carpeta)}
    try:
        f = _fichero_servicios(carpeta)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except OSError:
        pass


def programa_guardado(label: str, carpeta=None) -> dict | None:
    """Lo que instalar_servicio apuntó para ese label ({"programa": [...], "cwd": ...}), mirando en la carpeta
    de la app y en la del launcher; None si no hay nada."""
    for c in ([Path(carpeta)] if carpeta else []) + [RAIZ]:
        p = _leer_servicios(c).get(label)
        if isinstance(p, dict) and isinstance(p.get("programa"), list) and p["programa"]:
            return {"programa": [str(x) for x in p["programa"]], "cwd": str(p.get("cwd") or c)}
    return None


def puede_relanzar(label: str, carpeta=None) -> bool:
    """¿Se podrá volver a arrancar el servicio tras pararlo? mac: está en launchd. Windows: existe la tarea
    o hay programa guardado (la clave Run sola no sirve: no se puede «ejecutar» desde fuera)."""
    if ES_MAC:
        return servicio_cargado(label)
    if ES_WIN:
        return tarea_existe(label) or programa_guardado(label, carpeta) is not None
    return False


def instalar_servicio(label: str, programa: list, carpeta: Path, cada_minutos: int | None = None,
                      al_iniciar_sesion: bool = False, keepalive: bool = False, log=print) -> bool:
    """Crea (o sustituye) el servicio y lo arranca.
    mac: RunAtLoad siempre; StartInterval si cada_minutos; KeepAlive si keepalive.
    win: /SC MINUTE /MO n si cada_minutos; si no, ONLOGON (y se ejecuta ahora); keepalive lo hace el vigilante."""
    carpeta = Path(carpeta)
    (carpeta / "logs").mkdir(parents=True, exist_ok=True)
    if ES_MAC:
        LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
        pl = {"Label": label, "ProgramArguments": [str(x) for x in programa], "WorkingDirectory": str(carpeta),
              "EnvironmentVariables": {"PATH": PATH_MAC, "PYTHONUTF8": "1"}, "RunAtLoad": True,
              "StandardOutPath": str(carpeta / "logs" / "launchd.log"), "StandardErrorPath": str(carpeta / "logs" / "launchd.log")}
        if cada_minutos:
            pl["StartInterval"] = int(cada_minutos) * 60
        if keepalive:
            pl["KeepAlive"] = True
        destino = LAUNCH_AGENTS / f"{label}.plist"
        with destino.open("wb") as fh:
            plistlib.dump(pl, fh)
        sh("launchctl", "bootout", f"gui/{_uid()}/{label}", timeout=20)
        r = sh("launchctl", "bootstrap", f"gui/{_uid()}", destino, timeout=20)
        sh("launchctl", "enable", f"gui/{_uid()}/{label}", timeout=20)
        if r.returncode:
            log(f"✗ launchctl bootstrap {label}: {(r.stderr or r.stdout).strip()[-200:]}")
        return r.returncode == 0
    if ES_WIN:
        tr = _tr(programa)
        if cada_minutos:
            r = sh("schtasks", "/Create", "/F", "/SC", "MINUTE", "/MO", str(int(cada_minutos)), "/TN", label, "/TR", tr, "/RL", "LIMITED", timeout=60)
            if r.returncode:
                log(f"✗ schtasks {label}: {(r.stderr or r.stdout).strip()[-200:]}")
                return False
            _guardar_programa(label, programa, carpeta)
            return True
        r = sh("schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", label, "/TR", tr, "/RL", "LIMITED", timeout=60)
        if r.returncode:
            # Windows puede reservar ONLOGON al administrador: el arranque del usuario actual va al registro.
            log(f"   (schtasks ONLOGON no permitido: se usa la clave Run del registro) {(r.stderr or r.stdout).strip()[-120:]}")
            r = sh("reg", "add", CLAVE_RUN, "/v", _nombre_run(label), "/t", "REG_SZ", "/d", tr, "/f", timeout=15)
            if r.returncode:
                log(f"✗ reg add: {(r.stderr or r.stdout).strip()[-200:]}")
                return False
            _guardar_programa(label, programa, carpeta)      # sin tarea, reiniciar_servicio relanza esto
            suelto(programa, cwd=carpeta)
            return True
        _guardar_programa(label, programa, carpeta)
        sh("schtasks", "/Run", "/TN", label, timeout=30)
        return True
    log("✗ sistema no soportado")
    return False


def quitar_servicio(label: str) -> None:
    if ES_MAC:
        sh("launchctl", "bootout", f"gui/{_uid()}/{label}", timeout=20)
        p = LAUNCH_AGENTS / f"{label}.plist"
        if p.exists():
            p.unlink()
    elif ES_WIN:
        sh("schtasks", "/End", "/TN", label, timeout=30)
        sh("schtasks", "/Delete", "/F", "/TN", label, timeout=30)
        for n in _nombres_run(label):
            sh("reg", "delete", CLAVE_RUN, "/v", n, "/f", timeout=15)


def reiniciar_servicio(label: str, carpeta=None) -> bool:
    """mac: kickstart. Windows: schtasks /Run; si no puede (no hay tarea: el arranque quedó en la clave Run),
    relanza el programa guardado por instalar_servicio, suelto y sin ventana."""
    if ES_MAC:
        return sh("launchctl", "kickstart", "-k", f"gui/{_uid()}/{label}", timeout=20).returncode == 0
    if ES_WIN:
        sh("schtasks", "/End", "/TN", label, timeout=30)
        if sh("schtasks", "/Run", "/TN", label, timeout=30).returncode == 0:
            return True
        p = programa_guardado(label, carpeta)
        return p is not None and suelto(p["programa"], cwd=p["cwd"])
    return False


def matar_puerto(puerto: int) -> None:
    """Mata el proceso que escucha en ese puerto (sea quien sea)."""
    if not puerto:
        return
    if ES_MAC:
        r = sh("lsof", "-ti", f"tcp:{int(puerto)}", "-sTCP:LISTEN", timeout=15)
        for pid in r.stdout.split():
            if pid.isdigit() and int(pid) != os.getpid():
                sh("kill", pid, timeout=5)
    elif ES_WIN:
        # solo se interpolan ENTEROS (puerto y pid): ninguna ruta ni nombre entra en el -Command
        sh("powershell", "-NoProfile", "-Command",
           f"Get-NetTCPConnection -LocalPort {int(puerto)} -State Listen -ErrorAction SilentlyContinue | "
           f"Where-Object {{ $_.OwningProcess -ne {int(os.getpid())} }} | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}",
           timeout=30)


# --------------------------------------------------------------------------- abrir cosas
def abrir(objetivo) -> bool:
    """Una URL, una app o un fichero, con lo que el sistema tenga."""
    o = str(objetivo)
    try:
        if ES_MAC:
            return sh("open", o, timeout=20).returncode == 0
        if ES_WIN:
            os.startfile(o)  # type: ignore[attr-defined]
            return True
        return sh("xdg-open", o, timeout=20).returncode == 0
    except OSError:
        return False


def abrir_carpeta(ruta) -> bool:
    return abrir(ruta)


# --------------------------------------------------------------------------- accesos (app de escritorio)
def _carpeta_aplicaciones() -> Path:
    for c in APLICACIONES:
        if c.exists() and os.access(c, os.W_OK):
            return c
    APLICACIONES[-1].mkdir(parents=True, exist_ok=True)
    return APLICACIONES[-1]


def _nombre_app(app: dict) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "", str(app.get("app_nombre") or app.get("nombre") or app.get("id", "app"))).strip() or "app"


def _menu_inicio() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / EMPRESA


def ruta_acceso(app: dict) -> Path:
    """Dónde está (o estaría) el acceso principal de una app."""
    nombre = _nombre_app(app)
    if ES_WIN:
        return _menu_inicio() / f"{nombre}.lnk"
    for c in APLICACIONES:
        if (c / f"{nombre}.app").exists():
            return c / f"{nombre}.app"
    return APLICACIONES[0] / f"{nombre}.app"


def acceso_existe(app: dict) -> bool:
    return ruta_acceso(app).exists()


def plantilla_electron() -> Path | None:
    return next((p for p in PLANTILLAS_ELECTRON if p.exists()), None)


def _bundle_electron(app: dict, carpeta: Path, origen: Path, plantilla: Path, log) -> Path:
    from . import version_de
    bundle = ruta_acceso(app)
    if not bundle.exists():
        bundle = _carpeta_aplicaciones() / bundle.name
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
    pl["CFBundleDisplayName"] = pl["CFBundleName"] = _nombre_app(app)
    pl["CFBundleIdentifier"] = app.get("bundle_id") or "com.ag." + re.sub(r"[^a-z0-9]", "", str(app["id"]).lower())
    pl["CFBundleShortVersionString"] = version_de(carpeta) or "0.0.0"
    with info.open("wb") as fh:
        plistlib.dump(pl, fh)
    if bundle.exists():
        shutil.rmtree(bundle)
    os.rename(tmp, bundle)
    sh("xattr", "-cr", bundle, timeout=60)
    sh("touch", bundle, timeout=10)                    # que Finder refresque el icono
    return bundle


def _app_minima_mac(app: dict, carpeta: Path, origen: Path, log) -> Path:
    """Un .app de verdad (Finder, Dock, Spotlight) sin Electron: un guion que abre la URL en el navegador."""
    from . import version_de
    nombre = _nombre_app(app)
    bundle = ruta_acceso(app)
    if not bundle.exists():
        bundle = _carpeta_aplicaciones() / bundle.name
    log(f"▸ creando {bundle.name} (abre http://localhost:{app.get('puerto')} en el navegador)…")
    tmp = bundle.with_name(bundle.name + ".nuevo")
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "Contents" / "MacOS").mkdir(parents=True)
    (tmp / "Contents" / "Resources").mkdir(parents=True)
    ejecutable = re.sub(r"[^A-Za-z0-9]", "", nombre) or "app"
    guion = tmp / "Contents" / "MacOS" / ejecutable
    guion.write_text(f"#!/bin/sh\nopen 'http://localhost:{int(app.get('puerto') or 80)}/'\n", encoding="utf-8")
    os.chmod(guion, 0o755)
    pl = {"CFBundleName": nombre, "CFBundleDisplayName": nombre, "CFBundleExecutable": ejecutable,
          "CFBundleIdentifier": app.get("bundle_id") or "com.ag." + re.sub(r"[^a-z0-9]", "", str(app["id"]).lower()),
          "CFBundlePackageType": "APPL", "CFBundleShortVersionString": version_de(carpeta) or "0.0.0", "LSMinimumSystemVersion": "11.0"}
    if (origen / "icon.icns").exists():
        shutil.copy2(origen / "icon.icns", tmp / "Contents" / "Resources" / "icon.icns")
        pl["CFBundleIconFile"] = "icon"
    with (tmp / "Contents" / "Info.plist").open("wb") as fh:
        plistlib.dump(pl, fh)
    if bundle.exists():
        shutil.rmtree(bundle)
    os.rename(tmp, bundle)
    sh("touch", bundle, timeout=10)
    return bundle


def _icono_ico(origen: Path) -> Path | None:
    """app/icon.ico a partir de app/icon.png si Pillow está disponible; si no, sin icono."""
    ico = origen / "icon.ico"
    if ico.exists():
        return ico
    png = origen / "icon.png"
    if not png.exists():
        return None
    try:
        from PIL import Image  # type: ignore
        im = Image.open(png).convert("RGBA")
        im.save(ico, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        return ico
    except Exception:
        return None


def _ps_str(valor: str) -> str:
    """Una cadena literal de PowerShell (comillas simples, con la comilla simple doblada). SIEMPRE que un dato
    (ruta, nombre de app, argumento) entre en un guion de PowerShell pasa por aquí."""
    return "'" + str(valor).replace("'", "''") + "'"


def _navegador_app_windows(puerto: int) -> tuple[str, str]:
    """(programa, argumentos) del acceso: Edge en modo app, si no Chrome, si no el navegador por defecto."""
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    for exe in (Path(pf86) / "Microsoft/Edge/Application/msedge.exe", Path(pf) / "Microsoft/Edge/Application/msedge.exe",
                Path(pf) / "Google/Chrome/Application/chrome.exe", Path(pf86) / "Google/Chrome/Application/chrome.exe",
                Path(local) / "Google/Chrome/Application/chrome.exe" if local else None):
        if exe and exe.exists():
            return str(exe), f"--app=http://localhost:{int(puerto)}/"
    return os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "cmd.exe"), f'/c start "" http://localhost:{int(puerto)}/'


def _lnk_windows(app: dict, carpeta: Path, origen: Path, log) -> bool:
    nombre = _nombre_app(app)
    puerto = int(app.get("puerto") or 80)
    programa, argumentos = _navegador_app_windows(puerto)
    ico = _icono_ico(origen) if origen.exists() else None
    menu = _menu_inicio()
    menu.mkdir(parents=True, exist_ok=True)
    guion = "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$ws = New-Object -ComObject WScript.Shell",
        f"$escritorio = [Environment]::GetFolderPath('Desktop')",
        f"foreach ($ruta in @({_ps_str(str(menu / (nombre + '.lnk')))}, (Join-Path $escritorio {_ps_str(nombre + '.lnk')}))) {{",
        "  $s = $ws.CreateShortcut($ruta)",
        f"  $s.TargetPath = {_ps_str(programa)}",
        f"  $s.Arguments = {_ps_str(argumentos)}",
        f"  $s.WorkingDirectory = {_ps_str(str(carpeta))}",
        f"  $s.Description = {_ps_str(nombre + ' (AG Creations)')}",
        f"  $s.WindowStyle = {7 if programa.lower().endswith('cmd.exe') else 1}",
        f"  if ({_ps_str(str(ico) if ico else '')} -ne '') {{ $s.IconLocation = {_ps_str(str(ico) + ',0' if ico else '')} }}",
        "  $s.Save()",
        "}",
    ])
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig", dir=str(carpeta / "logs") if (carpeta / "logs").exists() else None) as fh:
        fh.write(guion)
        ruta_ps1 = fh.name
    try:
        r = sh("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ruta_ps1, timeout=60)
    finally:
        try:
            os.unlink(ruta_ps1)
        except OSError:
            pass
    if r.returncode:
        log(f"✗ no pude crear el acceso directo: {(r.stderr or r.stdout).strip()[-300:]}")
        return False
    log(f"✓ acceso directo «{nombre}» en el Menú Inicio (AG Creations) y en el Escritorio" + ("" if ico else " (sin icono: falta Pillow)"))
    return True


def construir_acceso(app: dict, carpeta: Path, log=print) -> bool:
    """La «app de escritorio» de una app: bundle en /Applications (mac) o .lnk (Windows)."""
    carpeta = Path(carpeta)
    origen = carpeta / str(app.get("app") or "app")
    if ES_MAC:
        plantilla = plantilla_electron()
        if (origen / "main.js").exists() and plantilla:
            log(f"✓ {_bundle_electron(app, carpeta, origen, plantilla, log)}")
        else:
            if (origen / "main.js").exists():
                log("   (sin Electron.app de plantilla: se crea una app sencilla que abre el navegador)")
            log(f"✓ {_app_minima_mac(app, carpeta, origen, log)}")
        return True
    if ES_WIN:
        return _lnk_windows(app, carpeta, origen, log)
    log("   (sin acceso de escritorio en este sistema)")
    return True


def quitar_acceso(app: dict, log=print) -> None:
    nombre = _nombre_app(app)
    if ES_MAC:
        for c in APLICACIONES:
            b = c / f"{nombre}.app"
            if b.exists():
                shutil.rmtree(b)
                log(f"✓ {b.name} eliminada de Aplicaciones")
    elif ES_WIN:
        r = sh("powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')", timeout=30)
        escritorio = Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else Path.home() / "Desktop"
        for l in (_menu_inicio() / f"{nombre}.lnk", escritorio / f"{nombre}.lnk"):
            if l.exists():
                l.unlink()
                log(f"✓ acceso directo {l.name} quitado de {l.parent.name}")


# --------------------------------------------------------------------------- relanzarme
def relanzarme(label: str | None = None, guion: Path | None = None) -> None:
    """Termina este proceso y hace que vuelva a arrancar con el código nuevo.
    mac con launchd (KeepAlive): basta con salir. Sin launchd (o Windows): se arranca otro proceso
    suelto con el mismo guion (el panel espera a que el puerto quede libre antes de escuchar)."""
    if ES_MAC and label and servicio_cargado(label):
        os._exit(0)
    guion = Path(guion or sys.argv[0]).resolve()
    py = sys.executable
    if ES_WIN and py.lower().endswith("python.exe"):
        pw = Path(py).with_name("pythonw.exe")
        if pw.exists():
            py = str(pw)
    suelto([py, guion], cwd=guion.parent)
    time.sleep(0.5)
    os._exit(0)

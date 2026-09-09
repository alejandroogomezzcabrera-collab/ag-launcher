"""tienda.py — el motor del AG Launcher: qué está instalado, instalar, actualizar, sincronizar, abrir, quitar.

Una app «instalada» en este ordenador tiene tres piezas:
  1. la carpeta (carpeta_de(a)) con su entorno de Python (catálogo → venv: "venv" o ".venv");
  2. sus servicios: launchd (servicios_mac) o Tareas programadas (servicios_windows);
  3. su acceso de escritorio: app en /Applications (mac) o acceso directo (Windows).

Dos modos:
  propietario   existe <RAIZ>/secrets/propietario.key (los ordenadores de Alejandro): se ven todas las apps,
                sus carpetas y servicios reales vienen de catalogo.local.json, y el launcher se actualiza con
                git pull --rebase --autostash (como siempre).
  amigo         solo las apps repartibles (publica: true); las privadas (privado: true) se clonan con el token
                del código de invitación; el launcher solo instala versiones ETIQUETADAS y FIRMADAS por el
                propietario (agcore.firmas), nunca HEAD de main; sin git (Windows) descarga el ZIP de la
                etiqueta desde GitHub y verifica cada fichero contra la firma antes de sustituir nada.

Todo lo que hace deja un registro línea a línea (callback `log`) para enseñarlo en el launcher; el registro
pasa por invitacion.enmascarar: NUNCA aparece un token (x-access-token:***@).
Todo lo que toca el sistema pasa por `SO` (agcore.so), que los tests sustituyen por uno falso.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from . import ES_WIN, RAIZ, carpeta_de, catalogo, version_de
from . import firmas, invitacion, recetas
from . import so as _so

SO = _so                                   # inyectable en los tests
_cache: dict = {"t": 0.0, "estado": None}
_remoto_cache: dict[str, tuple[float, str | None]] = {}
_puente_cache: dict[str, tuple[float, dict | None]] = {}
_versiones_regex = re.compile(r"v\d+\.\d+\.\d+")


# ----------------------------------------------------------------- modo, catálogo visible
def modo() -> str:
    return "propietario" if firmas.ruta_clave(RAIZ).exists() else "amigo"


def es_propietario() -> bool:
    return modo() == "propietario"


def apps_visibles() -> list[dict]:
    """Todas en modo propietario; solo las repartibles (publica) en modo amigo."""
    todas = catalogo()
    return todas if es_propietario() else [a for a in todas if a.get("publica")]


def app(app_id: str) -> dict | None:
    return next((a for a in apps_visibles() if a["id"] == app_id), None)


def _servicios(a: dict) -> list[str]:
    return list(a.get("servicios_windows" if SO.ES_WIN else "servicios_mac") or [])


def _panel(a: dict) -> str | None:
    s = _servicios(a)
    return a.get("panel_windows" if SO.ES_WIN else "panel_mac") or (s[0] if s else None)


def _tokens() -> list[str]:
    inv = invitacion.leer()
    return [inv["codigo"], inv["buzon"]] if inv else []


def _log_seguro(log):
    tokens = _tokens()
    return lambda linea: log(invitacion.enmascarar(str(linea), tokens))


# ----------------------------------------------------------------- piezas de estado
def _version_viva(puerto: int | None) -> str | None:
    """La versión que el PROCESO está ejecutando ahora mismo (no la del disco).

    Una app que lleva días arrancada sigue con el código que cargó: una actualización cambia el
    disco pero no el intérprete. Comparando esto con la versión instalada, la biblioteca puede
    avisar de «instalada 3.21.2, corriendo 3.20.5» en vez de darla por al día. Bot Lab responde en
    /version (no usa agcore); las demás, en /ag/version."""
    if not puerto or not SO.vivo(puerto):
        return None
    for ruta in ("/ag/version", "/version"):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{puerto}{ruta}", timeout=0.6) as r:
                v = json.loads(r.read()).get("version")
            if v:
                return str(v)
        except Exception:
            continue
    return None


def _venv_de(a: dict, carpeta: Path) -> Path | None:
    for v in dict.fromkeys([str(a.get("venv") or ".venv"), ".venv", "venv"]):
        if SO.python_de(carpeta / v).exists():
            return carpeta / v
    return None


def _necesita_venv(carpeta: Path) -> bool:
    return (carpeta / "requirements.txt").exists() or (carpeta / "pyproject.toml").exists()


def _hash_fichero(f: Path) -> str:
    try:
        return hashlib.sha256(f.read_bytes()).hexdigest()
    except OSError:
        return ""


def _app_desactualizada(a: dict, carpeta: Path) -> bool:
    """Solo mac con bundle de Electron: ¿main.js/package.json/icon.png del bundle son los de la carpeta?"""
    if not SO.ES_MAC:
        return False
    b = SO.ruta_acceso(a)
    if not b.exists() or not (b / "Contents/Resources/app").exists():
        return False
    origen = carpeta / str(a.get("app") or "app")
    for n in ("main.js", "package.json", "icon.png"):
        if (origen / n).exists() and _hash_fichero(origen / n) != _hash_fichero(b / "Contents/Resources/app" / n):
            return True
    return False


def _remoto(carpeta: Path) -> str | None:
    g = SO.git()
    if not g or not (carpeta / ".git").exists():
        return None
    r = SO.sh(g, "-C", carpeta, "remote", "get-url", "origin", timeout=10)
    return invitacion.sin_token(r.stdout.strip()) or None if r.returncode == 0 else None


def _mismo_repo(u1: str | None, u2: str | None) -> bool:
    n = lambda u: re.sub(r"\.git$", "", invitacion.sin_token(u or "").strip().rstrip("/").lower())
    return bool(u1 and u2) and n(u1) == n(u2)


def _mayor_etiqueta(tags) -> str | None:
    tags = [t for t in tags if _versiones_regex.fullmatch(t)]
    return max(tags, key=lambda x: tuple(int(p) for p in x[1:].split("."))) if tags else None


def _repo_github(repo: str | None) -> tuple[str, str] | None:
    m = re.match(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", invitacion.sin_token(repo or ""))
    return (m.group(1), m.group(2)) if m else None


def _ultima_etiqueta_remota(a: dict, carpeta: Path, refrescar: bool) -> str | None:
    """La mayor etiqueta vX.Y.Z publicada (fetch --tags con git; la API pública de GitHub sin git).
    Como mucho cada 10 min, salvo que se pida."""
    k = str(carpeta)
    t, v = _remoto_cache.get(k, (0.0, None))
    if not refrescar and time.time() - t < 600:
        return v
    v = None
    g = SO.git()
    if g and (carpeta / ".git").exists():
        SO.sh(g, "-C", carpeta, "fetch", "-q", "--tags", "origin", timeout=60)
        r = SO.sh(g, "-C", carpeta, "tag", "-l", "v[0-9]*", timeout=10)
        v = _mayor_etiqueta(r.stdout.split())
    elif a.get("id") == "ag-launcher" and _repo_github(a.get("repo")) and not a.get("privado"):
        o, rp = _repo_github(a["repo"])
        try:
            with urllib.request.urlopen(f"https://api.github.com/repos/{o}/{rp}/tags?per_page=100", timeout=8) as r:
                v = _mayor_etiqueta([str(x.get("name")) for x in json.loads(r.read()) if isinstance(x, dict)])
        except Exception:
            v = None
    _remoto_cache[k] = (time.time(), v)
    return v


def _mayor(a: str | None, b: str | None) -> bool:
    """a > b como versiones."""
    try:
        return tuple(int(p) for p in a.split(".")) > tuple(int(p) for p in b.split("."))
    except (AttributeError, ValueError):
        return False


def estado_puente(carpeta: Path, refrescar: bool = False) -> dict | None:
    """Lo que el puente de Bot Lab deja en logs/puente.json y flota.json (sin URLs con token)."""
    k = str(carpeta)
    t, v = _puente_cache.get(k, (0.0, None))
    if not refrescar and time.time() - t < 20:
        return v
    d = None
    try:
        p = json.loads((carpeta / "logs" / "puente.json").read_text(encoding="utf-8"))
        d = {k2: p.get(k2) for k2 in ("ultimo", "actualizar", "recibir", "publicar", "instalado", "instalado_en",
                                      "codigo_pendiente", "codigo_error", "buzon_ok", "prodigios_ajenos", "rechazados", "propietario")}
        d["flotas"] = len(p.get("flotas") or [])
    except (OSError, ValueError):
        pass
    try:
        f = json.loads((carpeta / "flota.json").read_text(encoding="utf-8"))
        d = d or {}
        d.update(nombre=f.get("nombre"), auto_codigo=f.get("auto_codigo"), compartir=f.get("compartir"), huella=f.get("huella"),
                 strikes=len(f.get("strikes") or []) if isinstance(f.get("strikes"), list) else f.get("strikes") or 0,
                 alterado=bool(f.get("alterado")), baneada=bool(f.get("baneada")), baneo_motivo=f.get("baneo_motivo"))
    except (OSError, ValueError):
        pass
    if (carpeta / "BANEADO.txt").exists():
        d = d or {}
        d["baneada"] = True
    _puente_cache[k] = (time.time(), d)
    return d


# ----------------------------------------------------------------- estado
def estado_app(a: dict, refrescar_remoto: bool = False) -> dict:
    carpeta = carpeta_de(a)
    existe = carpeta.exists() and (carpeta / "VERSION").exists()
    servicios = _servicios(a)
    cargados = {s: SO.servicio_cargado(s) for s in servicios} if existe else {}
    version = version_de(carpeta) if existe else None
    viva = _version_viva(a.get("puerto")) if existe else None
    remoto = _remoto(carpeta) if existe else None
    con_git = bool(remoto)
    etiqueta = _ultima_etiqueta_remota(a, carpeta, refrescar_remoto) if existe and (con_git or a.get("id") == "ag-launcher") else None
    acceso = SO.ruta_acceso(a)
    venv_ok = (bool(_venv_de(a, carpeta)) or not _necesita_venv(carpeta)) if existe else False
    d = {"id": a["id"], "nombre": a["nombre"], "icono": a.get("icono", "🧩"), "descripcion": a.get("descripcion", ""),
         "carpeta": str(carpeta).replace(str(Path.home()), "~"), "existe": existe, "version": version, "puerto": a.get("puerto"),
         "vivo": SO.vivo(a.get("puerto")) if existe else False, "version_viva": viva, "venv": venv_ok, "servicios": cargados,
         "app": acceso.exists(), "app_ruta": str(acceso), "app_desactualizada": _app_desactualizada(a, carpeta) if existe else False,
         "remoto": remoto, "etiqueta_remota": etiqueta, "propia": a.get("id") == "ag-launcher", "publica": bool(a.get("publica")),
         "privado": bool(a.get("privado")), "puente": bool(a.get("puente")), "receta": a.get("receta"), "requisitos": a.get("requisitos"),
         "repo": invitacion.sin_token(a.get("repo") or "") or None, "extra": recetas.extra_instalada(a, carpeta) if existe else False,
         "puente_estado": estado_puente(carpeta, refrescar_remoto) if existe and a.get("puente") else None}
    d["instalada"] = existe and venv_ok and bool(cargados) and all(cargados.values()) and d["app"] and d["extra"]
    if a.get("puente") and d["puente_estado"]:
        pe = d["puente_estado"]
        d["actualizacion"] = (pe.get("codigo_pendiente") and f"v{pe['codigo_pendiente']} pendiente en el puente") or None
    else:
        d["actualizacion"] = (etiqueta and version and _mayor(etiqueta[1:], version) and f"{etiqueta} en GitHub") \
            or (viva and version and viva != version and f"panel en v{viva}, carpeta en v{version}: reinicia") \
            or (d["app_desactualizada"] and "la app de escritorio no es la última") or None
    return d


def estado(refrescar_remoto: bool = False) -> list[dict]:
    if not refrescar_remoto and _cache["estado"] and time.time() - _cache["t"] < 4:
        return _cache["estado"]
    e = [estado_app(a, refrescar_remoto) for a in apps_visibles()]
    _cache.update(t=time.time(), estado=e)
    return e


def invalidar() -> None:
    _cache["t"] = 0.0
    _puente_cache.clear()


# ----------------------------------------------------------------- piezas de acción
def _log_cmd(log, r, ok="hecho") -> bool:
    salida = ((r.stdout or "") + (r.stderr or "")).strip()
    for l in salida.splitlines()[-12:]:
        log("   " + l)
    log(("✓ " + ok) if r.returncode == 0 else f"✗ falló (código {r.returncode})")
    return r.returncode == 0


def preparar_entorno(a: dict, carpeta: Path, log) -> bool:
    v = _venv_de(a, carpeta)
    if v is None and not _necesita_venv(carpeta):
        log("   (solo librería estándar: sin entorno que preparar)")
        return True
    if v is None:
        nombre = str(a.get("venv") or ".venv")
        log(f"▸ creando el entorno de Python ({nombre})…")
        if not _log_cmd(log, SO.crear_venv(carpeta, nombre), "entorno creado"):
            return False
        v = carpeta / nombre
    py = SO.python_de(v)
    if (carpeta / "requirements.txt").exists():
        log("▸ instalando dependencias (requirements.txt; puede tardar varios minutos)…")
        SO.sh(py, "-m", "pip", "install", "-q", "--upgrade", "pip", cwd=carpeta, timeout=600, utf8=True)
        return _log_cmd(log, SO.sh(py, "-m", "pip", "install", "-q", "-r", "requirements.txt", cwd=carpeta, timeout=2400, utf8=True), "dependencias al día")
    if (carpeta / "pyproject.toml").exists():
        log("▸ instalando dependencias (pyproject.toml)…")
        return _log_cmd(log, SO.sh(py, "-m", "pip", "install", "-q", "-e", ".", cwd=carpeta, timeout=2400, utf8=True), "dependencias al día")
    log("   (sin dependencias que instalar)")
    return True


def instalar_servicios(a: dict, carpeta: Path, log) -> bool:
    """La receta de la app si la tiene; si no, su instalador propio (mac); si no, sus plantillas de launchd/."""
    r = recetas.instalar(a, carpeta, log, SO)
    if r is not None:
        return r
    inst = a.get("instalador_windows" if SO.ES_WIN else "instalador_mac")
    if inst and (carpeta / inst).exists():
        log(f"▸ ejecutando el instalador de la app ({inst})…")
        if SO.ES_WIN:
            return _log_cmd(log, SO.sh("cmd", "/c", carpeta / inst, cwd=carpeta, timeout=2400), "servicios instalados")
        return _log_cmd(log, SO.sh("/bin/zsh", carpeta / inst, cwd=carpeta, timeout=2400), "servicios instalados")
    if SO.ES_MAC and (carpeta / "launchd").exists():
        plantillas = [p for p in sorted((carpeta / "launchd").glob("*.plist")) if "__CARPETA__" in p.read_text(encoding="utf-8", errors="replace")]
        if plantillas:
            ok = True
            SO.LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
            for p in plantillas:
                label = p.stem
                log(f"▸ servicio {label}…")
                destino = SO.LAUNCH_AGENTS / p.name
                destino.write_text(p.read_text(encoding="utf-8").replace("__CARPETA__", str(carpeta)), encoding="utf-8")
                SO.sh("launchctl", "bootout", f"gui/{SO._uid()}/{label}", timeout=20)
                r2 = SO.sh("launchctl", "bootstrap", f"gui/{SO._uid()}", destino, timeout=20)
                SO.sh("launchctl", "enable", f"gui/{SO._uid()}/{label}", timeout=20)
                ok = _log_cmd(log, r2, f"{label} en marcha") and ok
            return ok
    log("   (la app no trae servicios que instalar en este sistema)")
    return True


def quitar_servicios(a: dict, log) -> None:
    for s in _servicios(a):
        log(f"▸ parando {s}…")
        SO.quitar_servicio(s)
        log(f"✓ {s} parado y retirado")


def reiniciar_panel(a: dict, log) -> bool:
    label = _panel(a)
    if not label:
        log("   (sin panel que reiniciar)")
        return True
    carpeta = carpeta_de(a)
    log(f"▸ reiniciando {label}…")
    if SO.ES_WIN:
        # el panel solo se mata si se va a poder relanzar: existe la tarea o hay programa guardado (servicios.json)
        if not SO.puede_relanzar(label, carpeta):
            log(f"✗ no hay tarea programada ni programa guardado para {label}: no se toca el panel (Instalar lo recrea)")
            return False
        if a.get("puerto"):
            SO.matar_puerto(a["puerto"])
    if not SO.reiniciar_servicio(label, carpeta):
        log(f"✗ no pude reiniciar {label}")
        return False
    for _ in range(40):
        time.sleep(0.3)
        if SO.vivo(a.get("puerto")):
            log(f"✓ panel vivo en http://localhost:{a.get('puerto')}")
            return True
    log("✗ el panel no responde tras reiniciar (mira logs/ en su carpeta)")
    return False


# ----------------------------------------------------------------- acciones
def instalar(a: dict, log, datos: dict | None = None) -> bool:
    log = _log_seguro(log)
    datos = datos or {}
    carpeta = carpeta_de(a)
    inv = invitacion.leer()
    log(f"{a.get('icono', '')} Instalando {a['nombre']} en {carpeta}")
    if a.get("id") == "ag-launcher":
        log("   (el launcher ya está: solo se completan sus servicios y su acceso)")
    error = recetas.validar(a, datos, carpeta)
    if error:
        log("✗ " + error)
        return False
    if not (carpeta / "VERSION").exists():
        if not a.get("repo"):
            log("✗ no está la carpeta del proyecto y el catálogo no tiene repositorio del que descargarla")
            return False
        if a.get("privado") and not inv:
            log("✗ esta app es privada: pega antes tu código de invitación (página Invitación)")
            return False
        g = SO.git()
        if not g:
            log("✗ falta git" + (": instálalo con el botón «Instalar Git» (o desde git-scm.com) y repite" if SO.ES_WIN else " (xcode-select --install)"))
            return False
        url = invitacion.url_con_token(a["repo"], inv["codigo"]) if a.get("privado") else a["repo"]
        log(f"▸ descargando {invitacion.sin_token(a['repo'])} (git clone)…")
        carpeta.parent.mkdir(parents=True, exist_ok=True)
        r = SO.sh(g, "clone", "-q", "--depth", "50", "--config", "core.autocrlf=false", url, carpeta, timeout=1800)
        if not _log_cmd(log, r, "código descargado"):
            if a.get("privado"):
                log("   ¿la invitación ha caducado o se ha revocado? Pide otra a Alejandro")
            return False
    if not recetas.preparar(a, carpeta, datos, inv, log):
        return False
    ok = preparar_entorno(a, carpeta, log) and instalar_servicios(a, carpeta, log) and SO.construir_acceso(a, carpeta, log)
    invalidar()
    log("✓ INSTALADA" if ok else "✗ la instalación no terminó bien: mira el registro")
    return ok


def sincronizar(a: dict, log) -> bool:
    """Apps con puente propio (Bot Lab): <venv python> puente_git.py --sincronizar, y luego --estado."""
    log = _log_seguro(log)
    carpeta = carpeta_de(a)
    v = _venv_de(a, carpeta)
    if not a.get("puente") or not (carpeta / "puente_git.py").exists() or v is None:
        log("✗ esta app no tiene puente que sincronizar")
        return False
    py = SO.python_de(v)
    log(f"{a.get('icono', '')} Sincronizando {a['nombre']} con su puente (código firmado, buzón de prodigios, latido)…")
    ok = _log_cmd(log, SO.sh(py, "puente_git.py", "--sincronizar", cwd=carpeta, timeout=1800, utf8=True), "sincronizado")
    r = SO.sh(py, "puente_git.py", "--estado", cwd=carpeta, timeout=120, utf8=True)
    if r.returncode == 0 and r.stdout.strip():
        log("▸ estado del puente:")
        for l in r.stdout.strip().splitlines()[:60]:
            log("   " + l)
    invalidar()
    return ok


def _firma_ok(carpeta: Path, etiqueta: str, log) -> bool:
    if not firmas.disponible():
        log("✗ falta la librería cryptography: no se pueden verificar firmas ni instalar actualizaciones "
            "(instala requirements.txt del launcher en su entorno)")
        return False
    ok, msg = firmas.verificar(etiqueta, firmas.publica_conocida(RAIZ), base=carpeta)
    log(("✓ " if ok else "✗ ") + msg)
    return ok


def _actualizar_launcher(a: dict, carpeta: Path, log) -> bool:
    g = SO.git()
    remoto = _remoto(carpeta) if g else None
    etiqueta = _ultima_etiqueta_remota(a, carpeta, True)
    actual = version_de(carpeta) or "0.0.0"
    log(f"▸ GitHub: última versión publicada {etiqueta or '—'} · aquí v{actual}")
    if not etiqueta:
        log("   (sin etiquetas publicadas o sin conexión: nada que instalar)")
        if es_propietario() and g and remoto:
            return _pull_propietario(carpeta, g, log)
        return True
    if not _mayor(etiqueta[1:], actual):
        log("✓ ya tienes la última versión")
        return True
    if not (g and remoto):
        if not SO.ES_WIN and g is None:
            log("✗ falta git")
            return False
        return _actualizar_launcher_zip(a, carpeta, etiqueta, log)
    if not _mismo_repo(remoto, a.get("repo")):
        log(f"✗ el remoto de esta copia ({remoto}) no es el repositorio del catálogo ({invitacion.sin_token(a.get('repo') or '')}): no se actualiza")
        return False
    if SO.sh(g, "-C", carpeta, "merge-base", "--is-ancestor", etiqueta, "origin/main", timeout=20).returncode:
        log(f"✗ la etiqueta {etiqueta} no está en la rama principal del repositorio: no se instala")
        return False
    if not _firma_ok(carpeta, etiqueta, log):
        return False
    if es_propietario():
        return _pull_propietario(carpeta, g, log)
    log(f"▸ instalando {etiqueta} (se descartan cambios locales en el código)…")
    r = SO.sh(g, "-C", carpeta, "checkout", "-q", "--", ".", timeout=60)
    if r.returncode:
        log(f"✗ no pude descartar los cambios locales (git checkout -- . falló, código {r.returncode}): no se actualiza")
        for l in ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-6:]:
            log("   " + l)
        return False
    return _log_cmd(log, SO.sh(g, "-C", carpeta, "merge", "-q", "--ff-only", etiqueta, timeout=120), f"código en {etiqueta}")


def _pull_propietario(carpeta: Path, g, log) -> bool:
    sucio = SO.sh(g, "-C", carpeta, "status", "--porcelain", "--untracked-files=no", timeout=20).stdout.strip()
    if sucio:
        log("   hay cambios locales sin subir: se conservan (rebase --autostash)")
    r = SO.sh(g, "-C", carpeta, "pull", "-q", "--rebase", "--autostash", "--tags", "origin", "main", timeout=300)
    return _log_cmd(log, r, f"código en v{version_de(carpeta) or '?'}")


def _actualizar_launcher_zip(a: dict, carpeta: Path, etiqueta: str, log) -> bool:
    """Sin git: ZIP público de la etiqueta en GitHub, verificado fichero a fichero contra la firma."""
    if not firmas.disponible():
        log("✗ falta la librería cryptography: no se pueden verificar firmas ni instalar actualizaciones")
        return False
    rg = _repo_github(a.get("repo"))
    if not rg:
        log("✗ el catálogo no tiene un repositorio de GitHub para el launcher")
        return False
    o, rp = rg
    version = etiqueta[1:]
    url = f"https://github.com/{o}/{rp}/archive/refs/tags/{etiqueta}.zip"
    log(f"▸ descargando {url}…")
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            datos = r.read(64 * 1024 * 1024)
    except Exception as e:
        log(f"✗ no pude descargar el ZIP: {e}")
        return False
    tmp = carpeta / "logs" / f"actualizacion-{etiqueta}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            for n in z.namelist():
                if n.startswith("/") or ".." in n.split("/"):
                    log("✗ el ZIP trae rutas raras: se descarta")
                    return False
            z.extractall(tmp)
        raices = [p for p in tmp.iterdir() if p.is_dir()]
        if len(raices) != 1:
            log("✗ el ZIP no tiene la forma esperada")
            return False
        nuevo = raices[0]
        if (version_de(nuevo) or "") != version:
            log(f"✗ el ZIP dice v{version_de(nuevo)} y no v{version}")
            return False
        ok, msg, malos = firmas.verificar_disco(nuevo, version, firmas.publica_conocida(RAIZ))
        log(("✓ " if ok else "✗ ") + msg)
        for m in malos[:10]:
            log("   ≠ " + m)
        if not ok:
            return False
        lista = json.loads((nuevo / firmas.CARPETA / f"v{version}.json").read_text(encoding="utf-8"))["ficheros"]
        log(f"▸ sustituyendo {len(lista)} ficheros…")
        for ruta in sorted(lista):
            destino = carpeta / ruta
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(nuevo / ruta, destino)
        firma_nueva = nuevo / firmas.CARPETA / f"v{version}.json"
        (carpeta / firmas.CARPETA).mkdir(exist_ok=True)
        shutil.copy2(firma_nueva, carpeta / firmas.CARPETA / firma_nueva.name)
        vieja = carpeta / firmas.CARPETA / f"v{version_de(carpeta) or ''}.json"
        try:
            for ruta in json.loads(vieja.read_text(encoding="utf-8")).get("ficheros", {}):
                if ruta not in lista and (carpeta / ruta).exists() and not ruta.startswith(("secrets/", "logs/")):
                    (carpeta / ruta).unlink()
        except (OSError, ValueError):
            pass
        (carpeta / "VERSION").write_text(version + "\n", encoding="utf-8")
        log(f"✓ código en {etiqueta}")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def actualizar(a: dict, log) -> bool:
    log = _log_seguro(log)
    carpeta = carpeta_de(a)
    log(f"{a.get('icono', '')} Actualizando {a['nombre']}")
    if not (carpeta / "VERSION").exists():
        log("✗ no está instalada")
        return False
    if a.get("puente"):
        log("   (esta app se actualiza sola con su puente: se sincroniza ahora)")
        return sincronizar(a, log)
    antes_req = _hash_fichero(carpeta / "requirements.txt") + _hash_fichero(carpeta / "pyproject.toml")
    if a.get("id") == "ag-launcher":
        if not _actualizar_launcher(a, carpeta, log):
            invalidar()
            return False
    elif es_propietario() and _remoto(carpeta):
        etiqueta = _ultima_etiqueta_remota(a, carpeta, True)
        log(f"▸ GitHub: última versión publicada {etiqueta or '—'} · aquí v{version_de(carpeta) or '?'}")
        if not _pull_propietario(carpeta, SO.git(), log):
            return False
    else:
        log("   (sin repositorio remoto: se aplica la versión de la carpeta)")
    if antes_req != _hash_fichero(carpeta / "requirements.txt") + _hash_fichero(carpeta / "pyproject.toml"):
        if not preparar_entorno(a, carpeta, log):
            return False
    if a.get("id") == "ag-launcher":
        ok = SO.construir_acceso(a, carpeta, log)
        log("   (el launcher se reinicia solo al terminar)")
    else:
        ok = instalar_servicios(a, carpeta, log) if not all(SO.servicio_cargado(s) for s in _servicios(a)) else reiniciar_panel(a, log)
        ok = SO.construir_acceso(a, carpeta, log) and ok
    invalidar()
    log("✓ ACTUALIZADA" if ok else "✗ la actualización no terminó bien")
    return ok


def desinstalar(a: dict, log) -> bool:
    log = _log_seguro(log)
    log(f"{a.get('icono', '')} Quitando {a['nombre']} (los servicios y el acceso de escritorio; la carpeta y tus datos se quedan)")
    quitar_servicios(a, log)
    SO.quitar_acceso(a, log)
    invalidar()
    log("✓ DESINSTALADA (para volver: Instalar)")
    return True


def instalar_git(log) -> bool:
    """Windows: git con winget (el instalador oficial, todo por defecto)."""
    log = _log_seguro(log)
    if SO.git():
        log("✓ git ya está instalado")
        return True
    if not SO.ES_WIN:
        log("✗ en el Mac: xcode-select --install (o brew install git)")
        return False
    log("▸ winget install --id Git.Git -e --source winget (puede pedir confirmación en una ventana de Windows)…")
    r = SO.sh("winget", "install", "--id", "Git.Git", "-e", "--source", "winget", "--accept-package-agreements", "--accept-source-agreements", timeout=1800)
    ok = _log_cmd(log, r, "git instalado")
    if ok and not SO.git():
        log("   git está instalado pero este panel aún no lo ve: pulsa «Relanzar el launcher»")
    if not ok:
        log("   si winget no está disponible: descarga Git desde https://git-scm.com/download/win (todo por defecto)")
    return ok


def abrir(a: dict) -> str:
    acceso = SO.ruta_acceso(a)
    if acceso.exists():
        SO.abrir(acceso)
        return f"abriendo {acceso.name}"
    if a.get("puerto"):
        SO.abrir(f"http://localhost:{a['puerto']}/")
        return f"abriendo http://localhost:{a['puerto']} en el navegador"
    return "no hay nada que abrir"


def abrir_carpeta(a: dict) -> str:
    c = carpeta_de(a)
    if not c.exists():
        return "la carpeta aún no existe"
    SO.abrir_carpeta(c)
    return "carpeta abierta"


def registro(a: dict, n: int = 80) -> str:
    carpeta = carpeta_de(a) / "logs"
    ficheros = sorted(carpeta.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True) if carpeta.exists() else []
    if not ficheros:
        return "(sin registros)"
    f = ficheros[0]
    try:
        lineas = f.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return "(no pude leer el registro)"
    return invitacion.enmascarar(f"— {f.name} —\n" + "\n".join(lineas), _tokens())

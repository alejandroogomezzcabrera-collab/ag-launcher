"""agcore — el núcleo común de las apps de AG Creations.

Lo comparten todas las apps de Alejandro (Shorts Factory, LLM Lab, Second Brain AI…) y el AG Launcher
que se reparte a los amigos:
  cuentas.py     una cuenta por dispositivo, compartida por todas las apps; nunca sale del ordenador
  acceso.py      la Guardia: cabeceras de seguridad, comprobación de Host/Origin, sesión por cookie,
                 rutas /ag/* (acceso, términos, versión, catálogo)
  so.py          lo que depende del sistema (launchd / Tareas programadas, accesos directos, venv…)
  tienda.py      el motor del launcher: estado, instalar, actualizar, sincronizar, quitar
  firmas.py      firma Ed25519 del propietario sobre cada versión publicada
  invitacion.py  el código de invitación con el que un amigo instala las apps privadas
  recetas.py     los pasos particulares de cada app (Bot Lab: .env, buzon.json, flota.json, tareas)
  web/           la pantalla de acceso y el chip de cuenta que se inyectan en cada app

Solo librería estándar (cryptography es opcional y solo hace falta para instalar actualizaciones firmadas).
Portable a macOS y Windows.

El catálogo tiene dos capas:
  catalogo.json         PÚBLICO, viaja en el repositorio: id, nombre, icono, puerto, descripción, repo…
                        Sin rutas de nadie. Las apps privadas de Alejandro llevan "publica": false.
  catalogo.local.json   PRIVADO, gitignorado: por id, la carpeta y los servicios reales de este ordenador
                        (en el Mac de Alejandro: sus proyectos con sus rutas de siempre).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

EMPRESA = "AG Creations"
ES_WIN = os.name == "nt"
ES_MAC = sys.platform == "darwin"
RAIZ = Path(os.environ.get("AG_CREATIONS") or Path(__file__).resolve().parent.parent)   # la carpeta del launcher
VERSION = (RAIZ / "VERSION").read_text().strip() if (RAIZ / "VERSION").exists() else "0.0.0"


def carpeta_datos() -> Path:
    """Dónde viven las cuentas del dispositivo y la invitación (compartidas por todas las apps)."""
    if os.environ.get("AG_DATOS"):
        p = Path(os.environ["AG_DATOS"])
    elif ES_MAC:
        p = Path.home() / "Library" / "Application Support" / EMPRESA
    elif ES_WIN:
        p = Path(os.environ.get("APPDATA", Path.home())) / EMPRESA
    else:
        p = Path.home() / ".ag-creations"
    p.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p, 0o700)
    except OSError:
        pass
    return p


def raiz_apps() -> Path:
    """Dónde se instalan las apps que no tienen carpeta propia en catalogo.local.json."""
    if os.environ.get("AG_APPS"):
        return Path(os.environ["AG_APPS"])
    if ES_WIN:
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / EMPRESA / "apps"
    return Path.home() / EMPRESA


RAIZ_APPS = raiz_apps()


def carpeta_de(a: dict) -> Path:
    """La carpeta de una app: la de catalogo.local.json si la hay; si no, RAIZ_APPS/<id> (el launcher: RAIZ)."""
    if a.get("carpeta"):
        return Path(str(a["carpeta"])).expanduser()
    if a.get("id") == "ag-launcher":
        return RAIZ
    return raiz_apps() / str(a.get("id", "app"))


def _leer_json(ruta: Path) -> dict:
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def catalogo() -> list[dict]:
    """Las apps (catalogo.json fusionado por id con catalogo.local.json), con su versión actual
    leída de la carpeta de cada una si existe."""
    publico = _leer_json(RAIZ / "catalogo.json").get("apps")
    if not isinstance(publico, list):
        return []
    apps = [dict(a) for a in publico if isinstance(a, dict) and a.get("id")]
    local = _leer_json(RAIZ / "catalogo.local.json").get("apps")
    if isinstance(local, list):
        por_id = {a["id"]: a for a in apps}
        for l in local:
            if not isinstance(l, dict) or not l.get("id"):
                continue
            if l["id"] in por_id:
                por_id[l["id"]].update(l)
            else:
                apps.append(dict(l))
    for a in apps:
        a.setdefault("nombre", a["id"])
        a.setdefault("icono", "🧩")
        a["version"] = version_de(carpeta_de(a)) or a.get("version", "?")
    return apps


def version_de(base: Path) -> str | None:
    f = Path(base) / "VERSION"
    try:
        return f.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def app_del_catalogo(app_id: str) -> dict:
    return next((a for a in catalogo() if a["id"] == app_id), {"id": app_id, "nombre": app_id, "icono": "🧩"})

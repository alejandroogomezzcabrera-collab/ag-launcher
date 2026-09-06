"""agcore — el núcleo común de las apps de AG Creations.

Lo comparten todas las apps de Alejandro (Shorts Factory, LLM Lab, Second Brain AI…):
  cuentas.py   una cuenta por dispositivo, compartida por todas las apps; nunca sale del ordenador
  acceso.py    la Guardia: cabeceras de seguridad, comprobación de Host/Origin, sesión por cookie,
               rutas /ag/* (acceso, términos, versión, catálogo)
  web/         la pantalla de acceso y el chip de cuenta que se inyectan en cada app

Solo librería estándar. Portable a macOS y Windows.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

EMPRESA = "AG Creations"
RAIZ = Path(__file__).resolve().parent.parent          # ~/ag-creations
VERSION = (RAIZ / "VERSION").read_text().strip() if (RAIZ / "VERSION").exists() else "0.0.0"


def carpeta_datos() -> Path:
    """Dónde viven las cuentas del dispositivo (compartidas por todas las apps)."""
    if os.environ.get("AG_DATOS"):
        p = Path(os.environ["AG_DATOS"])
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / EMPRESA
    elif os.name == "nt":
        p = Path(os.environ.get("APPDATA", Path.home())) / EMPRESA
    else:
        p = Path.home() / ".ag-creations"
    p.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p, 0o700)
    except OSError:
        pass
    return p


def catalogo() -> list[dict]:
    """Las apps del imperio (catalogo.json), con su versión actual leída de cada carpeta."""
    try:
        apps = json.loads((RAIZ / "catalogo.json").read_text(encoding="utf-8"))["apps"]
    except (OSError, ValueError, KeyError):
        return []
    for a in apps:
        a["version"] = version_de(Path(a.get("carpeta", "")).expanduser()) or a.get("version", "?")
    return apps


def version_de(base: Path) -> str | None:
    f = Path(base) / "VERSION"
    try:
        return f.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def app_del_catalogo(app_id: str) -> dict:
    return next((a for a in catalogo() if a["id"] == app_id), {"id": app_id, "nombre": app_id, "icono": "🧩"})

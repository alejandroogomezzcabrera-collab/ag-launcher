#!/usr/bin/env python3
"""agc — la consola del imperio AG Creations.

  python3 agc.py versiones                      qué versión tiene cada app, su última etiqueta y si hay cambios sin subir
  python3 agc.py subir <app> patch|minor|major -m "qué cambia"
                                                sube la versión (VERSION + CHANGELOG.md), hace commit y etiqueta vX.Y.Z
  python3 agc.py nuevo <id> --nombre "Mi App" --icono 🎯 --puerto 8888 [--descripcion "..."]
                                                crea una app nueva desde la plantilla (con acceso, seguridad y términos) y la añade al catálogo
  python3 agc.py comprobar                      tests de agcore + revisión de cada app (VERSION, TERMINOS.md con AG Creations, agcore conectado)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
from agcore import catalogo, version_de  # noqa: E402

CAT = RAIZ / "catalogo.json"


def _git(carpeta: Path, *args) -> str:
    r = subprocess.run(["git", "-C", str(carpeta), *args], capture_output=True, text=True)
    return r.stdout.strip()


def _vivo(puerto: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=0.3):
            return True
    except OSError:
        return False


def versiones(_):
    apps = catalogo() + [{"id": "agcore", "nombre": "agcore (núcleo)", "icono": "🧩", "carpeta": str(RAIZ), "version": version_de(RAIZ)}]
    print(f"{'app':<22}{'versión':<10}{'etiqueta':<12}{'estado':<20}panel")
    for a in apps:
        c = Path(a["carpeta"]).expanduser()
        tag = _git(c, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*") or "—"
        sucio = _git(c, "status", "--porcelain")
        estado = "cambios sin subir" if sucio else ("etiqueta al día" if tag == "v" + str(a.get("version")) else "sin etiquetar")
        panel = ("● vivo" if _vivo(a["puerto"]) else "○ parado") if a.get("puerto") else ""
        print(f"{a['icono']} {a['nombre']:<19}{a.get('version') or '?':<10}{tag[:11]:<12}{estado:<20}{panel}")


def subir(ns):
    apps = json.loads(CAT.read_text(encoding="utf-8"))["apps"]
    a = next((x for x in apps if x["id"] == ns.app), None)
    if a is None and ns.app != "agcore":
        sys.exit(f"app desconocida: {ns.app}. Están: {', '.join(x['id'] for x in apps)}, agcore")
    c = RAIZ if ns.app == "agcore" else Path(a["carpeta"]).expanduser()
    v = version_de(c) or "0.0.0"
    M, m, p = (int(x) for x in v.split("."))
    nueva = {"major": f"{M + 1}.0.0", "minor": f"{M}.{m + 1}.0", "patch": f"{M}.{m}.{p + 1}"}[ns.salto]
    (c / "VERSION").write_text(nueva + "\n", encoding="utf-8")
    ch = c / "CHANGELOG.md"
    previo = ch.read_text(encoding="utf-8") if ch.exists() else f"# Cambios de {a['nombre'] if a else 'agcore'}\n\n"
    cabecera, _, resto = previo.partition("\n\n")
    ch.write_text(f"{cabecera}\n\n## {nueva} — {date.today().isoformat()}\n\n- {ns.mensaje}\n\n{resto}", encoding="utf-8")
    if ns.app != "agcore":
        a["version"] = nueva
        CAT.write_text(json.dumps({"empresa": "AG Creations", "propietario": "Alejandro Gómez Cabrera", "apps": apps}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(_git(c, "add", "VERSION", "CHANGELOG.md"))
    if ns.todo:
        _git(c, "add", "-A")
    print(_git(c, "commit", "-m", f"v{nueva}: {ns.mensaje}\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"))
    print(_git(c, "tag", "-a", f"v{nueva}", "-m", ns.mensaje))
    print(f"{ns.app} → v{nueva} (etiqueta v{nueva} en {c})")


def nuevo(ns):
    apps = json.loads(CAT.read_text(encoding="utf-8"))["apps"]
    if not re.fullmatch(r"[a-z][a-z0-9\-]{1,30}", ns.id):
        sys.exit("el id: minúsculas, números y guiones (p. ej. mi-app)")
    if any(x["id"] == ns.id for x in apps):
        sys.exit("ya existe esa app en el catálogo")
    if any(x.get("puerto") == ns.puerto for x in apps):
        sys.exit(f"el puerto {ns.puerto} ya lo usa otra app")
    destino = Path(ns.carpeta or f"~/{ns.id}").expanduser()
    if destino.exists():
        sys.exit(f"ya existe {destino}")
    shutil.copytree(RAIZ / "plantilla", destino)
    sust = {"__ID__": ns.id, "__NOMBRE__": ns.nombre, "__ICONO__": ns.icono, "__PUERTO__": str(ns.puerto),
            "__DESCRIPCION__": ns.descripcion or "", "__FECHA__": date.today().isoformat(), "__CLASE__": re.sub(r"[^A-Za-z0-9]", "", ns.nombre)}
    for f in destino.rglob("*"):
        if f.is_file():
            t = f.read_text(encoding="utf-8")
            for k, v in sust.items():
                t = t.replace(k, v)
            f.write_text(t, encoding="utf-8")
    (destino / "launchd" / f"com.ag.{ns.id}-panel.plist").write_text((destino / "launchd" / "panel.plist").read_text(encoding="utf-8"), encoding="utf-8")
    (destino / "launchd" / "panel.plist").unlink()
    apps.append({"id": ns.id, "nombre": ns.nombre, "icono": ns.icono, "carpeta": str(destino).replace(str(Path.home()), "~"),
                 "puerto": ns.puerto, "descripcion": ns.descripcion or "", "launchd": f"com.ag.{ns.id}-panel"})
    CAT.write_text(json.dumps({"empresa": "AG Creations", "propietario": "Alejandro Gómez Cabrera", "apps": apps}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _git(destino, "init", "-q")
    _git(destino, "add", "-A")
    _git(destino, "commit", "-q", "-m", f"v0.1.0: {ns.nombre}, creada desde la plantilla de AG Creations")
    _git(destino, "tag", "-a", "v0.1.0", "-m", "primera versión")
    print(f"✓ {ns.icono} {ns.nombre} creada en {destino} (puerto {ns.puerto}). Arranca con: python3 {destino}/panel.py")
    print("  Lee su README.md para instalarla en launchd y crear la app de escritorio.")


def comprobar(_):
    # pytest: el python que lo tenga (el del sistema o el venv de cualquier app del catálogo)
    candidatos = [Path(sys.executable)] + [Path(a["carpeta"]).expanduser() / ".venv" / "bin" / "python" for a in catalogo()]
    py = next((str(x) for x in candidatos if x.exists() and subprocess.run([str(x), "-c", "import pytest"], capture_output=True).returncode == 0), None)
    if py is None:
        sys.exit("no encuentro ningún python con pytest (pip install pytest)")
    r = subprocess.run([py, "-m", "pytest", "-q", str(RAIZ / "tests")], capture_output=True, text=True)
    print("agcore: " + (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-300:]))
    ok = r.returncode == 0
    for a in catalogo():
        c = Path(a["carpeta"]).expanduser()
        fallos = []
        if not (c / "VERSION").exists():
            fallos.append("sin VERSION")
        t = c / "TERMINOS.md"
        if not t.exists() or "AG Creations" not in t.read_text(encoding="utf-8"):
            fallos.append("TERMINOS.md sin AG Creations")
        if a.get("cuentas") != "propias" and "agcore" not in (c / "panel.py").read_text(encoding="utf-8", errors="ignore"):
            fallos.append("panel.py sin agcore")
        print(f"{'✓' if not fallos else '✗'} {a['icono']} {a['nombre']} v{a.get('version')}" + (" · " + ", ".join(fallos) if fallos else ""))
        ok = ok and not fallos
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("versiones").set_defaults(fn=versiones)
    s = sp.add_parser("subir"); s.add_argument("app"); s.add_argument("salto", choices=["patch", "minor", "major"]); s.add_argument("-m", "--mensaje", required=True)
    s.add_argument("--todo", action="store_true", help="incluye en el commit todos los cambios de la carpeta"); s.set_defaults(fn=subir)
    n = sp.add_parser("nuevo"); n.add_argument("id"); n.add_argument("--nombre", required=True); n.add_argument("--icono", default="🧩"); n.add_argument("--puerto", type=int, required=True)
    n.add_argument("--descripcion", default=""); n.add_argument("--carpeta", default=""); n.set_defaults(fn=nuevo)
    sp.add_parser("comprobar").set_defaults(fn=comprobar)
    ns = p.parse_args(); ns.fn(ns)

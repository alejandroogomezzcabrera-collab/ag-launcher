#!/usr/bin/env python3
"""agc — la consola del imperio AG Creations (solo para Alejandro; los amigos no la necesitan).

  python3 agc.py versiones                      qué versión tiene cada app, su última etiqueta y si hay cambios sin subir
  python3 agc.py publicar "qué cambia" [--minor|--major]
                                                publica una versión del AG LAUNCHER: comprueba (py_compile, node --check,
                                                pytest), sube VERSION y launcher/VERSION, CHANGELOG.md, commit, FIRMA
                                                (firmas/vX.Y.Z.json + politica.json), etiqueta anotada, push (si hay remoto),
                                                dist/AG-Launcher-vX.Y.Z.zip y, si hay gh y remoto, la Release de GitHub
  python3 agc.py invitar "Nombre"               imprime el código de invitación para un amigo (secrets/token_codigo + token_buzon)
  python3 agc.py subir <app> patch|minor|major -m "qué cambia"
                                                sube la versión de otra app (VERSION + CHANGELOG.md), commit y etiqueta vX.Y.Z
  python3 agc.py nuevo <id> --nombre "Mi App" --icono 🎯 --puerto 8888 [--descripcion "..."]
                                                crea una app nueva desde la plantilla y la añade al catálogo (privada)
  python3 agc.py comprobar                      tests de agcore + revisión de cada app (VERSION, TERMINOS.md con AG Creations, agcore)
"""
from __future__ import annotations

import argparse
import json
import py_compile
import re
import shutil
import socket
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
from agcore import carpeta_de, catalogo, version_de  # noqa: E402

CAT = RAIZ / "catalogo.json"
CAT_LOCAL = RAIZ / "catalogo.local.json"
SECRETS = RAIZ / "secrets"


def _git(carpeta: Path, *args, comprobar=False) -> str:
    r = subprocess.run(["git", "-C", str(carpeta), *args], capture_output=True, text=True)
    if comprobar and r.returncode:
        sys.exit(f"git {' '.join(args)} falló:\n{(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def _vivo(puerto: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=0.3):
            return True
    except OSError:
        return False


def _escribir_catalogo(ruta: Path, datos: dict) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"apps": []}


# ----------------------------------------------------------------- versiones
def versiones(_):
    apps = catalogo()
    print(f"{'app':<22}{'versión':<10}{'etiqueta':<12}{'estado':<20}panel")
    for a in apps:
        c = carpeta_de(a)
        if not c.exists():
            print(f"{a['icono']} {a['nombre']:<19}{'—':<10}{'—':<12}{'sin carpeta':<20}")
            continue
        tag = _git(c, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*") or "—"
        sucio = _git(c, "status", "--porcelain")
        estado = "cambios sin subir" if sucio else ("etiqueta al día" if tag == "v" + str(a.get("version")) else "sin etiquetar")
        panel = ("● vivo" if _vivo(a["puerto"]) else "○ parado") if a.get("puerto") else ""
        print(f"{a['icono']} {a['nombre']:<19}{a.get('version') or '?':<10}{tag[:11]:<12}{estado:<20}{panel}")


# ----------------------------------------------------------------- publicar el launcher
def _siguiente(v: str, salto: str) -> str:
    M, m, p = (int(x) for x in v.split("."))
    return {"major": f"{M + 1}.0.0", "minor": f"{M}.{m + 1}.0", "patch": f"{M}.{m}.{p + 1}"}[salto]


def _changelog(ch: Path, titulo: str, nueva: str, mensaje: str) -> None:
    previo = ch.read_text(encoding="utf-8") if ch.exists() else f"# Cambios de {titulo}\n\n"
    cabecera, _, resto = previo.partition("\n\n")
    ch.write_text(f"{cabecera}\n\n## {nueva} — {date.today().isoformat()}\n\n- {mensaje}\n\n{resto}", encoding="utf-8")


def _comprobaciones() -> None:
    for f in sorted((RAIZ / "agcore").glob("*.py")) + [RAIZ / "launcher" / "panel.py", RAIZ / "launcher" / "launcher_panel.py", RAIZ / "agc.py"]:
        py_compile.compile(str(f), doraise=True)
    print("✓ py_compile")
    if shutil.which("node"):
        for f in (RAIZ / "launcher/panel_web/app.js", RAIZ / "launcher/app/main.js"):
            if subprocess.run(["node", "--check", str(f)], capture_output=True).returncode:
                sys.exit(f"node --check falló en {f}")
        print("✓ node --check")
    py = _python_con("pytest")
    if py is None:
        sys.exit("no encuentro ningún python con pytest (pip install pytest)")
    r = subprocess.run([py, "-m", "pytest", "-q", str(RAIZ / "tests")], capture_output=True, text=True)
    if r.returncode:
        sys.exit("pytest falló:\n" + (r.stdout + r.stderr)[-2000:])
    print("✓ pytest: " + (r.stdout.strip().splitlines() or ["?"])[-1])


def _python_con(modulo: str) -> str | None:
    candidatos = [RAIZ / ".venv" / "bin" / "python", Path(sys.executable)] + [carpeta_de(a) / ".venv" / "bin" / "python" for a in catalogo()]
    return next((str(x) for x in candidatos if x.exists() and subprocess.run([str(x), "-c", f"import {modulo}"], capture_output=True).returncode == 0), None)


CARPETAS_PRIVADAS = {"logs", "secrets", "dist"}
FICHEROS_PRIVADOS = {"catalogo.local.json", "invitacion.json"}


def _privados_en_git() -> list[str]:
    """Rutas versionadas que NUNCA deben viajar en una versión: registros, secretos, ZIPs y el catálogo local."""
    r = subprocess.run(["git", "-C", str(RAIZ), "ls-files", "-z"], capture_output=True, text=True)
    if r.returncode:
        sys.exit("git ls-files falló:\n" + (r.stderr or r.stdout).strip())
    malos = []
    for ruta in filter(None, r.stdout.split("\0")):
        partes = ruta.split("/")
        if CARPETAS_PRIVADAS & set(partes[:-1]) or partes[-1] in FICHEROS_PRIVADOS:
            malos.append(ruta)
    return malos


def _sin_privados_en_git() -> None:
    malos = _privados_en_git()
    if malos:
        sys.exit("NO se publica: hay ficheros privados versionados en git (registros, secretos, dist o catálogo local):\n  "
                 + "\n  ".join(malos) + "\nQuítalos del índice (sin borrarlos del disco) con: git rm --cached <ruta>  y repite.")


def publicar(ns):
    from agcore import firmas
    clave = firmas.ruta_clave(RAIZ)
    if not clave.exists():
        sys.exit(f"falta {clave}: cópiala de tu Bot Lab (misma clave del imperio) y protege secrets/ (está en .gitignore)")
    _sin_privados_en_git()
    if _git(RAIZ, "status", "--porcelain", "--untracked-files=no") and not ns.todo:
        print("hay cambios sin commit: se incluyen todos en el commit de la versión (--todo implícito)")
    _comprobaciones()
    py = _python_con("cryptography")
    if py is None:
        sys.exit("hace falta un python con cryptography para firmar (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)")
    if py != sys.executable:
        # firmar con el intérprete que tiene cryptography
        print(f"(firmando con {py})")
        r = subprocess.run([py, str(RAIZ / "agc.py"), "publicar", ns.mensaje] + (["--minor"] if ns.minor else []) + (["--major"] if ns.major else []) + ["--todo"] + (["--sin-push"] if ns.sin_push else []))
        sys.exit(r.returncode)
    salto = "major" if ns.major else "minor" if ns.minor else "patch"
    nueva = _siguiente(version_de(RAIZ) or "0.0.0", salto)
    (RAIZ / "VERSION").write_text(nueva + "\n", encoding="utf-8")
    (RAIZ / "launcher" / "VERSION").write_text(nueva + "\n", encoding="utf-8")
    _changelog(RAIZ / "CHANGELOG.md", "AG Launcher", nueva, ns.mensaje)
    _changelog(RAIZ / "launcher" / "CHANGELOG.md", "AG Launcher", nueva, ns.mensaje)
    cat = _cargar(CAT)
    for a in cat["apps"]:
        if a["id"] == "ag-launcher":
            a["version"] = nueva
    _escribir_catalogo(CAT, cat)
    firmas.actualizar_politica(clave, RAIZ)
    _git(RAIZ, "add", "-A", comprobar=True)
    _sin_privados_en_git()                      # otra vez tras el add: nada privado entra en el commit de la versión
    _git(RAIZ, "commit", "-q", "-m", f"v{nueva}: {ns.mensaje}\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>", comprobar=True)
    # la firma cubre el árbol del commit anterior + la propia firma va en un commit aparte (como Bot Lab: firmas/ no entra en el manifiesto)
    destino = firmas.escribir_firma(nueva, clave, "HEAD", RAIZ)
    _git(RAIZ, "add", str(destino.relative_to(RAIZ)), comprobar=True)
    _git(RAIZ, "commit", "-q", "-m", f"firma v{nueva}", comprobar=True)
    ok, msg = firmas.verificar("HEAD", firmas.publica_hex(clave), RAIZ)
    if not ok:
        sys.exit("la firma no verifica: " + msg)
    _git(RAIZ, "tag", "-a", f"v{nueva}", "-m", ns.mensaje, comprobar=True)
    print(f"✓ v{nueva} firmada y etiquetada ({msg})")
    remoto = _git(RAIZ, "remote", "get-url", "origin")
    if remoto and not ns.sin_push:
        _git(RAIZ, "push", "-q", "origin", "HEAD", comprobar=True)
        _git(RAIZ, "push", "-q", "--tags", "origin", comprobar=True)
        print(f"✓ push a {remoto}")
    zip_ = _zip(nueva)
    print(f"✓ {zip_}")
    if remoto and shutil.which("gh") and not ns.sin_push:
        notas = f"AG Launcher v{nueva}: {ns.mensaje}\n\nDescarga el ZIP, descomprímelo y sigue LEEME.txt (Windows: windows\\instalar.bat · Mac: AG Launcher.command)."
        r = subprocess.run(["gh", "release", "create", f"v{nueva}", str(zip_), "--title", f"AG Launcher v{nueva}", "--notes", notas], capture_output=True, text=True)
        print(("✓ release en GitHub: " + r.stdout.strip()) if r.returncode == 0 else ("✗ gh release: " + (r.stderr or r.stdout).strip()[-300:]))
    elif not remoto:
        print("(sin remoto: no hay push ni release; cuando publiques el repositorio: git remote add origin … && git push -u origin main --tags)")


def _zip(version: str) -> Path:
    """dist/AG-Launcher-vX.Y.Z.zip = git archive de la etiqueta (ya incluye firmas/), con la carpeta raíz AG-Launcher-vX.Y.Z/."""
    dist = RAIZ / "dist"
    dist.mkdir(exist_ok=True)
    destino = dist / f"AG-Launcher-v{version}.zip"
    r = subprocess.run(["git", "-C", str(RAIZ), "archive", "--format=zip", f"--prefix=AG-Launcher-v{version}/", "-o", str(destino), f"v{version}"], capture_output=True, text=True)
    if r.returncode:
        sys.exit("git archive falló: " + (r.stderr or r.stdout))
    return destino


# ----------------------------------------------------------------- invitar
def invitar(ns):
    from agcore import invitacion
    tc, tb = SECRETS / "token_codigo", SECRETS / "token_buzon"
    if not tc.exists() or not tb.exists():
        sys.exit(f"""faltan {tc.name} y/o {tb.name} en {SECRETS}/ (una línea cada uno). Cómo crearlos (AMIGOS.md §2 de Bot Lab):
  https://github.com/settings/personal-access-tokens/new  (tokens fine-grained, expiración máxima)
  - botlab-codigo: Repository access → Only select repositories → bot_lab;       Permissions → Contents: Read-only  → secrets/token_codigo
  - botlab-buzon:  Repository access → Only select repositories → bot_lab-buzon; Permissions → Contents: Read and write → secrets/token_buzon
  mkdir -p secrets && chmod 700 secrets && printf '%s' 'github_pat_…' > secrets/token_codigo && printf '%s' 'github_pat_…' > secrets/token_buzon && chmod 600 secrets/*""")
    codigo = invitacion.generar(ns.nombre, tc.read_text(encoding="utf-8").strip(), tb.read_text(encoding="utf-8").strip())
    print(f"Código de invitación para {ns.nombre} (pásaselo por un canal privado; lleva sus accesos a los repositorios):\n")
    print(codigo)
    print("\nEn el launcher: página «Invitación» → pegar → Guardar. Para cortar el acceso: revoca los tokens en GitHub y reparte códigos nuevos.")


# ----------------------------------------------------------------- subir (otras apps)
def subir(ns):
    a = next((x for x in catalogo() if x["id"] == ns.app), None)
    if a is None and ns.app != "agcore":
        sys.exit(f"app desconocida: {ns.app}. Están: {', '.join(x['id'] for x in catalogo())}, agcore")
    if ns.app in ("agcore", "ag-launcher"):
        sys.exit("el launcher (y agcore) se publican con: python3 agc.py publicar \"qué cambia\" [--minor]")
    c = carpeta_de(a)
    nueva = _siguiente(version_de(c) or "0.0.0", ns.salto)
    (c / "VERSION").write_text(nueva + "\n", encoding="utf-8")
    _changelog(c / "CHANGELOG.md", a["nombre"], nueva, ns.mensaje)
    cat = _cargar(CAT)
    for x in cat["apps"]:
        if x["id"] == ns.app:
            x["version"] = nueva
    _escribir_catalogo(CAT, cat)
    print(_git(c, "add", "VERSION", "CHANGELOG.md"))
    if ns.todo:
        _git(c, "add", "-A")
    print(_git(c, "commit", "-m", f"v{nueva}: {ns.mensaje}\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"))
    print(_git(c, "tag", "-a", f"v{nueva}", "-m", ns.mensaje))
    print(f"{ns.app} → v{nueva} (etiqueta v{nueva} en {c})")


# ----------------------------------------------------------------- nuevo
def nuevo(ns):
    cat, local = _cargar(CAT), _cargar(CAT_LOCAL)
    apps = cat["apps"]
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
    apps.append({"id": ns.id, "nombre": ns.nombre, "icono": ns.icono, "puerto": ns.puerto, "descripcion": ns.descripcion or "",
                 "publica": False, "servicios_mac": [f"com.ag.{ns.id}-panel"], "panel_mac": f"com.ag.{ns.id}-panel", "venv": ".venv", "app": "app"})
    _escribir_catalogo(CAT, cat)
    local.setdefault("apps", []).append({"id": ns.id, "carpeta": str(destino).replace(str(Path.home()), "~")})
    _escribir_catalogo(CAT_LOCAL, local)
    _git(destino, "init", "-q")
    _git(destino, "add", "-A")
    _git(destino, "commit", "-q", "-m", f"v0.1.0: {ns.nombre}, creada desde la plantilla de AG Creations")
    _git(destino, "tag", "-a", "v0.1.0", "-m", "primera versión")
    print(f"✓ {ns.icono} {ns.nombre} creada en {destino} (puerto {ns.puerto}); catálogo público + carpeta en catalogo.local.json. Arranca con: python3 {destino}/panel.py")


# ----------------------------------------------------------------- comprobar
def ipad(ns):
    """Abre una app de AG Creations a tus otros dispositivos (iPad, móvil). Ver IPAD.md."""
    from agcore import carpeta_de, remoto
    a = next((x for x in catalogo() if x["id"] == ns.app), None)
    if a is None:
        sys.exit(f"app desconocida: {ns.app}")
    base, puerto = carpeta_de(a), a.get("puerto")
    if not puerto:
        sys.exit(f"{a['nombre']} no tiene panel")
    if ns.modo == "estado":
        e = remoto.estado(base, puerto)
        print(f"{a['icono']} {a['nombre']}: acceso desde otros dispositivos {'ABIERTO (' + str(e['modo']) + ')' if e['activo'] else 'cerrado'}")
        if e["url"]:
            print(f"  Dirección: {e['url']}")
            if e.get("url_ip") and e["url_ip"] != e["url"]:
                print(f"  Si esa no va, por IP: {e['url_ip']}")
        print(f"  Tailscale: {e['tailscale'] or 'no instalado'} · Red de casa: {e['lan'] or '—'}")
        return
    ok, msg = remoto.desactivar(base) if ns.modo == "off" else remoto.activar(base, puerto, ns.modo)
    print(("✓ " if ok else "✗ ") + msg)
    if ok and a.get("servicios_mac") or a.get("launchd"):
        from agcore import so
        for label in (a.get("servicios_mac") or [a.get("launchd")]):
            if label:
                so.reiniciar_servicio(label, base)
        print("  panel reiniciado")
    if ok and ns.modo != "off":
        print("  En el iPad: abre esa dirección en Safari → Compartir → «Añadir a pantalla de inicio».")


def comprobar(_):
    py = _python_con("pytest")
    if py is None:
        sys.exit("no encuentro ningún python con pytest (pip install pytest)")
    r = subprocess.run([py, "-m", "pytest", "-q", str(RAIZ / "tests")], capture_output=True, text=True)
    print("agcore: " + (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-300:]))
    ok = r.returncode == 0
    for a in catalogo():
        c = carpeta_de(a)
        fallos = []
        if not c.exists():
            print(f"○ {a['icono']} {a['nombre']} · sin carpeta en este ordenador")
            continue
        if not (c / "VERSION").exists():
            fallos.append("sin VERSION")
        t = c / ("launcher/TERMINOS.md" if a["id"] == "ag-launcher" else "TERMINOS.md")
        if not t.exists() or "AG Creations" not in t.read_text(encoding="utf-8"):
            fallos.append("TERMINOS.md sin AG Creations")
        panel = c / ("launcher/panel.py" if a["id"] == "ag-launcher" else "panel.py")
        if a.get("nucleo") != "propio" and "agcore" not in panel.read_text(encoding="utf-8", errors="ignore"):
            fallos.append("panel.py sin agcore")
        print(f"{'✓' if not fallos else '✗'} {a['icono']} {a['nombre']} v{a.get('version')}" + (" · " + ", ".join(fallos) if fallos else ""))
        ok = ok and not fallos
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("versiones").set_defaults(fn=versiones)
    pb = sp.add_parser("publicar"); pb.add_argument("mensaje"); pb.add_argument("--minor", action="store_true"); pb.add_argument("--major", action="store_true")
    pb.add_argument("--todo", action="store_true", help="(implícito) incluye todos los cambios"); pb.add_argument("--sin-push", action="store_true", help="ni push ni release"); pb.set_defaults(fn=publicar)
    i = sp.add_parser("invitar"); i.add_argument("nombre"); i.set_defaults(fn=invitar)
    s = sp.add_parser("subir"); s.add_argument("app"); s.add_argument("salto", choices=["patch", "minor", "major"]); s.add_argument("-m", "--mensaje", required=True)
    s.add_argument("--todo", action="store_true", help="incluye en el commit todos los cambios de la carpeta"); s.set_defaults(fn=subir)
    n = sp.add_parser("nuevo"); n.add_argument("id"); n.add_argument("--nombre", required=True); n.add_argument("--icono", default="🧩"); n.add_argument("--puerto", type=int, required=True)
    n.add_argument("--descripcion", default=""); n.add_argument("--carpeta", default=""); n.set_defaults(fn=nuevo)
    ip = sp.add_parser("ipad", help="abre (o cierra) una app para verla desde el iPad")
    ip.add_argument("modo", choices=["tailscale", "lan", "off", "estado"])
    ip.add_argument("app", nargs="?", default="ag-launcher")
    ip.set_defaults(fn=ipad)
    sp.add_parser("comprobar").set_defaults(fn=comprobar)
    ns = p.parse_args(); ns.fn(ns)

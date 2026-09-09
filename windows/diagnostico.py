"""diagnostico.py — por qué no abre el AG Launcher (o Bot Lab) en este ordenador.

No cambia nada: mira y escribe `diagnostico.txt` en la carpeta del launcher para poder mandárselo
a Alejandro. Se ejecuta con doble clic en windows\\diagnostico.bat.
No recoge contraseñas, claves de Alpaca ni el código de invitación.
"""
from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "diagnostico.txt"
ES_WIN = os.name == "nt"
APPS = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AG Creations" / "apps" if ES_WIN else \
    Path(os.environ.get("AG_APPS") or (Path.home() / "AG Creations" / "apps"))
lineas: list[str] = []


def di(*x) -> None:
    lineas.append(" ".join(str(i) for i in x))


def corre(*args, tiempo=25) -> str:
    try:
        r = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=tiempo,
                           encoding="utf-8", errors="replace")
        return ((r.stdout or "") + (r.stderr or "")).strip() or "(sin salida)"
    except FileNotFoundError:
        return "(no está en este ordenador)"
    except Exception as e:
        return f"({type(e).__name__}: {e})"


def escucha(puerto: int) -> bool:
    s = socket.socket()
    s.settimeout(0.6)
    try:
        return s.connect_ex(("127.0.0.1", puerto)) == 0
    finally:
        s.close()


def cola(f: Path, n=40) -> str:
    try:
        return "\n".join(f.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]) or "(vacío)"
    except OSError:
        return "(no existe)"


def python_del_entorno(carpeta: Path, nombre: str) -> Path | None:
    p = carpeta / nombre / ("Scripts/python.exe" if ES_WIN else "bin/python")
    return p if p.exists() else None


di("=== DIAGNÓSTICO AG CREATIONS ===")
di("fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
di("sistema:", platform.platform())
di("carpeta del launcher:", RAIZ)
di("versión del launcher:", (RAIZ / "VERSION").read_text(encoding="utf-8").strip() if (RAIZ / "VERSION").exists() else "(falta VERSION)")
di("este python:", sys.version.split()[0], sys.executable)

di("\n--- entorno del launcher ---")
py = python_del_entorno(RAIZ, ".venv")
di(".venv:", py or "NO EXISTE (vuelve a ejecutar windows\\instalar.bat)")
if py:
    di("  versión:", corre(py, "-V"))
    di("  cryptography:", corre(py, "-c", "import cryptography;print(cryptography.__version__)"))
    pw = py.with_name("pythonw.exe")
    di("  pythonw.exe:", "sí" if pw.exists() else "NO (el panel se lanzaría con consola)")

di("\n--- ¿hay algún panel escuchando? ---")
for nombre, puerto in (("AG Launcher", 8282), ("Bot Lab", 8484)):
    di(f"  {nombre} (puerto {puerto}):", "SÍ responde" if escucha(puerto) else "NO responde")

if ES_WIN:
    di("\n--- procesos de python ---")
    di(corre("tasklist", "/FI", "IMAGENAME eq pythonw.exe"))
    di(corre("tasklist", "/FI", "IMAGENAME eq python.exe"))
    di("\n--- tareas programadas ---")
    for tarea in ("AG Creations\\com.ag.launcher-panel", "AG Creations\\com.ag.launcher-vigilante"):
        di(f"  [{tarea}]")
        di(corre("schtasks", "/Query", "/TN", tarea, "/FO", "LIST", "/V"))
    di("  [tareas de Bot Lab]")
    todas = corre("schtasks", "/Query", "/FO", "TABLE")
    di("\n".join(l for l in todas.splitlines() if "BotLab" in l) or "(ninguna)")
    di("\n--- arranque por el registro (si las tareas no estaban permitidas) ---")
    di(corre("reg", "query", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"))

di("\n--- registro del panel del launcher ---")
di(cola(RAIZ / "launcher" / "logs" / "panel.log"))

di("\n--- prueba de arranque (aquí sale el error de verdad) ---")
intento = str(py) if py else sys.executable
di(corre(intento, "-c",
         "import sys;sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2]);"
         "import panel;print('el panel se importa bien: v'+str(panel.version_de(panel.BASE)),'modo',panel.tienda.modo())",
         str(RAIZ), str(RAIZ / "launcher"), tiempo=60))

di("\n--- Bot Lab ---")
bl = APPS / "bot-lab"
if (bl / "VERSION").exists():
    di("  carpeta:", bl)
    di("  versión:", (bl / "VERSION").read_text(encoding="utf-8").strip())
    di("  claves (.env):", "sí" if (bl / ".env").exists() else "NO")
    di("  buzón (buzon.json):", "sí" if (bl / "buzon.json").exists() else "NO")
    di("  entorno:", python_del_entorno(bl, "venv") or "NO EXISTE")
    log = bl / "logs" / "panel.log"
    di("  registro del panel de Bot Lab:")
    di(cola(log, 25))
else:
    di("  no está instalado en", bl)

di("\n=== FIN ===")

texto = "\n".join(lineas) + "\n"
try:
    SALIDA.write_text(texto, encoding="utf-8")
    print(f"Escrito {SALIDA}")
except OSError:
    print(texto)
if ES_WIN:
    try:
        os.startfile(SALIDA)                                          # type: ignore[attr-defined]
    except Exception:
        traceback.print_exc()

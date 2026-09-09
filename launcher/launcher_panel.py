"""launcher_panel.py — punto de entrada del AG Launcher en Windows (y válido en cualquier sistema).

¿Por qué no arrancar panel.py directamente? Porque Bot Lab, al instalarse una versión nueva en Windows,
reinicia su propio panel con puente_git._reiniciar_panel(), que mata CUALQUIER proceso python cuya línea
de comandos contenga «panel.py» (Get-CimInstance Win32_Process … -match 'panel\\.py'). Si el launcher
corriera como «pythonw panel.py», Bot Lab lo mataría cada vez que se actualiza. Con este guion la línea
de comandos del launcher es «pythonw launcher_panel.py» y no coincide.

Las tareas programadas de Windows no tienen «carpeta de inicio»: aquí se fija el directorio de trabajo.

Con pythonw.exe no hay consola NI sys.stderr: un fallo al importar (una dependencia que falta, un fichero
a medias) mataría el proceso sin dejar rastro y el navegador solo diría «localhost rechazó la conexión».
Por eso aquí se abre logs/panel.log ANTES de importar nada y se apunta cualquier error con su traza.
"""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.chdir(BASE)
sys.path.insert(0, str(BASE))
sys.argv[0] = str(BASE / "launcher_panel.py")     # así relanzarme() vuelve a arrancar ESTE guion

REGISTRO = BASE / "logs" / "panel.log"


def _apuntar(que: str) -> None:
    try:
        REGISTRO.parent.mkdir(exist_ok=True)
        with open(REGISTRO, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {que}\n")
    except OSError:
        pass


if __name__ == "__main__":
    try:
        import panel
    except BaseException:
        _apuntar("EL PANEL NO ARRANCA (fallo al importar):\n" + traceback.format_exc()
                 + f"python: {sys.executable}\ncarpeta: {BASE}\n")
        raise
    try:
        panel.main()
    except SystemExit:
        raise
    except BaseException:
        _apuntar("EL PANEL SE HA CAÍDO:\n" + traceback.format_exc())
        raise

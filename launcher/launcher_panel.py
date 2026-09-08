"""launcher_panel.py — punto de entrada del AG Launcher en Windows (y válido en cualquier sistema).

¿Por qué no arrancar panel.py directamente? Porque Bot Lab, al instalarse una versión nueva en Windows,
reinicia su propio panel con puente_git._reiniciar_panel(), que mata CUALQUIER proceso python cuya línea
de comandos contenga «panel.py» (Get-CimInstance Win32_Process … -match 'panel\\.py'). Si el launcher
corriera como «pythonw panel.py», Bot Lab lo mataría cada vez que se actualiza. Con este guion la línea
de comandos del launcher es «pythonw launcher_panel.py» y no coincide.

Las tareas programadas de Windows no tienen «carpeta de inicio»: aquí se fija el directorio de trabajo.
"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.chdir(BASE)
sys.path.insert(0, str(BASE))
sys.argv[0] = str(BASE / "launcher_panel.py")     # así relanzarme() vuelve a arrancar ESTE guion

import panel  # noqa: E402

if __name__ == "__main__":
    panel.main()

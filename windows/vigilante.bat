@echo off
rem Vigilante del AG Launcher: si el panel (puerto 8282) no responde, lo arranca sin consola.
rem Tarea programada "AG Creations\com.ag.launcher-vigilante" (cada minuto), lanzada a traves de windows\oculto.vbs
rem (wscript, ventana 0) para que no aparezca una consola cada minuto. Tambien lo usa "AG Launcher.bat".
rem El panel se lanza como "pythonw launcher_panel.py" (nunca panel.py: Bot Lab mata los python con panel.py).
rem Sin PowerShell y sin rutas dentro de literales: la carpeta solo va entre comillas dobles de cmd (vale con
rem espacios o apostrofos en la ruta); el puerto se comprueba con python -c sin interpolar nada.
cd /d "%~dp0.."
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
set "PYW=%CD%\.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"
set PYTHONUTF8=1
"%PY%" -c "import socket,sys;s=socket.socket();s.settimeout(0.5);sys.exit(0 if s.connect_ex(('127.0.0.1',8282))==0 else 1)" >nul 2>&1
if errorlevel 1 start "" /b /d "%CD%\launcher" "%PYW%" "%CD%\launcher\launcher_panel.py"

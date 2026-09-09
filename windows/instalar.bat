@echo off
rem ============================================================
rem  AG Launcher - instalacion en Windows. Doble clic una vez (es idempotente).
rem  Crea el entorno del launcher (.venv con cryptography), dos tareas programadas
rem  ("AG Creations\com.ag.launcher-panel" al iniciar sesion y "AG Creations\com.ag.launcher-vigilante"
rem  cada minuto), arranca el panel (http://localhost:8282) y crea el acceso directo.
rem  El panel corre como "pythonw launcher_panel.py" (no panel.py: ver launcher\launcher_panel.py).
rem  Ventanas: una tarea sin /RU (usuario actual) abre una consola cada vez que corre. Por eso los .bat
rem  se lanzan a traves de windows\oculto.vbs (wscript, ventana 0) y los programas Python con pythonw.exe.
rem  Rutas: nunca dentro de literales de python/PowerShell (un apostrofo las romperia); se pasan como
rem  argumentos entre comillas dobles de cmd.
rem ============================================================
setlocal
cd /d "%~dp0.."
set "RAIZ=%CD%"
echo === AG Launcher - instalacion en Windows ===
echo Carpeta: %RAIZ%

rem 1) Python 3.11 o mas nuevo (lanzador "py -3" o "python" en el PATH)
set "PY="
py -3 -c "import sys;sys.exit(0 if sys.version_info.major*100+sys.version_info.minor>=311 else 1)" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys;sys.exit(0 if sys.version_info.major*100+sys.version_info.minor>=311 else 1)" >nul 2>&1 && set "PY=python"
if not defined PY (
  echo.
  echo No encuentro Python 3.11 o mas nuevo.
  echo Instalalo desde https://www.python.org/downloads/windows/ y, en el instalador, marca la casilla
  echo "Add python.exe to PATH". Despues vuelve a ejecutar este instalador.
  pause
  exit /b 1
)
echo Python: %PY%

rem 2) Entorno del launcher (cryptography: verificar las firmas de las actualizaciones)
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo No pude crear el entorno .venv. Revisa la instalacion de Python.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -q --upgrade pip >nul 2>&1
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 echo (aviso: no se pudo instalar cryptography; el launcher funcionara, pero no se actualizara solo)
set "PYW=%RAIZ%\.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%RAIZ%\.venv\Scripts\python.exe"
if not exist "logs" mkdir logs
if not exist "launcher\logs" mkdir launcher\logs

rem 3) Tareas programadas (sin /RU: el usuario actual; /RL LIMITED: sin privilegios).
rem    El panel va con pythonw.exe (sin consola). El vigilante es un .bat: va a traves de
rem    "%SystemRoot%\System32\wscript.exe" "windows\oculto.vbs" "windows\vigilante.bat" para que no se vea ninguna ventana.
schtasks /Create /F /SC ONLOGON /TN "AG Creations\com.ag.launcher-panel" /TR "\"%PYW%\" \"%RAIZ%\launcher\launcher_panel.py\"" /RL LIMITED >nul
if errorlevel 1 (
  echo (ONLOGON no permitido en este PC: el arranque va a la clave Run del registro)
  reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v AG_AGCreationscomaglauncherpanel /t REG_SZ /d "\"%PYW%\" \"%RAIZ%\launcher\launcher_panel.py\"" /f >nul
)
schtasks /Create /F /SC MINUTE /MO 1 /TN "AG Creations\com.ag.launcher-vigilante" /TR "\"%SystemRoot%\System32\wscript.exe\" \"%RAIZ%\windows\oculto.vbs\" \"%RAIZ%\windows\vigilante.bat\"" /RL LIMITED >nul
if errorlevel 1 echo (aviso: no pude crear la tarea del vigilante; el panel se arranca con "AG Launcher.bat")
echo Tareas creadas: panel (al iniciar sesion) y vigilante (cada minuto, sin ventana).

rem 4) Arrancar ahora y esperar a que responda
call "%RAIZ%\windows\vigilante.bat"
".venv\Scripts\python.exe" -c "import socket,time,sys;t=time.time()+20;f=lambda:socket.create_connection(('127.0.0.1',8282),timeout=0.5).close();exec('while time.time()<t:\n try:\n  f();sys.exit(0)\n except OSError: time.sleep(0.5)\nsys.exit(1)')" 2>nul
if errorlevel 1 (
  echo.
  echo El panel NO responde en http://localhost:8282. Saco el diagnostico para ver por que:
  ".venv\Scripts\python.exe" "%RAIZ%\windows\diagnostico.py"
  echo Manda diagnostico.txt a Alejandro. No lleva contrasenas ni claves.
  pause
  exit /b 1
)

rem 5) Acceso directo en el Menu Inicio y el Escritorio (la raiz se pasa como argumento, nunca dentro del literal)
".venv\Scripts\python.exe" -c "import sys;sys.path.insert(0,sys.argv[1]);from agcore import so,app_del_catalogo,RAIZ;so.construir_acceso(app_del_catalogo('ag-launcher'),RAIZ)" "%RAIZ%"
echo.
echo LISTO. AG Launcher: http://localhost:8282 (o el acceso directo "AG Launcher").
echo La primera vez la app te pide crear tu cuenta (es local: solo vive en este PC).
start "" http://localhost:8282
pause

@echo off
rem Doble clic en Windows: arranca el panel del AG Launcher si hace falta y abre la app en el navegador.
call "%~dp0windows\vigilante.bat"
timeout /t 2 /nobreak >nul
start "" http://localhost:8282

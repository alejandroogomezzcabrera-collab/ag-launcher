@echo off
rem Doble clic: escribe diagnostico.txt con el porque de que no abra la app. No cambia nada.
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (".venv\Scripts\python.exe" "windows\diagnostico.py") else (python "windows\diagnostico.py")
pause

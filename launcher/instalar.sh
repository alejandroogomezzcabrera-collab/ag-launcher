#!/bin/zsh
# Instala el panel del AG Launcher en launchd (puerto 8282, siempre vivo) y lo arranca. Ejecutar una vez; es idempotente.
# Crea además el entorno del launcher (<raíz>/.venv con cryptography, para verificar las firmas de las actualizaciones);
# si no puede, el panel corre con el python3 del sistema y simplemente no se actualizará solo.
cd "$(dirname "$0")"
RAIZ="$(cd .. && pwd)"
mkdir -p logs
command -v python3 >/dev/null || { echo "Falta python3: instala las Command Line Tools (xcode-select --install) y repite."; exit 1; }
PY="/usr/bin/env python3"
if [[ ! -x "$RAIZ/.venv/bin/python" ]]; then python3 -m venv "$RAIZ/.venv" >/dev/null 2>&1 || true; fi
if [[ -x "$RAIZ/.venv/bin/python" ]]; then
  "$RAIZ/.venv/bin/python" -m pip install -q -r "$RAIZ/requirements.txt" >/dev/null 2>&1 \
    || echo "(aviso: no pude instalar cryptography en .venv; el launcher funciona, pero no se actualizará solo)"
  PY="$RAIZ/.venv/bin/python"
fi
mkdir -p ~/Library/LaunchAgents
# El plist lo escribe plistlib: sin word-splitting ni XML a mano, valen carpetas con espacios, apóstrofos, & o <
# (el LEEME propone «~/AG Launcher»). Programa: <raíz>/.venv/bin/python si existe; si no, /usr/bin/env python3.
if [[ -x "$RAIZ/.venv/bin/python" ]]; then PROGRAMA=("$RAIZ/.venv/bin/python"); else PROGRAMA=(/usr/bin/env python3); fi
python3 - "$PWD" "$HOME/Library/LaunchAgents/com.ag.launcher-panel.plist" "${PROGRAMA[@]}" <<'P'
import plistlib, sys
base, destino, programa = sys.argv[1], sys.argv[2], sys.argv[3:]
pl = {"Label": "com.ag.launcher-panel",
      "ProgramArguments": [*programa, base + "/panel.py"],
      "WorkingDirectory": base,
      "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", "PYTHONUTF8": "1"},
      "RunAtLoad": True, "KeepAlive": True,
      "StandardOutPath": base + "/logs/panel.log", "StandardErrorPath": base + "/logs/panel.log"}
with open(destino, "wb") as fh:
    plistlib.dump(pl, fh)
P
launchctl bootout "gui/$(id -u)/com.ag.launcher-panel" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.ag.launcher-panel.plist && launchctl enable "gui/$(id -u)/com.ag.launcher-panel"
for i in {1..20}; do curl -s -o /dev/null --max-time 1 http://localhost:8282/ag/version && break; sleep 0.5; done
echo "AG Launcher: http://localhost:8282 (panel launchd com.ag.launcher-panel, python: $PY)"

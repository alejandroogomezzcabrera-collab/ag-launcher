#!/bin/zsh
# Doble clic en el Mac: arranca el panel del AG Launcher si no responde y abre la app.
# (si macOS dice que no se puede abrir: clic derecho → Abrir, una sola vez)
cd "$(dirname "$0")"
if ! curl -s -o /dev/null --max-time 1 http://localhost:8282/ag/version; then
  if launchctl print "gui/$(id -u)/com.ag.launcher-panel" >/dev/null 2>&1; then
    launchctl kickstart -k "gui/$(id -u)/com.ag.launcher-panel"
  else
    zsh launcher/instalar.sh
  fi
  for i in {1..20}; do curl -s -o /dev/null --max-time 1 http://localhost:8282/ag/version && break; sleep 0.5; done
fi
if [[ -d "/Applications/AG Launcher.app" ]]; then open -a "/Applications/AG Launcher.app"; else open http://localhost:8282; fi

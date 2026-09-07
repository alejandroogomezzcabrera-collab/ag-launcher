#!/bin/zsh
# Instala el panel del AG Launcher en launchd (puerto 8282, siempre vivo). Ejecutar una vez.
cd "$(dirname "$0")"; mkdir -p logs
sed "s#__CARPETA__#$PWD#g" launchd/com.ag.launcher-panel.plist > ~/Library/LaunchAgents/com.ag.launcher-panel.plist
launchctl bootout "gui/$(id -u)/com.ag.launcher-panel" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.ag.launcher-panel.plist && launchctl enable "gui/$(id -u)/com.ag.launcher-panel"
echo "AG Launcher: http://localhost:8282 · App: /Applications/AG Launcher.app"

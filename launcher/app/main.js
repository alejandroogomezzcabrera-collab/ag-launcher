// AG Launcher — app de escritorio. Carga el panel local (puerto 8282); si no responde, lo despierta:
// macOS vía launchd (com.ag.launcher-panel), Windows vía la tarea programada «AG Creations\com.ag.launcher-panel».
const { app, BrowserWindow, shell } = require("electron");
const { execFile } = require("child_process");
const path = require("path");
const URL_PANEL = "http://localhost:8282";
const ES_MAC = process.platform === "darwin", ES_WIN = process.platform === "win32";

function despertarPanel() {
  if (ES_MAC && typeof process.getuid === "function") {
    execFile("/bin/launchctl", ["kickstart", "gui/" + process.getuid() + "/com.ag.launcher-panel"], () => {});
  } else if (ES_WIN) {
    execFile("schtasks", ["/Run", "/TN", "AG Creations\\com.ag.launcher-panel"], { windowsHide: true }, () => {});
  }
}
function crearVentana() {
  const win = new BrowserWindow({ width: 1380, height: 880, minWidth: 900, minHeight: 600,
    backgroundColor: "#07090f", title: "AG Launcher", titleBarStyle: ES_MAC ? "hiddenInset" : "default",
    autoHideMenuBar: true, webPreferences: { contextIsolation: true } });
  const cargar = () => win.loadURL(URL_PANEL);
  win.webContents.on("did-fail-load", () => { despertarPanel(); setTimeout(cargar, 1500); });
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  cargar();
}
app.whenReady().then(() => {
  if (app.dock) app.dock.setIcon(path.join(__dirname, "icon.png"));
  despertarPanel(); crearVentana();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) crearVentana(); });
});
app.on("window-all-closed", () => app.quit());

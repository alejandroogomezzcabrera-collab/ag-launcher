// __NOMBRE__ — app de escritorio (Electron). Carga el panel local (puerto __PUERTO__); si no responde, lo despierta vía launchd.
const { app, BrowserWindow, shell } = require("electron");
const { execFile } = require("child_process");
const path = require("path");
const URL_PANEL = "http://localhost:__PUERTO__";
function despertarPanel() { execFile("/bin/launchctl", ["kickstart", "gui/" + process.getuid() + "/com.ag.__ID__-panel"], () => {}); }
function crearVentana() {
  const win = new BrowserWindow({ width: 1300, height: 860, minWidth: 800, minHeight: 560,
    backgroundColor: "#0d1117", title: "__NOMBRE__", webPreferences: { contextIsolation: true } });
  const cargar = () => win.loadURL(URL_PANEL);
  win.webContents.on("did-fail-load", () => { despertarPanel(); setTimeout(cargar, 1500); });
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  cargar();
}
app.whenReady().then(() => {
  if (app.dock && require("fs").existsSync(path.join(__dirname, "icon.png"))) app.dock.setIcon(path.join(__dirname, "icon.png"));
  despertarPanel(); crearVentana();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) crearVentana(); });
});
app.on("window-all-closed", () => app.quit());

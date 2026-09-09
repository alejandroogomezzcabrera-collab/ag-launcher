# 🏛 AG Launcher

La tienda de **AG Creations**, las apps de Alejandro Gómez Cabrera. Con el launcher instalas en tu
ordenador (Windows o Mac) las apps que Alejandro reparte a sus amigos, y se mantienen al día solas.
Todo corre en tu propio ordenador: no hay servidores, ni cuentas en internet, ni nada que se envíe fuera.

| app | qué es | cómo llega |
|---|---|---|
| 🏛 AG Launcher | la tienda: instala, actualiza y abre las demás | este ZIP (repositorio público) |
| 🤖 Bot Lab | laboratorio de trading con **dinero ficticio**: una flota de bots que evoluciona sola y comparte sus «prodigios» con las flotas de los demás | la instala el launcher con tu **código de invitación** (repositorio privado) |

Las apps privadas de Alejandro (Shorts Factory, LLM Lab, Second Brain AI…) también están en el catálogo,
pero no se enseñan en modo amigo.

## Descarga

En [Releases](../../releases) de este repositorio: `AG-Launcher-vX.Y.Z.zip`. Cada versión está
**etiquetada y firmada** (Ed25519) por el propietario; el launcher solo se actualiza a versiones así.

## En el iPad o el móvil

Cualquier app de AG Creations se puede abrir desde tu iPad como una app más (icono en la pantalla de
inicio, a pantalla completa). El iPad es una ventana a lo que corre en tu ordenador: entras con la
misma cuenta y no se guarda ninguna clave en él. Se abre el acceso con una orden y se cierra con
otra:

```
python3 agc.py ipad tailscale bot-lab     # por tu red privada Tailscale (desde cualquier sitio)
python3 agc.py ipad lan bot-lab           # por la wifi de casa
python3 agc.py ipad off bot-lab           # cerrado (como viene de fábrica)
```

Instrucciones completas y avisos de seguridad en [IPAD.md](IPAD.md).

## Qué necesitas

- **Python 3.11 o más nuevo.** Windows: [python.org](https://www.python.org/downloads/windows/), y en el
  instalador marca la casilla **«Add python.exe to PATH»**. Mac: ya viene; si falta, `xcode-select --install`.
- **Git.** Windows: [git-scm.com](https://git-scm.com/download/win) (todo por defecto) o el botón «Instalar
  Git» del propio launcher. Mac: `xcode-select --install`.
- El **código de invitación** que te pasa Alejandro (un texto largo). Es tu llave para las apps privadas.
- Para Bot Lab: una cuenta en [app.alpaca.markets](https://app.alpaca.markets) y unas **API Keys de Paper
  Trading** (dinero ficticio; arriba a la izquierda cambia a *Paper Trading* → *API Keys* → *Generate*).

## Instalación en Windows

1. Descomprime el ZIP donde quieras (por ejemplo `C:\AG Launcher`).
2. Doble clic en **`windows\instalar.bat`** (una sola vez). Crea el entorno del launcher (`.venv`), dos tareas
   programadas (`AG Creations\com.ag.launcher-panel` al iniciar sesión y `AG Creations\com.ag.launcher-vigilante`
   cada minuto, que arranca el panel si no responde), arranca el panel y deja un acceso directo «AG Launcher»
   en el Menú Inicio y en el Escritorio.
3. Se abre `http://localhost:8282`. Crea tu cuenta (nombre, apellido y una contraseña que solo vive en tu PC;
   vale para todas las apps de AG Creations), lee los términos y entra.
4. Página **Invitación** → pega el código → **Guardar**.
5. Biblioteca → Bot Lab → **Instalar**: te pide el nombre de tu flota y las claves de Paper Trading. Se
   descarga el código, se crea su entorno de Python (varios minutos), se comprueban las claves con Alpaca y
   quedan cuatro tareas programadas trabajando solas (`BotLab pasada` cada 5 min, `BotLab vigilante` cada
   minuto, `BotLab actualizar` cada 10 min y `BotLab panel` al iniciar sesión).

Para abrir el launcher después: el acceso directo o `AG Launcher.bat`. Si falta Git, el launcher lo avisa y
ofrece instalarlo (`winget install --id Git.Git -e --source winget`).

## Instalación en Mac

1. Descomprime el ZIP donde quieras (por ejemplo `~/AG Launcher`).
2. Doble clic en **`AG Launcher.command`** (si macOS protesta, clic derecho → Abrir, una vez). Instala el
   panel en launchd (`com.ag.launcher-panel`, siempre vivo), crea `.venv` y abre la app.
3. Igual que en Windows: cuenta, invitación, Instalar Bot Lab. En el Mac, Bot Lab deja tres servicios de
   launchd (`com.botlab.pasada`, `com.botlab.vigilante`, `com.botlab.panel`) y una app en `/Applications`.

## El código de invitación

Lo genera Alejandro y contiene dos accesos de GitHub: uno de **solo lectura** al código de Bot Lab y otro al
**buzón** donde las flotas comparten prodigios. Se guarda en tu carpeta de datos (permisos solo para ti) y
nunca aparece en los registros del launcher. Si caduca o Alejandro lo renueva, pega el nuevo en la misma
página. Si hay que cortar el acceso, Alejandro revoca los tokens y reparte códigos nuevos.

## Cómo se actualiza cada cosa

- **El launcher** comprueba en GitHub la última versión etiquetada, verifica que la etiqueta está en la
  rama principal y que lleva la **firma del propietario** (`firmas/vX.Y.Z.json`, clave pública en
  `politica.json`); si todo cuadra, la instala y se reinicia. Sin Git (Windows) descarga el ZIP de esa versión
  y verifica cada fichero contra la firma antes de sustituir nada. Necesita la librería `cryptography`
  (`requirements.txt`, la instala el instalador en `.venv`); sin ella, funciona pero no se actualiza y avisa.
- **Bot Lab** se actualiza **sola** con su puente (`puente_git.py`, cada 10 min): trae la versión firmada,
  pasa sus tests en una copia aparte y solo entonces la instala. El launcher no toca su carpeta con git; solo
  ofrece «Sincronizar ahora» y enseña el estado del puente. En las instalaciones de amigos, cada
  sincronización comprueba que el código es exactamente el firmado: si se altera, se restaura y cuenta un
  *strike*; al tercero la instalación queda baneada (deja de recibir código y de compartir; tus datos no se
  tocan).

## Dónde están tus datos

| qué | Windows | Mac |
|---|---|---|
| cuenta e invitación | `%APPDATA%\AG Creations\` | `~/Library/Application Support/AG Creations/` |
| apps instaladas por el launcher | `%LOCALAPPDATA%\AG Creations\apps\<app>\` | `~/AG Creations/<app>/` |
| claves de Alpaca (Bot Lab) | `…\apps\bot-lab\.env` | `~/AG Creations/bot-lab/.env` |
| registros | `logs\` de cada app y `launcher\logs\panel.log` | ídem |

Si olvidas la contraseña: borra `cuentas.json` y `sesiones.json` de la carpeta de datos y crea la cuenta
otra vez (los datos de las apps no se tocan).

## Desinstalar

- Una app: en el launcher, menú `⋯` → **Quitar** (para sus tareas/servicios y borra su acceso; la carpeta y
  tus datos se quedan; bórrala a mano si quieres).
- El launcher: Windows → `schtasks /Delete /F /TN "AG Creations\com.ag.launcher-panel"` y lo mismo con
  `…launcher-vigilante`, borra los accesos directos y la carpeta. Mac → `launchctl bootout gui/$(id -u)/com.ag.launcher-panel`,
  borra `~/Library/LaunchAgents/com.ag.launcher-panel.plist`, `/Applications/AG Launcher.app` y la carpeta.

## Seguridad

Cada panel escucha solo en `127.0.0.1`; rechaza otros `Host`; los POST exigen cabecera propia y origen local
(CSRF); cookie de sesión `HttpOnly` + `SameSite=Strict`; CSP estricta. Las claves de Alpaca solo se escriben
en `.env`; el launcher nunca las devuelve ni las registra. Los tokens de la invitación se enmascaran en todo
registro (`x-access-token:***@`).

---

## Para Alejandro (desarrollo)

Estructura: `agcore/` (núcleo: cuentas, Guardia, `so.py` sistema, `tienda.py` motor, `firmas.py`,
`invitacion.py`, `recetas.py`), `launcher/` (panel 8282, interfaz, app Electron, `launcher_panel.py` para
Windows), `windows/` (instalador y vigilante), `plantilla/` (apps nuevas), `tests/`.

Catálogo en dos capas: `catalogo.json` (público, sin rutas) + `catalogo.local.json` (gitignorado: carpetas y
servicios reales de este Mac, p. ej. Bot Lab en `~/accc-projects/paper-trading-bot` con `com.ag.paper-*`).
`AG_CREATIONS` (raíz), `AG_DATOS` y `AG_APPS` se pueden forzar por variable de entorno.

Modo **propietario** = existe `secrets/propietario.key` (la misma clave del imperio que Bot Lab; `secrets/`
está en `.gitignore`). En este modo el launcher se actualiza con `git pull --rebase --autostash` y enseña
todas las apps.

```bash
python3 agc.py versiones                         # versión, etiqueta, cambios sin subir, panel vivo
python3 agc.py publicar "qué cambia" [--minor]   # comprueba, VERSION + launcher/VERSION, CHANGELOG, commit, FIRMA, etiqueta, push, dist/*.zip, gh release
python3 agc.py invitar "Nombre"                  # código de invitación (secrets/token_codigo + secrets/token_buzon; ver AMIGOS.md §2 de Bot Lab)
python3 agc.py subir <app> patch|minor|major -m "…"   # otras apps
python3 agc.py nuevo mi-app --nombre "Mi App" --icono 🎯 --puerto 8888
python3 agc.py comprobar
python3 -m pytest -q tests                       # con cualquier python que tenga pytest
```

Primera publicación: `git remote add origin https://github.com/alejandroogomezzcabrera-collab/ag-launcher.git`
(el mismo `repo` que dice `catalogo.json`), `git push -u origin main --tags`, y `agc.py publicar` hace el resto.

Windows se ha escrito sin poder probarlo en un PC: `so.py`, `windows\instalar.bat`, `windows\vigilante.bat`,
`AG Launcher.bat`, la receta Windows de Bot Lab y `launcher_panel.py` están marcados «sin probar en Windows».

# 🏛 AG Creations

El imperio de apps y herramientas de Alejandro Gómez Cabrera. Todas funcionan en el propio ordenador,
sin servidores ni cuentas en internet, y todas comparten este núcleo.

| app | carpeta | puerto | qué es |
|---|---|---|---|
| 🎬 Shorts Factory | `~/shorts-factory-v2` | 8585 | fábrica autónoma de shorts para YouTube |
| 🧠 LLM Lab | `~/llm-lab` | 8686 | un GPT desde cero, por dentro, con curso interactivo |
| 🌌 Second Brain AI | `~/second-brain` | 8787 | la memoria de largo plazo de Claude, en 3D |
| 🤖 Bot Lab | `~/accc-projects/paper-trading-bot` | 8484 | trading con dinero ficticio; se reparte a amigos (lleva su propia copia de la lógica de cuentas: mismo formato y misma carpeta) |

La lista viva está en `catalogo.json`; cada app lleva su versión en su fichero `VERSION`.

## Qué pone el núcleo (`agcore/`)

- **Una cuenta por dispositivo, para todas las apps.** Nombre, apellido y contraseña. Se guarda en
  `~/Library/Application Support/AG Creations/` (macOS) o `%APPDATA%\AG Creations\` (Windows): hash
  scrypt con sal, nunca la contraseña. Al abrir otra app aparece «bienvenido de nuevo»: eliges la
  cuenta, pones la contraseña y aceptas los términos de esa app la primera vez. También se puede crear
  otra cuenta. Nada sale del ordenador; no hay servidor de cuentas.
- **Seguridad de cada panel** (`Guardia`): solo escucha en 127.0.0.1; rechaza otros `Host` (DNS
  rebinding); los POST exigen la cabecera `X-AG: 1` y origen local (CSRF); cookie de sesión `HttpOnly`
  + `SameSite=Strict` (30 días, 5 fallos → 1 minuto de bloqueo); CSP estricta, `nosniff`,
  `X-Frame-Options: DENY`; los datos solo con sesión (la interfaz html/css/js es pública).
- **Términos por app** (`TERMINOS.md` en cada carpeta). Si cambian, la app los vuelve a pedir sola
  (la versión de los términos es el hash del fichero).
- **Pantalla de acceso y chip de cuenta** (`agcore/web/`): se inyectan en cada app con dos líneas en
  su `index.html`; el chip de abajo a la derecha da acceso a términos, cambio de contraseña, «acerca
  de» (el catálogo del imperio con versiones) y salir.

## Cómo se conecta una app (ya hecho en las cuatro)

```python
AG_CREATIONS = Path(os.environ.get("AG_CREATIONS", Path.home() / "ag-creations"))
sys.path.insert(0, str(AG_CREATIONS))
from agcore.acceso import Guardia
G = Guardia("mi-app", PUERTO, BASE)
# en _send: G.cabeceras(self) antes de end_headers()
# en do_GET:  if not G.host_ok(self) or G.get(self, ruta): return
#             if not _estatico(ruta) and not G.exigir(self): return
# en do_POST: if not G.host_ok(self) or not G.post_ok(self) or G.post(self, ruta) or not G.exigir(self): return
```

En `index.html`: `<link rel="stylesheet" href="/ag/acceso.css">` y `<script src="/ag/acceso.js"></script>`
antes del `app.js`; en `app.js`, el arranque dentro de `AG.listo(() => {...})`.

## La consola: `agc.py`

```bash
python3 ~/ag-creations/agc.py versiones                    # versión, etiqueta, cambios sin subir y si el panel está vivo
python3 ~/ag-creations/agc.py subir llm-lab minor -m "qué cambia"   # VERSION + CHANGELOG + commit + etiqueta vX.Y.Z (--todo para incluir todos los cambios)
python3 ~/ag-creations/agc.py nuevo mi-app --nombre "Mi App" --icono 🎯 --puerto 8888 --descripcion "…"
python3 ~/ag-creations/agc.py comprobar                    # tests de agcore + revisión de cada app
```

`nuevo` copia `plantilla/` (panel con Guardia, interfaz mínima, términos, launchd, app Electron),
hace el primer commit con la etiqueta `v0.1.0` y añade la app al catálogo. Versionado semántico:
`patch` arreglos, `minor` funciones nuevas, `major` cambios que rompen.

## Si olvidas la contraseña

Borra `cuentas.json` y `sesiones.json` de la carpeta de datos y crea la cuenta otra vez. Los datos de
cada app están en su carpeta y no se tocan.

## Tests

```bash
~/llm-lab/.venv/bin/python -m pytest -q ~/ag-creations/tests
```

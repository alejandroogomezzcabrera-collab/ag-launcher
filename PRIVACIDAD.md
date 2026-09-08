# Política de privacidad de las apps de AG Creations

Versión del 7 de septiembre de 2026. Escrita en cristiano, sin letra pequeña. Vale para todas las
apps de AG Creations: AG Launcher, Bot Lab, Shorts Factory, LLM Lab y Second Brain AI. Si una app
necesita decir algo más, lo dice al principio de su propia copia de este documento.

## 1. Quién es el responsable y cómo contactar

- **Responsable**: Alejandro Gómez Cabrera, particular residente en España. «AG Creations» es el
  nombre con el que firma sus apps; no es una empresa ni tiene empleados.
- **Contacto**: alejandroogomezzcabrera@gmail.com. Para cualquier cosa de esta política, escribe ahí.
- No hay delegado de protección de datos: para un particular que reparte apps entre amigos no es
  obligatorio, y no lo hay.

## 2. Qué es una app AG Creations y por qué casi nada sale de tu ordenador

Una app AG Creations es un programa que se instala en **tu** ordenador (Mac o Windows) y funciona
ahí: su panel es una página web que solo escucha en tu propia máquina (`127.0.0.1`), no es visible
desde tu red ni desde internet, y sus datos viven en su carpeta. **No hay servidor de AG Creations**:
no existe ningún ordenador de Alejandro al que las apps manden lo que haces. No hay analítica, ni
rastreo, ni identificadores de publicidad, ni cuentas en internet.

Lo poco que sale de tu ordenador sale porque la app lo necesita para hacer lo que le pides (subir un
vídeo a tu YouTube, pedir precios a tu bróker, comprobar si hay versión nueva en GitHub), y va
directo de tu ordenador al proveedor de ese servicio, con **tus** credenciales, sin pasar por
Alejandro. La tabla del apartado 4 lo enumera app por app. La única excepción es el **buzón de Bot
Lab**, un repositorio privado de GitHub de Alejandro que sí recibe datos (sobre bots, no sobre ti);
se explica en el apartado 4 y, con más detalle, en la copia de esta política que va con Bot Lab.

## 3. La cuenta AG Creations

- **Qué se guarda**: tu nombre, tu apellido, un *hash* de tu contraseña (scrypt con sal aleatoria;
  la contraseña en sí no se guarda y no se puede recuperar), la fecha de creación, qué versión de
  los términos y de esta política has aceptado en cada app y cuándo entraste por última vez en cada
  una. Nada más: ni correo, ni teléfono, ni nada que no hayas tecleado tú.
- **Dónde**: en la carpeta de datos de tu usuario, ficheros `cuentas.json` y `sesiones.json`:
  `%APPDATA%\AG Creations` en Windows, `~/Library/Application Support/AG Creations` en macOS.
  Puedes abrirlos con cualquier editor de texto y ver exactamente qué hay.
- **A dónde va**: a ningún sitio. No existe servidor de cuentas. **Alejandro nunca recibe tu
  cuenta**, ni tu nombre, ni tu hash. Bot Lab tampoco la sube al buzón: allí solo viaja un
  identificador aleatorio de instalación y el nombre de flota que tú eliges.
- **Para qué**: para abrir las apps en tu ordenador y para que cada app sepa si ya aceptaste sus
  términos. Es la misma cuenta para todas las apps de AG Creations de ese ordenador.
- **Cómo borrarla**: borra `cuentas.json` y `sesiones.json` de esa carpeta. Ya está: no hay copia
  en ningún otro sitio. Los datos de cada app (tus vídeos, tus bots, tus modelos) están en la
  carpeta de cada app y no se tocan. En las apps con núcleo común también puedes borrarla desde el
  propio panel.

## 4. Qué sale de tu ordenador, app por app

La «base» de cada tratamiento es sencilla: **tú instalas el programa y le pides que haga eso**. Donde
una app manda algo a un tercero lo hace con tus credenciales y porque es la función que has puesto
en marcha; aceptar los términos y esta política es tu consentimiento para que lo haga. Donde no hay
nada que mandar, no se manda nada.

### AG Launcher (puerto 8282)

| Qué sale | A quién | Para qué | Cuánto tiempo |
|---|---|---|---|
| Una petición `git fetch` (tu dirección IP y, si la app tiene repositorio, el token de acceso) | GitHub | Saber si hay versión nueva de cada app | GitHub guarda sus registros según su política; en tu ordenador no queda registro |
| Nada más | — | — | — |

En **modo amigo** (cuando instalas apps con un código de invitación que te ha dado Alejandro), el
launcher guarda ese código, que contiene tokens de GitHub de solo lectura, en la carpeta de datos
de tu usuario. Los tokens son de Alejandro: para GitHub, quien descarga es «el token de Alejandro»,
no tú. Para dejar de usarlos, borra el fichero de la invitación de esa carpeta.

### Bot Lab (puerto 8484)

| Qué sale | A quién | Para qué | Cuánto tiempo |
|---|---|---|---|
| Órdenes y consultas de tu cuenta *paper* (dinero ficticio), con **tus** claves de Alpaca | Alpaca | Espejar en tu cuenta paper lo que hacen los bots; leer precios | Lo que diga la política de Alpaca; las claves están solo en tu `.env` |
| Peticiones a fuentes públicas de noticias y calendarios (RSS de medios cripto, calendarios de la Reserva Federal y del BLS) | Esos sitios web | Los «noticieros» de la flota | No se manda nada tuyo salvo tu IP, como al abrir cualquier web |
| **Prodigios**: la ficha de un bot que ha superado todas las pruebas (genoma, estadísticas, últimas operaciones **virtuales**) | Buzón: repositorio privado de GitHub de Alejandro | Que ese bot compita en las flotas de los demás | Hasta que se borre; ver apartado 5 |
| **Latido** (como mucho uno por hora): id aleatorio de instalación, huella de la máquina (16 caracteres, no reversible), nombre de flota que eliges tú, sistema operativo, versión, ciclo, nº de bots, nº de operaciones virtuales, retorno virtual, nº de prodigios, si tiene actualizaciones automáticas, nº de *strikes*, si el código estaba alterado y hora | Buzón | Ver qué flotas trabajan y cuánto, y aplicar la política de integridad | Se sobreescribe con cada latido; se borra al pedirlo, ver apartado 5 |
| `git fetch` del repositorio de código (tu IP y un token de solo lectura de Alejandro) | GitHub | Recibir versiones nuevas y la política | Según GitHub |

**Nunca** salen: tus claves de Alpaca, tus saldos ni posiciones, tu cuenta de la app, tus ficheros,
tu nombre real (salvo que lo pongas como nombre de flota). La copia de esta política que va con Bot
Lab explica campo a campo el latido, la huella, los *strikes* y el baneo.

### Shorts Factory (puerto 8585)

| Qué sale | A quién | Para qué | Cuánto tiempo |
|---|---|---|---|
| El tema del vídeo y las instrucciones para escribir el guion, con **tu** `ANTHROPIC_API_KEY` (o a través del programa `claude` con tu sesión) | Anthropic | Escribir el guion | Según la política de Anthropic |
| La descripción de cada imagen (el *prompt*, dentro de la URL), sin credenciales, tier anónimo | Pollinations | Generar las imágenes | Según Pollinations; no exige cuenta |
| Si tú lo configuras en vez de Pollinations: el *prompt* con tu `OPENAI_API_KEY`, o una búsqueda en Wikimedia Commons | OpenAI / Wikimedia | Generar o buscar las imágenes | Según cada uno |
| El texto de cada frase del guion | Microsoft (servicio de voz que usa `edge-tts`) | Generar la voz | Según Microsoft |
| Una búsqueda de música con **tu** Client ID de Jamendo | Jamendo | Elegir la música | Según Jamendo |
| El vídeo, título, descripción, etiquetas y miniatura, con **tus** credenciales de Google | YouTube (Google) | Publicar en **tu** canal y leer sus métricas (permisos `youtube.upload` y `youtube.readonly`) | Lo que tú decidas en YouTube |

Tus credenciales de Google viven en `secrets/` dentro de la carpeta de la app y solo se usan contra
la API de Google. Para revocarlas: https://myaccount.google.com/permissions (quita el acceso de la
app) y borra `secrets/`. Las demás claves están en `.env`; bórralas de ahí y de la web de cada
proveedor cuando quieras.

### LLM Lab (puerto 8686)

| Qué sale | A quién | Para qué | Cuánto tiempo |
|---|---|---|---|
| Nada | — | Entrena y ejecuta modelos en tu CPU/GPU con PyTorch | El nombre que pones en el diploma se guarda en `data/`, en tu ordenador |

### Second Brain AI (puerto 8787)

| Qué sale | A quién | Para qué | Cuánto tiempo |
|---|---|---|---|
| Nada | — | Calcula los *embeddings* con Ollama en tu propio ordenador | El índice está en `data/`, en tu ordenador |

Ojo: Second Brain indexa código, transcripts de sesiones de Claude Code y notas, y eso **puede
contener datos de otras personas** (un correo en un fichero, un nombre en una nota). No sale de tu
ordenador, pero eres tú quien decide qué indexa (`cerebro/config.py`, lista PROYECTOS): no apuntes
carpetas con datos de terceros que no deban estar ahí.

## 5. Tus derechos y cómo ejercerlos

Tienes derecho a acceder a tus datos, rectificarlos, suprimirlos, oponerte a su tratamiento,
limitarlo y llevártelos (portabilidad). Como casi todo está en tu ordenador, casi todo lo ejerces
tú mismo, ahora, sin pedir permiso a nadie:

- **Acceso y portabilidad**: abre los ficheros. Son JSON y texto en la carpeta de la app y en la
  carpeta de datos de tu usuario. Cópialos donde quieras.
- **Rectificación**: edítalos, o borra la cuenta y créala otra vez con los datos correctos.
- **Supresión, oposición y limitación**: borra `cuentas.json` y `sesiones.json` (la cuenta), borra
  `secrets/` y `.env` (las credenciales) y borra la carpeta de la app (todo lo demás). Alejandro no
  tiene copia de nada de eso, así que no hay nada más que borrar.
- **Lo que está en el buzón de Bot Lab** (latido y prodigios) sí está en un sitio de Alejandro.
  Escribe a alejandroogomezzcabrera@gmail.com con el id de tu instalación (lo ves en `flota.json`
  y en Prodigios › Buzón) y Alejandro borra `flotas/<id>.json` y `prodigios/<id>-*.json` del
  buzón. El buzón es un repositorio git y guarda historial: si quieres que desaparezca también del
  historial, dilo y Alejandro lo reescribe o crea un buzón nuevo. Plazo: en cuanto lo lea, y como
  mucho en un mes.
- **Lo que está en manos de un proveedor** (Alpaca, Google, Anthropic…) lo gestionas con ese
  proveedor: son tus cuentas, no las de Alejandro.

Si crees que algo no se está haciendo bien y hablar con Alejandro no lo arregla, puedes reclamar
ante la **Agencia Española de Protección de Datos**: https://www.aepd.es.

## 6. Proveedores que pueden recibir algo

Todos reciben lo que reciben directamente desde tu ordenador y con tus credenciales; ninguno tiene
relación con AG Creations ni le manda nada.

| Proveedor | Lo usa | Su política |
|---|---|---|
| GitHub (Microsoft) | AG Launcher, Bot Lab | https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement |
| Alpaca | Bot Lab | https://alpaca.markets/privacy |
| Google / YouTube | Shorts Factory | https://policies.google.com/privacy · https://www.youtube.com/t/terms |
| Anthropic | Shorts Factory | https://www.anthropic.com/privacy |
| Pollinations | Shorts Factory | https://pollinations.ai |
| OpenAI (solo si lo configuras) | Shorts Factory | https://openai.com/policies/privacy-policy |
| Wikimedia Commons (solo si lo configuras) | Shorts Factory | https://foundation.wikimedia.org/wiki/Policy:Privacy_policy |
| Microsoft (voz) | Shorts Factory | https://privacy.microsoft.com/privacystatement |
| Jamendo | Shorts Factory | https://www.jamendo.com/legal |
| Medios y calendarios públicos (RSS, Reserva Federal, BLS) | Bot Lab | Cada web la suya |

Ollama, PyTorch y Python funcionan en tu ordenador y no mandan nada.

## 7. Menores

Las apps de AG Creations están pensadas para adultos. **Bot Lab exige ser mayor de 18 años** (es la
edad que exige Alpaca para abrir una cuenta, aunque sea paper). Si eres menor, no las uses; si te
consta que un menor las está usando, escribe al correo de contacto y Alejandro borrará lo que haya
en el buzón.

## 8. Cambios en esta política

Si cambia el texto de esta política o el de los términos, la app te los vuelve a enseñar y te pide
aceptarlos antes de seguir (la app calcula una huella de los dos documentos y la compara con la
que aceptaste). La fecha de la versión vigente está arriba del todo.

## 9. Resumen para los que no leen

Todo vive en tu ordenador. No hay servidor de Alejandro. Lo que sale, sale a proveedores que tú
has elegido y con tus claves. Lo único que llega a Alejandro es el buzón de Bot Lab, con datos de
bots y un latido sin tu nombre; se borra escribiéndole. Eres mayor de edad. Si algo no cuadra,
escribe: alejandroogomezzcabrera@gmail.com.

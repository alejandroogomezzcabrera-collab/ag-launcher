# Términos de uso de __NOMBRE__

Una app de **AG Creations**. Versión del __FECHA__. Escrito en cristiano, sin letra pequeña.

## Qué es esto

__NOMBRE__: __DESCRIPCION__

No es un producto ni se vende. Es una herramienta personal de AG Creations.

## Qué hace en tu ordenador

- Una tarea programada (launchd) mantiene el panel vivo en el puerto __PUERTO__.
- Guarda sus datos en `data/`, dentro de su carpeta.

## Qué se queda en tu ordenador (todo)

Tus datos y tu cuenta de la app no salen de tu ordenador. No hay analítica, ni rastreo, ni identificadores de publicidad.

## Tu cuenta AG Creations

- La cuenta (nombre, apellido y contraseña) sirve **solo para abrir las apps de AG Creations en este
  dispositivo**. Es la misma para todas: si ya la creaste en otra app, aquí verás «bienvenido de nuevo»
  y solo tendrás que escribir la contraseña.
- No existe ningún servidor de cuentas. Crear la cuenta no envía nada a ningún sitio.
- La contraseña no se guarda: se guarda un *hash* (scrypt con sal aleatoria) en la carpeta de datos
  del usuario (`~/Library/Application Support/AG Creations` en macOS, `%APPDATA%\AG Creations` en
  Windows). Nadie, ni AG Creations, puede leerla ni recuperarla.
- Si la olvidas: borra `cuentas.json` y `sesiones.json` de esa carpeta y crea la cuenta otra vez. No
  pierdes nada: los datos de cada app están en la carpeta de cada app.
- Tras 5 intentos fallidos seguidos la cuenta se bloquea un minuto. Las sesiones caducan a los 30 días.
- Cada app te pide aceptar **sus** términos la primera vez que entras con la cuenta, y otra vez si
  cambian.

## Seguridad

- El panel escucha únicamente en tu propio ordenador (`127.0.0.1`). No es visible desde tu red ni
  desde internet.
- Rechaza peticiones con otro nombre de servidor (protección contra *DNS rebinding*) y cualquier
  acción que no venga de la propia app (cabecera propia y origen local: protección *CSRF*).
- La sesión va en una cookie `HttpOnly` y `SameSite=Strict`; la página lleva política de contenido
  estricta (`CSP`), no se puede incrustar en otras webs y no carga nada de fuera.
- Los datos solo se sirven con la sesión abierta. La interfaz en sí (html, css, js) es pública porque
  no contiene datos.

## Quién está detrás y cómo contactar

AG Creations es **Alejandro Gómez Cabrera**, un particular en España que hace apps gratuitas, locales y
sin servidor para él y sus amigos. No es una empresa. Para cualquier duda, queja, petición sobre tus
datos o idea: **alejandroogomezzcabrera@gmail.com**.

## Licencia de uso

Tienes una licencia **personal, gratuita, no exclusiva e intransferible** para instalar y usar la app en
tus propios ordenadores. No la modifiques para seguir usándola modificada, no la redistribuyas (ni la
publiques ni se la pases a nadie: que se la pidan a Alejandro) y no la uses con fines comerciales. El
código sigue siendo de Alejandro; lo que tú produces con la app es tuyo. Las librerías y programas de
terceros que usa van con sus propias licencias. El texto completo está en `LICENCIA.md` (menú de la
cuenta › 📄 Licencia).

## Privacidad

- Todo vive en tu ordenador: no hay servidor de AG Creations, ni analítica, ni rastreo, ni cuentas en
  internet.
- Tu cuenta (nombre, apellido y el *hash* de la contraseña) se guarda en la carpeta de datos de tu
  usuario y **Alejandro nunca la recibe**.
- Esta app no manda nada a ningún sitio: sus datos están en `data/`, dentro de su carpeta.
- Todo lo borras tú mismo: la cuenta (`cuentas.json` y `sesiones.json`), las credenciales y la carpeta
  de la app. Alejandro no tiene copia de nada de eso.
- Tienes los derechos de acceso, rectificación, supresión, oposición, limitación y portabilidad; para lo
  local, los ejerces tú borrando o copiando ficheros; para lo demás, escribe al correo de arriba. Si algo
  no se arregla, puedes reclamar ante la AEPD (https://www.aepd.es).

La política completa está en `PRIVACIDAD.md` (menú de la cuenta › 🔒 Privacidad), **que aceptas junto con
estos términos**.

## Sin garantía y sin responsabilidad

- Se entrega **tal cual**, sin garantía de ningún tipo: puede tener errores, puede dejar de funcionar,
  puede desaparecer. Es un proyecto personal que se comparte gratis.
- Hasta donde la ley permita, Alejandro no responde de ningún daño que venga de usar la app o de no
  poder usarla (datos perdidos, tiempo perdido, decisiones que tomes mirando lo que enseña, ni de lo
  que hagan los servicios de terceros). Si la ley no permite excluir algo, esa parte no se excluye y el
  resto sigue valiendo.

## Marcas de terceros

Alpaca, TradingView, GitHub, Google, YouTube, Pollinations, Jamendo, Microsoft, Anthropic, Claude,
OpenAI, Ollama, PyTorch, Python, Apple y Electron son marcas de sus dueños. AG Creations no tiene
relación con ellos ni está patrocinada, avalada ni supervisada por ellos.

## Edad mínima

Esta app está pensada para adultos. Al aceptar estos términos confirmas que eres mayor de edad. Si no lo eres, no la uses.

## Ley aplicable

Estos términos, la licencia y la política de privacidad se rigen por la **ley española**. Para lo que no
se pueda arreglar hablando, los juzgados que correspondan según esa ley. Autoridad de control en
materia de datos: la Agencia Española de Protección de Datos (https://www.aepd.es).

## Despedida

Para dejar de usarla: deshabilita su tarea programada (`launchctl bootout gui/$(id -u)/com.ag.__ID__-panel`)
y borra la carpeta. No queda nada más en ningún sitio.

Si cambian estos términos o la política de privacidad, la app te los volverá a enseñar antes de seguir.

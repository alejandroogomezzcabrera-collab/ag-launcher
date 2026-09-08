# Términos de uso de AG Launcher

Una app de **AG Creations**. Versión del 7 de septiembre de 2026. Escrito en cristiano, sin letra pequeña.

## Qué es esto

AG Launcher es la **tienda del imperio**: enseña todas las apps de AG Creations que hay en este Mac y
permite instalarlas, actualizarlas, abrirlas, reiniciar su panel y quitarlas. No es un producto ni se
vende. Es la herramienta de AG Creations para administrar sus propias apps.

## Qué hace en tu ordenador

- Una tarea programada (launchd) mantiene su panel vivo en el puerto 8282.
- **Instalar** una app: crea su entorno de Python, registra sus servicios en launchd y construye su app
  de escritorio en `/Applications`.
- **Actualizar**: si la app está en GitHub, descarga la última versión etiquetada (`git pull`
  conservando tus cambios locales); reinstala dependencias si cambiaron; reinicia el panel y
  reconstruye la app de escritorio.
- **Quitar**: para y retira sus servicios y borra la app de `/Applications`. **La carpeta del
  proyecto y tus datos no se tocan nunca.**
- Solo toca las carpetas que figuran en `~/ag-creations/catalogo.json`.

## Qué se queda en tu ordenador (todo)

Todo. Lo único que sale es la consulta a GitHub para saber si hay versión nueva de las apps que
tengan repositorio (una petición `git fetch` normal). No hay analítica, ni rastreo, ni identificadores.

## Modo amigo e invitaciones

Si Alejandro te ha dado un **código de invitación**, el launcher lo guarda en la carpeta de datos de tu
usuario y lo usa para descargar las apps privadas (por ejemplo Bot Lab) desde sus repositorios de
GitHub. El código contiene tokens de **solo lectura** de Alejandro: sirven para bajar código, no para
subirlo, y para GitHub quien descarga es «el token de Alejandro», no tú. Cada app que instales te pedirá
aceptar **sus** términos y su política de privacidad. Alejandro puede revocar esos tokens cuando quiera
(entonces el launcher deja de poder descargar, pero lo que ya tienes instalado sigue funcionando).

## Tu cuenta AG Creations

- La cuenta (nombre, apellido y contraseña) es la misma para todas las apps de AG Creations de este
  dispositivo y solo sirve para abrirlas aquí. No existe ningún servidor de cuentas.
- Se guarda un *hash* (scrypt con sal) en `~/Library/Application Support/AG Creations` (en Windows,
  `%APPDATA%\AG Creations`). Si olvidas la contraseña, borra allí `cuentas.json` y `sesiones.json` y
  créala otra vez.
- Tras 5 intentos fallidos la cuenta se bloquea un minuto. Las sesiones caducan a los 30 días.

## Seguridad

- El panel escucha solo en `127.0.0.1`, rechaza otros nombres de servidor (*DNS rebinding*) y cualquier
  acción que no venga de la propia app (cabecera propia y origen local: *CSRF*).
- Cookie `HttpOnly` + `SameSite=Strict`, política de contenido estricta, sin incrustar en otras webs.
- Las acciones de instalar, actualizar y quitar exigen sesión abierta.

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
- Lo único que sale es una petición `git fetch` a GitHub para ver si hay versión nueva (GitHub ve tu IP,
  como cualquier web). En modo amigo, el código de invitación con los tokens de solo lectura de
  Alejandro se guarda en esa misma carpeta de datos; bórralo de ahí para dejar de usarlo.
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

Para dejar de usarla: `launchctl bootout gui/$(id -u)/com.ag.launcher-panel` y borra la app y la
carpeta `launcher/`. Si quieres borrar también la cuenta y la invitación, vacía la carpeta de datos
de AG Creations. No queda nada más.

Si cambian estos términos o la política de privacidad, la app te los volverá a enseñar antes de seguir.

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

## Tu cuenta AG Creations

- La cuenta (nombre, apellido y contraseña) es la misma para todas las apps de AG Creations de este
  dispositivo y solo sirve para abrirlas aquí. No existe ningún servidor de cuentas.
- Se guarda un *hash* (scrypt con sal) en `~/Library/Application Support/AG Creations`. Si olvidas la
  contraseña, borra allí `cuentas.json` y `sesiones.json` y créala otra vez.
- Tras 5 intentos fallidos la cuenta se bloquea un minuto. Las sesiones caducan a los 30 días.

## Seguridad

- El panel escucha solo en `127.0.0.1`, rechaza otros nombres de servidor (*DNS rebinding*) y cualquier
  acción que no venga de la propia app (cabecera propia y origen local: *CSRF*).
- Cookie `HttpOnly` + `SameSite=Strict`, política de contenido estricta, sin incrustar en otras webs.
- Las acciones de instalar, actualizar y quitar exigen sesión abierta.

## Garantía, licencia y despedida

- Se entrega **tal cual**, sin garantía. Pertenece a **AG Creations** (Alejandro Gómez Cabrera); uso
  personal, no redistribuir sin preguntar.
- Para dejar de usarla: `launchctl bootout gui/$(id -u)/com.ag.launcher-panel` y borra la app y la
  carpeta `launcher/`. No queda nada más.

Si cambian estos términos, la app te los volverá a enseñar antes de seguir.

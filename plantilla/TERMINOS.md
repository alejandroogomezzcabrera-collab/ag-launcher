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

## Garantía, licencia y despedida

- Se entrega **tal cual**, sin garantía de ningún tipo: puede tener errores o dejar de funcionar.
- Pertenece a **AG Creations** (Alejandro Gómez Cabrera). Es para uso personal; no la publiques ni la
  redistribuyas sin preguntar.
- Para dejar de usarla: deshabilita su tarea programada (`launchctl bootout gui/$(id -u)/com.ag.__ID__-panel`)
  y borra la carpeta. No queda nada más en ningún sitio.

Si cambian estos términos, la app te los volverá a enseñar antes de seguir.

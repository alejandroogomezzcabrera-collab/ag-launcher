# Tus apps de AG Creations en el iPad (y en el iPhone)

Todas las apps de AG Creations (AG Launcher, Bot Lab, LLM Lab, Second Brain, Shorts Factory) se
pueden abrir desde el iPad como una app más: icono en la pantalla de inicio, a pantalla completa y
sin barra de navegador. El iPad es **una ventana** a lo que corre en tu ordenador, con la misma
cuenta, la misma contraseña y las mismas barreras de seguridad.

En el caso de Bot Lab: los 16 bots, el torneo y las operaciones siguen corriendo en tu Mac o en tu
PC; el iPad solo lo mira y lo controla.

**Por qué el trabajo no se hace en el iPad.** iOS no deja que un programa siga trabajando en segundo
plano indefinidamente, ni tiene Python, ni git, ni tareas programadas cada cinco minutos. Un Bot Lab
que operase dentro del iPad se pararía en cuanto cerrases la app o bloqueases la pantalla. Por eso
el trabajo se queda en el ordenador, que además es donde viven tus claves.

---

## Antes de empezar

- Bot Lab instalado y funcionando en tu Mac o tu PC (con sus claves paper de Alpaca ya puestas).
- Ese ordenador encendido cuando quieras mirar desde el iPad.
- Tu cuenta AG Creations: en el iPad entrarás con el mismo nombre y contraseña.

Las claves de Alpaca **no se escriben nunca en el iPad**: ya están en el ordenador, en su fichero
`.env`. Si aún no las has puesto, la app te lo explica en «Primeros pasos» (menú de tu cuenta).

---

## Opción A · Tailscale (recomendada: funciona desde cualquier sitio)

Tailscale crea una red privada solo tuya entre tus dispositivos. Es gratis para uso personal y no
abre nada a internet.

1. **En el ordenador**: instala Tailscale desde https://tailscale.com/download e inicia sesión.
2. **En el iPad**: instala Tailscale desde la App Store e inicia sesión **con la misma cuenta**.
3. **En el ordenador**, en la carpeta de Bot Lab:

   - Mac: `./venv/bin/python ipad.py tailscale`
   - Windows: `venv\Scripts\python.exe ipad.py tailscale`

   (para las demás apps de AG Creations, la orden equivalente es
   `python3 ~/ag-creations/agc.py ipad tailscale <app>`)

   Te responderá con una dirección tipo `http://100.x.y.z:8484/`.
4. **En el iPad**: abre esa dirección en Safari.

Con Tailscale encendido en los dos, esto funciona igual en casa, en el móvil o de vacaciones, y
nadie más puede ver el panel: solo tus propios dispositivos.

## Opción B · La wifi de casa (más simple, solo en casa)

1. En el ordenador, en la carpeta de Bot Lab:

   - Mac: `./venv/bin/python ipad.py lan`
   - Windows: `venv\Scripts\python.exe ipad.py lan`

   Te dará una dirección tipo `http://192.168.0.84:8484/`.
2. En el iPad, con la misma wifi, abre esa dirección en Safari.

Aviso honesto: en este modo, cualquiera conectado a esa wifi puede llegar a la **pantalla de
acceso** de Bot Lab. Para entrar sigue necesitando tu contraseña, pero si compartes la wifi con
gente que no conoces, usa la opción A.

## Cerrarlo

`./venv/bin/python ipad.py off` (Windows: `venv\Scripts\python.exe ipad.py off`). El panel vuelve a
escuchar solo dentro del ordenador, como de fábrica. `ipad.py` sin nada te dice cómo está.

---

## Instalar el icono en la pantalla de inicio

1. Abre la dirección en **Safari** (tiene que ser Safari; Chrome en iOS no puede instalar apps).
2. Toca **Compartir** (el cuadradito con la flecha) → **Añadir a pantalla de inicio**.
3. Ponle el nombre que quieras y toca **Añadir**.

Ya tienes el icono de Bot Lab con las demás apps. Al abrirlo se ve a pantalla completa, sin barra de
direcciones, como cualquier app. La sesión dura 30 días, así que no tendrás que escribir la
contraseña cada vez.

Lo mismo vale para el **AG Launcher** y para las demás apps de AG Creations: cada una tiene su
dirección y su icono.

---

## Qué puedes hacer desde el iPad

Todo lo que ves en el ordenador: resumen de la flota, operaciones abiertas y cerradas, cada bot con
su estrategia, el cerebro, la sala de entreno, los prodigios, las flotas conectadas y la guía. Si
eres el propietario, también los ajustes de flota y banear o perdonar flotas.

Lo que **no** cambia: los bots operan en el ordenador. Si lo apagas, la flota se para, mires desde
donde mires.

---

## Seguridad (lo que no se ha tocado)

Abrir el acceso solo cambia **por qué dirección** se puede llegar al panel. Todo lo demás sigue
exactamente igual:

- Hace falta iniciar sesión con tu cuenta AG Creations (contraseña con hash scrypt, cinco intentos
  fallidos bloquean un minuto).
- El panel rechaza cualquier petición dirigida a un nombre de servidor que no sea el tuyo, y toda
  acción exige una cabecera propia de la app y origen local.
- La cookie de sesión es `HttpOnly` y `SameSite=Strict`; la página lleva política de contenido
  estricta y no se puede incrustar en otras webs.
- Los datos (estado, operaciones, acciones) no se sirven sin sesión abierta.
- El iPad no guarda claves de Alpaca ni puede saltarse ninguna de estas barreras: es un navegador
  hablando con tu propio ordenador.

## Si algo no va

- **No carga en el iPad**: comprueba que el ordenador está encendido y despierto, que Tailscale está
  activo en los dos (opción A) o que ambos están en la misma wifi (opción B), y vuelve a mirar la
  dirección con `python ipad.py`.
- **«No es privado» o aviso de Safari**: es normal, la conexión es dentro de tu propia red y no
  lleva certificado. Continúa; nada sale a internet.
- **El icono abre una página en blanco**: el ordenador se habrá dormido. Despiértalo y recarga.
- **Cambiaste de red y ya no funciona**: la IP de casa cambia; vuelve a ejecutar `ipad.py lan` (con
  Tailscale la dirección no cambia nunca).

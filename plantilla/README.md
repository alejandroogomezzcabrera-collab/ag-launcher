# __ICONO__ __NOMBRE__

__DESCRIPCION__

Una app de **AG Creations**. Creada el __FECHA__ desde la plantilla de `~/ag-creations`.

## Arrancar

```bash
python3 panel.py          # http://localhost:__PUERTO__
```

La primera vez pide la cuenta AG Creations del dispositivo (si ya existe, «bienvenido de nuevo»).

## Instalar en launchd (siempre viva)

```bash
sed "s#__CARPETA__#$(pwd)#g" launchd/com.ag.__ID__-panel.plist > ~/Library/LaunchAgents/com.ag.__ID__-panel.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ag.__ID__-panel.plist
```

## App de escritorio

```bash
cd app && npm install && npm run empaquetar      # deja "__NOMBRE__.app" en app/dist/
```

## Dónde tocar

- `panel.py`: `_estado()` (lo que se pinta) y `_accion()` (los botones). Las rutas `/ag/*`, la sesión y
  las cabeceras de seguridad las pone `agcore` (no hace falta tocarlas).
- `panel_web/app.js` y `app.css`: la interfaz. Arranca dentro de `AG.listo(...)`.
- `TERMINOS.md`: los términos de esta app (se vuelven a pedir solos si cambian).
- Versiones: `python3 ~/ag-creations/agc.py subir __ID__ patch -m "qué cambia"`.

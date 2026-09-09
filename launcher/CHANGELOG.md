# Cambios de AG Launcher

## 1.3.7 — 2026-09-09

- el catalogo apunta a Bot Lab 3.21.2

## 1.3.6 — 2026-09-09

- cuando el panel no arranca ya se puede saber por que: windows/diagnostico.bat (y diagnostico.py) escribe un informe, el instalador de Windows lo saca solo si el panel no responde, y launcher_panel.py apunta en logs/panel.log cualquier fallo al importar (con pythonw no hay consola y hasta ahora se moria sin dejar rastro)

## 1.3.5 — 2026-09-09

- los tests tampoco nombran ya las apps que no reparto: el mundo de pruebas usa una app inventada en el catalogo local

## 1.3.4 — 2026-09-09

- el ZIP de un amigo ya no nombra en ningun sitio las apps que no reparto (colores del launcher, ejemplo de acceso.py, README y tests)

## 1.3.3 — 2026-09-09

- el catalogo publico solo lleva AG Launcher y Bot Lab: las apps que no reparto viven enteras en catalogo.local.json, asi ni el repositorio ni el ZIP de un amigo dicen que existen; tests que lo vigilan

## 1.3.2 — 2026-09-09

- la copia de un amigo ya no ensena por /ag/version las apps que no reparto (solo las publicas); el catalogo trae Bot Lab 3.21.1 (flota de 32 bots)

## 1.3.1 — 2026-09-08

- iPad por la wifi sin instalar nada: dirección por el nombre del ordenador (.local), estable aunque cambie la IP; IPAD.md empieza por esa opción

## 1.3.0 — 2026-09-08

- iPad y móvil: todas las apps se instalan como app (manifest, icono y diseño táctil, inyectado por agcore en cualquier panel) y se abren a tus dispositivos con agc.py ipad (Tailscale o wifi), sin tocar ninguna barrera; guía de primeros pasos al crear la cuenta en cada app; IPAD.md

## 1.2.0 — 2026-09-08

- launcher público multiplataforma: modo amigo con código de invitación, instalación de Bot Lab (claves paper, buzón, flota), actualizaciones solo a etiquetas firmadas (Ed25519, lista de ficheros), Windows con tareas programadas y accesos directos, textos legales (términos, privacidad, licencia) y correcciones de la revisión de seguridad

## 1.0.0 — 2026-09-07

- Primera versión: biblioteca con el estado real de cada app (carpeta, entorno, servicios, app de escritorio, versión en marcha y en GitHub), instalar, actualizar, abrir, reiniciar, quitar, registro en vivo de cada tarea.

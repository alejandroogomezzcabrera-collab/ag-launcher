# Cambios de agcore

## 1.4.0 — 2026-09-10

- las tareas de Windows de Bot Lab se registran con pythonw.exe windows/tarea.py, no con .bat: un .bat abre una consola cada vez que corre la tarea

## 1.3.21 — 2026-09-10

- el catalogo apunta a Bot Lab 3.26.0

## 1.3.20 — 2026-09-10

- el catalogo apunta a Bot Lab 3.25.0

## 1.3.19 — 2026-09-10

- el catalogo apunta a Bot Lab 3.24.0

## 1.3.18 — 2026-09-10

- el catalogo apunta a Bot Lab 3.23.0 (flota de 2048 bots)

## 1.3.17 — 2026-09-10

- Catálogo Bot Lab 3.22.7: cotizaciones recientes, autopsias reforzadas y equipos ampliados

## 1.3.16 — 2026-09-09

- Catálogo Bot Lab 3.22.5: adaptación contextual y aprendizaje correcto de cortos

## 1.3.15 — 2026-09-09

- Catálogo Bot Lab 3.22.4: mejora del aprendizaje y validación más rápida

## 1.3.14 — 2026-09-09

- Catálogo actualizado a Bot Lab 3.22.3: ampliación inmediata a 256 bots y corrección del reinicio en Windows

## 1.3.13 — 2026-09-09

- el catalogo apunta a Bot Lab 3.22.0 (flota de 256 bots)

## 1.3.12 — 2026-09-09

- el catalogo apunta a Bot Lab 3.21.7 (flota de 128 bots)

## 1.3.11 — 2026-09-09

- el catalogo apunta a Bot Lab 3.21.6

## 1.3.10 — 2026-09-09

- el catalogo apunta a Bot Lab 3.21.5

## 1.3.9 — 2026-09-09

- el catalogo apunta a Bot Lab 3.21.4

## 1.3.8 — 2026-09-09

- la biblioteca avisa cuando una app corre una version distinta de la instalada (un panel arrancado hace dias sigue con su codigo); Bot Lab responde en /version

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

## 1.1.0 — 2026-09-07

- AG Launcher: la tienda del imperio (biblioteca con estado real, instalar, actualizar, abrir, reiniciar, quitar, registro en vivo) y motor agcore/tienda.py; catálogo con servicios, instalador y repo por app


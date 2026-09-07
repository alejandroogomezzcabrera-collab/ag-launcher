/* AG Launcher — interfaz. Biblioteca (todas las apps con su estado real), Actualizaciones, Acerca de.
   Las tareas (instalar/actualizar/quitar/reiniciar) corren en el panel; aquí se lee su registro en vivo. */
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const COLORES = {"ag-launcher": ["#1d2b4f", "#2c1a4f"], "shorts-factory": ["#4a1d2f", "#1d2b4f"], "llm-lab": ["#1d3a4f", "#2f1d4f"], "second-brain": ["#1a1f4f", "#0f3a3f"], "bot-lab": ["#1f3f2a", "#1d2b4f"]};
let D = null, UI = {pagina: localStorage.getItem("agl.pagina") || "biblioteca", menu: null, tarea: null, ultimo: ""};
const apps = () => (D && D.apps) || [];

async function GET(ruta) {const r = await fetch(ruta, {cache: "no-store"}); return r.json();}
async function accion(nombre, cuerpo = {}) {
  try {
    const r = await fetch(`/accion/${nombre}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(cuerpo)});
    const j = await r.json();
    if (!r.ok || j.ok === false) aviso(j.msg || j.error || "No se pudo", true); else if (j.msg) aviso(j.msg);
    if (j.tarea) seguirTarea(j.tarea);
    await refrescar(true);
    return j;
  } catch (e) {aviso("Sin conexión con el launcher", true); return null;}
}
function aviso(t, rojo) {const el = document.createElement("div"); el.className = "aviso" + (rojo ? " rojo" : ""); el.textContent = t; $("avisos").appendChild(el); setTimeout(() => el.remove(), 4000);}

// ── estado de una app → chips y botón principal ─────────────────────────────
function chips(a) {
  const c = [];
  if (!a.existe) c.push(["rojo", "sin carpeta"]);
  else if (a.instalada) c.push(["verde", "instalada"]);
  else c.push(["oro", "a medias"]);
  if (a.existe) c.push([a.vivo ? "verde" : "rojo", a.vivo ? "panel vivo" : "panel parado"]);
  const serv = Object.entries(a.servicios || {}); const ok = serv.filter(([, v]) => v).length;
  if (serv.length) c.push([ok === serv.length ? "azul" : "oro", `${ok}/${serv.length} servicios`]);
  if (a.existe) c.push([a.app ? "azul" : "oro", a.app ? "app en Aplicaciones" : "sin app de escritorio"]);
  if (a.actualizacion) c.push(["oro", "⬆ " + a.actualizacion]);
  return `<div class="chips">${c.map(([k, t]) => `<span class="chip ${k}"><i></i>${esc(t)}</span>`).join("")}</div>`;
}
function tareaDe(a) {return ((D && D.tareas) || []).find(t => t.app === a.id && !t.fin);}
function botones(a) {
  const t = tareaDe(a);
  if (t) return `<div style="flex:1"><div class="progreso"><i></i></div><div class="mono" style="margin-top:6px">${esc(t.accion)}… <a style="cursor:pointer;color:var(--azul)" onclick="seguirTarea('${esc(t.id)}')">ver registro</a></div></div>`;
  let principal;
  if (!a.existe || !a.instalada) principal = `<a class="boton primario" onclick="accion('instalar',{app:'${a.id}'})">⬇ Instalar</a>`;
  else if (a.actualizacion) principal = `<a class="boton verde" onclick="accion('actualizar',{app:'${a.id}'})">⬆ Actualizar</a>`;
  else principal = `<a class="boton primario" onclick="accion('abrir',{app:'${a.id}'})">▶ Abrir</a>`;
  const segundo = a.instalada && a.actualizacion ? `<a class="boton" onclick="accion('abrir',{app:'${a.id}'})">▶ Abrir</a>` : "";
  return `${principal}${segundo}<div class="mas"><a class="boton" onclick="event.stopPropagation();menu('${a.id}')">⋯</a>${UI.menu === a.id ? menuHtml(a) : ""}</div>`;
}
function menuHtml(a) {
  return `<div class="menu" onclick="event.stopPropagation()">
    ${a.existe && a.vivo ? `<a onclick="window.open('http://localhost:${a.puerto}/')">🌐 Abrir en el navegador</a>` : ""}
    ${a.existe ? `<a onclick="accion('actualizar',{app:'${a.id}'})">⬆ Actualizar / reinstalar</a>` : ""}
    ${a.existe && a.puerto ? `<a onclick="accion('reiniciar',{app:'${a.id}'})">↻ Reiniciar el panel</a>` : ""}
    ${a.existe ? `<a onclick="verRegistro('${a.id}')">📄 Ver registro</a><a onclick="accion('carpeta',{app:'${a.id}'})">📁 Abrir carpeta</a>` : ""}
    ${a.remoto ? `<a onclick="window.open('${esc(a.remoto.replace(/\\.git$/, ""))}')">🐙 Repositorio en GitHub</a>` : ""}
    ${a.instalada && !a.propia ? `<a class="rojo" onclick="if(confirm('¿Quitar ${esc(a.nombre)}? Se paran sus servicios y se borra la app de Aplicaciones. La carpeta y tus datos se quedan.'))accion('desinstalar',{app:'${a.id}'})">🗑 Quitar</a>` : ""}
  </div>`;
}
window.menu = id => {UI.menu = UI.menu === id ? null : id; pintar(true);};
document.addEventListener("click", () => {if (UI.menu) {UI.menu = null; pintar(true);}});

function tarjeta(a) {
  const [c1, c2] = COLORES[a.id] || ["#1b2a4a", "#2a1b4a"];
  return `<div class="tarjeta" style="--c1:${c1};--c2:${c2}"><div class="portada">${esc(a.icono)}<span class="ver">${a.version ? "v" + esc(a.version) : "—"}</span>${a.puerto ? `<span class="puerto">localhost:${a.puerto}</span>` : ""}</div>
    <div class="cuerpo"><h3>${esc(a.nombre)}</h3><div class="desc">${esc(a.descripcion)}</div>${chips(a)}<div class="acciones">${botones(a)}</div></div></div>`;
}

// ── páginas ─────────────────────────────────────────────────────────────────
const pendientes = () => apps().filter(a => a.actualizacion || (a.existe && !a.instalada));
function pagBiblioteca() {
  const inst = apps().filter(a => a.instalada), otras = apps().filter(a => !a.instalada);
  return `<div class="hero"><h1>Tu biblioteca</h1><p>Las apps y herramientas de AG Creations en este Mac. Todo corre en local: un panel siempre vivo por app, una app de escritorio y tus datos en su carpeta.</p>
    <div class="fila"><a class="boton" onclick="accion('comprobar')">🔎 Buscar actualizaciones</a>${pendientes().length ? `<a class="boton verde" onclick="actualizarTodo()">⬆ Actualizar todo (${pendientes().length})</a>` : ""}<span class="mono">${apps().length} apps · ${inst.length} instaladas · ${apps().filter(a => a.vivo).length} paneles vivos</span></div></div>
    ${inst.length ? `<div class="seccion"><h2>Instaladas</h2><div class="rejilla">${inst.map(tarjeta).join("")}</div></div>` : ""}
    ${otras.length ? `<div class="seccion"><h2>Disponibles</h2><div class="rejilla">${otras.map(tarjeta).join("")}</div></div>` : ""}`;
}
function pagActualizaciones() {
  const p = pendientes();
  return `<div class="hero"><h1>Actualizaciones</h1><p>Se comparan la versión de la carpeta, la que está corriendo en el panel, la app de escritorio y, si el proyecto está en GitHub, la última versión etiquetada.</p>
    <div class="fila"><a class="boton" onclick="accion('comprobar')">🔎 Comprobar ahora</a>${p.length ? `<a class="boton verde" onclick="actualizarTodo()">⬆ Actualizar todo</a>` : ""}</div></div>
    <div class="seccion">${p.length ? `<div class="rejilla">${p.map(tarjeta).join("")}</div>` : `<div class="caja vacio">✓ Todo al día. Nada que actualizar.</div>`}
    <h2>Versiones</h2><div class="caja" style="padding:4px 10px"><table class="tabla"><tr><th>app</th><th>carpeta</th><th>en marcha</th><th>GitHub</th><th>app escritorio</th><th>servicios</th></tr>
    ${apps().map(a => `<tr><td>${esc(a.icono)} <b>${esc(a.nombre)}</b><div class="mono">${esc(a.carpeta)}</div></td><td class="mono">${a.version ? "v" + a.version : "—"}</td><td class="mono">${a.version_viva ? "v" + a.version_viva : a.vivo ? "viva" : "parada"}</td><td class="mono">${a.etiqueta_remota || (a.remoto ? "sin etiquetas" : "solo local")}</td><td class="mono">${a.app ? (a.app_desactualizada ? "⚠ antigua" : "✓") : "—"}</td><td class="mono">${Object.entries(a.servicios || {}).map(([k, v]) => `${v ? "●" : "○"} ${k.replace("com.ag.", "")}`).join("<br>") || "—"}</td></tr>`).join("")}</table></div></div>`;
}
function pagAcerca() {
  return `<div class="hero"><h1>AG Creations</h1><p>Las apps y herramientas de Alejandro Gómez Cabrera. Todas funcionan en tu propio ordenador, sin servidores ni cuentas en internet, con una sola cuenta por dispositivo.</p></div>
    <div class="seccion"><div class="caja"><p><b>Núcleo común</b> agcore v${esc(D.agcore)} · <b>launcher</b> v${esc(D.launcher)}</p>
    <p class="mono">Catálogo: ~/ag-creations/catalogo.json · nueva app: python3 ~/ag-creations/agc.py nuevo &lt;id&gt; --nombre … --puerto … · subir versión: agc.py subir &lt;app&gt; patch -m "…"</p>
    <p style="color:var(--sub)">Instalar = entorno de Python + servicios de launchd + app en /Applications. Actualizar = git pull (si hay GitHub) + dependencias si cambiaron + reinicio del panel + reconstruir la app de escritorio. Quitar = parar servicios y borrar la app; la carpeta y los datos no se tocan.</p></div></div>`;
}
const PAGINAS = {biblioteca: pagBiblioteca, actualizaciones: pagActualizaciones, acerca: pagAcerca};
const NAV = [["biblioteca", "📚", "Biblioteca"], ["actualizaciones", "⬆", "Actualizaciones"], ["acerca", "🏛", "Acerca de"]];
function pintarLateral() {
  const n = pendientes().length;
  $("nav").innerHTML = NAV.map(([k, i, t]) => `<a class="${UI.pagina === k ? "on" : ""}" onclick="ir('${k}')"><span>${i}</span>${t}${k === "actualizaciones" && n ? `<span class="n">${n}</span>` : ""}</a>`).join("");
  $("lateral-pie").innerHTML = D ? `agcore v${esc(D.agcore)} · launcher v${esc(D.launcher)}<br>© AG Creations` : "";
}
window.ir = k => {UI.pagina = k; localStorage.setItem("agl.pagina", k); pintar(true);};
function pintar(forzar) {
  if (!D) return;
  pintarLateral();
  const clave = UI.pagina + JSON.stringify(D.apps) + JSON.stringify((D.tareas || []).map(t => [t.id, t.fin])) + UI.menu;
  if (!forzar && clave === UI.ultimo) return;
  UI.ultimo = clave;
  const scroll = $("principal").scrollTop;
  $("principal").innerHTML = (PAGINAS[UI.pagina] || pagBiblioteca)();
  $("principal").scrollTop = scroll;
}
window.actualizarTodo = async () => {for (const a of pendientes()) await accion(a.instalada ? "actualizar" : "instalar", {app: a.id});};

// ── consola de tareas ───────────────────────────────────────────────────────
window.seguirTarea = id => {UI.tarea = id; $("consola").classList.remove("oculta"); tickTarea();};
async function tickTarea() {
  if (!UI.tarea) return;
  try {
    const t = await GET(`/tarea?id=${encodeURIComponent(UI.tarea)}`);
    const a = apps().find(x => x.id === t.app) || {};
    $("consola-titulo").textContent = `${a.icono || ""} ${a.nombre || t.app} · ${t.accion}`;
    $("consola-estado").textContent = t.fin ? (t.ok ? "✓ terminada" : "✗ con errores") : "en marcha…";
    const c = $("consola-cuerpo"), abajo = c.scrollTop + c.clientHeight >= c.scrollHeight - 20;
    c.textContent = t.lineas.join("\n"); if (abajo) c.scrollTop = c.scrollHeight;
    if (!t.fin) setTimeout(tickTarea, 700); else refrescar(true);
  } catch (e) {}
}
window.verRegistro = async id => {const a = apps().find(x => x.id === id); UI.tarea = null; $("consola").classList.remove("oculta"); $("consola-titulo").textContent = `${a.icono} ${a.nombre} · registro`; $("consola-estado").textContent = "últimas líneas"; $("consola-cuerpo").textContent = await (await fetch(`/registro?app=${id}`)).text(); $("consola-cuerpo").scrollTop = 1e9;};
$("consola-cerrar").onclick = () => {$("consola").classList.add("oculta"); UI.tarea = null;};

async function refrescar(forzar) {try {D = await GET("/estado"); pintar(forzar);} catch (e) {console.warn(e);}}
AG.listo(() => {refrescar(true); setInterval(() => refrescar(false), 3000);});

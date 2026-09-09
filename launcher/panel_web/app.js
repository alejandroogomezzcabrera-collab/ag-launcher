/* AG Launcher — interfaz. Biblioteca (las apps con su estado real), Actualizaciones, Invitación, Acerca de.
   Las tareas (instalar/actualizar/sincronizar/quitar/reiniciar) corren en el panel; aquí se lee su registro en vivo.
   Modo amigo: solo las apps repartibles; las privadas piden el código de invitación. Los textos cambian según el
   sistema (D.so: mac | windows): app en Aplicaciones / acceso directo, servicios launchd / tareas programadas. */
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const COLORES = {"ag-launcher": ["#1d2b4f", "#2c1a4f"], "bot-lab": ["#1f3f2a", "#1d2b4f"]};
// Cualquier otra app (las del catálogo local del propietario) coge su pareja de colores de su
// propio id: así el catálogo público no nombra apps que no reparto.
const PALETA = [["#4a1d2f", "#1d2b4f"], ["#1d3a4f", "#2f1d4f"], ["#1a1f4f", "#0f3a3f"], ["#3f2a1d", "#1d2b4f"], ["#2a1d4f", "#1d3f3a"]];
const colorDe = (id) => COLORES[id] || PALETA[[...String(id)].reduce((n, c) => n + c.charCodeAt(0), 0) % PALETA.length];
let D = null, UI = {pagina: localStorage.getItem("agl.pagina") || "biblioteca", menu: null, tarea: null, ultimo: ""};
const apps = () => (D && D.apps) || [];
const WIN = () => D && D.so === "windows";
const AMIGO = () => D && D.modo === "amigo";
// textos por sistema
const T = () => WIN() ? {acceso: "acceso directo en el Menú Inicio", sinAcceso: "sin acceso directo", servicios: "tareas programadas",
                          instalar: "Instalar = entorno de Python + tareas programadas + acceso directo en el Menú Inicio y el Escritorio.",
                          quitar: "Se borran sus tareas programadas y su acceso directo. La carpeta y tus datos se quedan.", datos: "%LOCALAPPDATA%\\AG Creations\\apps", sistema: "este PC"}
                       : {acceso: "app en Aplicaciones", sinAcceso: "sin app de escritorio", servicios: "servicios",
                          instalar: "Instalar = entorno de Python + servicios de launchd + app en /Applications.",
                          quitar: "Se paran sus servicios y se borra la app de Aplicaciones. La carpeta y tus datos se quedan.", datos: "~/AG Creations", sistema: "este Mac"};

async function GET(ruta) {const r = await fetch(ruta, {cache: "no-store"}); return r.json();}
async function accion(nombre, cuerpo = {}) {
  try {
    const r = await fetch(`/accion/${nombre}`, {method: "POST", headers: {"Content-Type": "application/json", "X-AG": "1"}, body: JSON.stringify(cuerpo)});
    const j = await r.json();
    if (!r.ok || j.ok === false) aviso(j.msg || j.error || "No se pudo", true); else if (j.msg) aviso(j.msg);
    if (j.tarea) seguirTarea(j.tarea);
    await refrescar(true);
    return j;
  } catch (e) {aviso("Sin conexión con el launcher", true); return null;}
}
function aviso(t, rojo) {const el = document.createElement("div"); el.className = "aviso" + (rojo ? " rojo" : ""); el.textContent = t; $("avisos").appendChild(el); setTimeout(() => el.remove(), 5000);}

// ── estado de una app → chips y botón principal ─────────────────────────────
function chips(a) {
  const c = [], t = T();
  if (!a.existe) c.push(["rojo", a.privado && AMIGO() && !D.invitacion ? "necesita invitación" : "sin instalar"]);
  else if (a.instalada) c.push(["verde", "instalada"]);
  else c.push(["oro", "a medias"]);
  if (a.existe) c.push([a.vivo ? "verde" : "rojo", a.vivo ? "panel vivo" : "panel parado"]);
  // Un panel que lleva días arrancado sigue con el código que cargó: la actualización cambia el
  // disco, no el intérprete. Si lo que corre no es lo instalado, se dice (y «Reiniciar» lo cura).
  if (a.vivo && a.version_viva && a.version && a.version_viva !== a.version)
    c.push(["rojo", `corriendo v${a.version_viva}: reinicia el panel`]);
  const serv = Object.entries(a.servicios || {}); const ok = serv.filter(([, v]) => v).length;
  if (serv.length) c.push([ok === serv.length ? "azul" : "oro", `${ok}/${serv.length} ${t.servicios}`]);
  if (a.existe) c.push([a.app ? "azul" : "oro", a.app ? t.acceso : t.sinAcceso]);
  if (a.existe && a.receta === "bot-lab" && !a.extra) c.push(["oro", "faltan las claves (.env)"]);
  if (a.actualizacion) c.push(["oro", "⬆ " + a.actualizacion]);
  const p = a.puente_estado;
  if (p && p.baneada) c.push(["rojo", "instalación baneada"]);
  else if (p && p.strikes) c.push(["rojo", `${p.strikes} strike${p.strikes > 1 ? "s" : ""}`]);
  return `<div class="chips">${c.map(([k, t]) => `<span class="chip ${k}"><i></i>${esc(t)}</span>`).join("")}</div>`;
}
function tareaDe(a) {return ((D && D.tareas) || []).find(t => t.app === a.id && !t.fin);}
function botonInstalar(a) {
  if (a.privado && AMIGO() && !D.invitacion) return `<a class="boton primario" onclick="ir('invitacion')">🎟 Pega tu invitación</a>`;
  if (a.receta === "bot-lab" && !a.extra) return `<a class="boton primario" onclick="formularioBotLab('${a.id}')">⬇ Instalar</a>`;
  return `<a class="boton primario" onclick="accion('instalar',{app:'${a.id}'})">⬇ Instalar</a>`;
}
function botones(a) {
  const t = tareaDe(a);
  if (t) return `<div style="flex:1"><div class="progreso"><i></i></div><div class="mono" style="margin-top:6px">${esc(t.accion)}… <a style="cursor:pointer;color:var(--azul)" onclick="seguirTarea('${esc(t.id)}')">ver registro</a></div></div>`;
  let principal;
  if (!a.existe || !a.instalada) principal = botonInstalar(a);
  else if (a.actualizacion && !a.puente) principal = `<a class="boton verde" onclick="accion('actualizar',{app:'${a.id}'})">⬆ Actualizar</a>`;
  else principal = `<a class="boton primario" onclick="accion('abrir',{app:'${a.id}'})">▶ Abrir</a>`;
  const segundo = a.instalada && a.actualizacion && !a.puente ? `<a class="boton" onclick="accion('abrir',{app:'${a.id}'})">▶ Abrir</a>`
    : a.instalada && a.puente ? `<a class="boton" onclick="accion('sincronizar',{app:'${a.id}'})" title="puente_git.py --sincronizar">⇄ Sincronizar ahora</a>` : "";
  return `${principal}${segundo}<div class="mas"><a class="boton" onclick="event.stopPropagation();menu('${a.id}')">⋯</a>${UI.menu === a.id ? menuHtml(a) : ""}</div>`;
}
function menuHtml(a) {
  return `<div class="menu" onclick="event.stopPropagation()">
    ${a.existe && a.vivo ? `<a onclick="window.open('http://localhost:${a.puerto}/')">🌐 Abrir en el navegador</a>` : ""}
    ${a.existe && a.puente ? `<a onclick="accion('sincronizar',{app:'${a.id}'})">⇄ Sincronizar ahora (puente)</a>` : ""}
    ${a.existe && !a.puente ? `<a onclick="accion('actualizar',{app:'${a.id}'})">⬆ Actualizar / reinstalar</a>` : ""}
    ${a.existe && a.puente ? `<a onclick="accion('instalar',{app:'${a.id}'})">🔧 Reparar (${WIN() ? "tareas y acceso" : "servicios y app"})</a>` : ""}
    ${a.existe && a.puerto ? `<a onclick="accion('reiniciar',{app:'${a.id}'})">↻ Reiniciar el panel</a>` : ""}
    ${a.existe ? `<a onclick="verRegistro('${a.id}')">📄 Ver registro</a><a onclick="accion('carpeta',{app:'${a.id}'})">📁 Abrir carpeta</a>` : ""}
    ${a.repo && !a.privado ? `<a onclick="window.open('${esc(a.repo.replace(/\\.git$/, ""))}')">🐙 Repositorio en GitHub</a>` : ""}
    ${a.instalada && !a.propia ? `<a class="rojo" onclick="if(confirm('¿Quitar ${esc(a.nombre)}? ${esc(T().quitar)}'))accion('desinstalar',{app:'${a.id}'})">🗑 Quitar</a>` : ""}
  </div>`;
}
window.menu = id => {UI.menu = UI.menu === id ? null : id; pintar(true);};
document.addEventListener("click", () => {if (UI.menu) {UI.menu = null; pintar(true);}});

function puenteHtml(a) {
  const p = a.puente_estado;
  if (!p) return "";
  const f = [];
  if (p.nombre) f.push(`flota «${esc(p.nombre)}»`);
  if (p.instalado) f.push(`código ${esc(p.instalado)}`);
  if (p.codigo_pendiente) f.push(`⬆ v${esc(p.codigo_pendiente)} pendiente`);
  if (p.codigo_error) f.push(`⚠ ${esc(p.codigo_error)}`);
  if (p.ultimo) f.push(`sincronizado ${esc(String(p.ultimo).replace("T", " ").slice(0, 16))}`);
  if (p.buzon_ok != null) f.push(p.buzon_ok ? `buzón ok · ${p.flotas || 0} flotas` : "buzón sin conexión");
  if (p.baneada) f.push(`⛔ baneada${p.baneo_motivo ? ": " + esc(p.baneo_motivo) : ""}`);
  return `<div class="puente mono" title="lo que dice puente_git.py --estado">${f.join(" · ") || "puente sin datos aún"}</div>`;
}
function tarjeta(a) {
  const [c1, c2] = colorDe(a.id);
  return `<div class="tarjeta" style="--c1:${c1};--c2:${c2}"><div class="portada">${esc(a.icono)}<span class="ver">${a.version ? "v" + esc(a.version) : "—"}</span>${a.puerto ? `<span class="puerto">localhost:${a.puerto}</span>` : ""}${a.privado ? `<span class="privado">🔒 con invitación</span>` : ""}</div>
    <div class="cuerpo"><h3>${esc(a.nombre)}</h3><div class="desc">${esc(a.descripcion)}${a.requisitos && !a.existe ? `<div class="mono" style="margin-top:4px">necesita: ${esc(a.requisitos)}</div>` : ""}</div>${chips(a)}${a.puente && a.existe ? puenteHtml(a) : ""}<div class="acciones">${botones(a)}</div></div></div>`;
}

// ── formulario de Bot Lab (claves PAPER de Alpaca) ──────────────────────────
window.formularioBotLab = id => {
  const a = apps().find(x => x.id === id) || {nombre: "Bot Lab"};
  const nombre = D.invitacion ? `Flota de ${D.invitacion.amigo}` : "Mi flota";
  $("modal").innerHTML = `<div class="dialogo" onclick="event.stopPropagation()">
    <h2>🤖 Instalar ${esc(a.nombre)}</h2>
    <p class="sub">Bot Lab opera con <b>dinero ficticio</b> en una cuenta <i>Paper Trading</i> de Alpaca. Necesita tus claves de Paper para leer precios y simular operaciones.
    Entra en <a href="https://app.alpaca.markets" target="_blank" rel="noopener">app.alpaca.markets</a> → arriba a la izquierda cambia a <b>Paper Trading</b> → <b>API Keys</b> → <i>Generate New Keys</i>.</p>
    <label>Nombre de tu flota<input id="f-flota" maxlength="60" value="${esc(nombre)}"></label>
    <label>API Key (paper)<input id="f-key" type="password" autocomplete="off" spellcheck="false" placeholder="PK…"></label>
    <label>Secret Key (paper)<input id="f-secret" type="password" autocomplete="off" spellcheck="false"></label>
    <label class="check"><input id="f-ok" type="checkbox"> Entiendo que son claves de <b>dinero ficticio</b> (paper) y que se guardan solo en el fichero <span class="mono">.env</span> de Bot Lab en ${esc(T().sistema)}; el launcher no las envía a ningún sitio ni las muestra.</label>
    <p class="sub">La instalación descarga el código (con tu invitación), crea el entorno de Python (puede tardar varios minutos), comprueba las claves con Alpaca y deja ${WIN() ? "cuatro tareas programadas" : "tres servicios de launchd"} trabajando solos. Después Bot Lab se actualiza sola con su puente cada 10 minutos.</p>
    <div class="fila"><a class="boton primario" onclick="enviarBotLab('${esc(id)}')">⬇ Instalar Bot Lab</a><a class="boton" onclick="cerrarModal()">Cancelar</a></div></div>`;
  $("modal").classList.remove("oculta");
  setTimeout(() => $("f-key").focus(), 50);
};
window.cerrarModal = () => {$("modal").classList.add("oculta"); $("modal").innerHTML = "";};
window.enviarBotLab = async id => {
  const key = $("f-key").value.trim(), secret = $("f-secret").value.trim(), flota = $("f-flota").value.trim(), ok = $("f-ok").checked;
  if (!ok) return aviso("Marca la casilla: son claves de dinero ficticio", true);
  if (key.length < 8 || secret.length < 8) return aviso("Pega la API Key y la Secret Key de Paper Trading", true);
  cerrarModal();
  await accion("instalar", {app: id, alpaca_key: key, alpaca_secret: secret, flota, acepta_ficticio: true});
};
$("modal").addEventListener("click", () => cerrarModal());

// ── páginas ─────────────────────────────────────────────────────────────────
const pendientes = () => apps().filter(a => (a.actualizacion && !a.puente) || (a.existe && !a.instalada));
function avisoGit() {
  if (!D.sin_git) return "";
  return `<div class="caja aviso-git"><b>Falta Git.</b> Sin Git el launcher no puede descargar Bot Lab ni las actualizaciones firmadas (en Windows, sin Git, el launcher se actualiza descargando el ZIP de cada versión; Bot Lab sí necesita Git).
    ${WIN() ? `<a class="boton" onclick="accion('instalar_git',{app:'git'})">⬇ Instalar Git (winget)</a> <span class="mono">winget install --id Git.Git -e --source winget · o desde git-scm.com/download/win, todo por defecto</span>` : `<span class="mono">en el Terminal: xcode-select --install</span>`}</div>`;
}
function avisoInvitacion() {
  if (!AMIGO() || D.invitacion) return "";
  return `<div class="caja aviso-inv">🎟 <b>Aún no has pegado tu código de invitación.</b> Sin él no se pueden descargar las apps privadas (Bot Lab). <a class="boton peq" onclick="ir('invitacion')">Pegar la invitación</a></div>`;
}
function pagBiblioteca() {
  const inst = apps().filter(a => a.instalada), otras = apps().filter(a => !a.instalada);
  return `<div class="hero"><h1>Tu biblioteca</h1><p>Las apps de AG Creations en ${esc(T().sistema)}. Todo corre en local: un panel siempre vivo por app, ${WIN() ? "un acceso directo" : "una app de escritorio"} y tus datos en su carpeta.${D.invitacion ? ` Invitado como <b>${esc(D.invitacion.amigo)}</b>.` : ""}</p>
    <div class="fila"><a class="boton" onclick="accion('comprobar')">🔎 Buscar actualizaciones</a>${pendientes().length ? `<a class="boton verde" onclick="actualizarTodo()">⬆ Actualizar todo (${pendientes().length})</a>` : ""}<span class="mono">${apps().length} apps · ${inst.length} instaladas · ${apps().filter(a => a.vivo).length} paneles vivos</span></div></div>
    <div class="seccion">${avisoInvitacion()}${avisoGit()}</div>
    ${inst.length ? `<div class="seccion"><h2>Instaladas</h2><div class="rejilla">${inst.map(tarjeta).join("")}</div></div>` : ""}
    ${otras.length ? `<div class="seccion"><h2>Disponibles</h2><div class="rejilla">${otras.map(tarjeta).join("")}</div></div>` : ""}`;
}
function pagActualizaciones() {
  const p = pendientes();
  return `<div class="hero"><h1>Actualizaciones</h1><p>El launcher solo instala versiones <b>etiquetadas y firmadas</b> por el propietario (Ed25519); nunca el último cambio sin publicar. Bot Lab se actualiza sola con su puente cada 10 minutos: aquí solo puedes forzar «Sincronizar ahora».${D.firmas ? "" : " <b>Falta la librería cryptography: no se instalarán actualizaciones del launcher hasta instalarla (requirements.txt).</b>"}</p>
    <div class="fila"><a class="boton" onclick="accion('comprobar')">🔎 Comprobar ahora</a>${p.length ? `<a class="boton verde" onclick="actualizarTodo()">⬆ Actualizar todo</a>` : ""}</div></div>
    <div class="seccion">${p.length ? `<div class="rejilla">${p.map(tarjeta).join("")}</div>` : `<div class="caja vacio">✓ Todo al día. Nada que actualizar.</div>`}
    <h2>Versiones</h2><div class="caja" style="padding:4px 10px;overflow:auto"><table class="tabla"><tr><th>app</th><th>carpeta</th><th>en marcha</th><th>publicada</th><th>${esc(T().acceso)}</th><th>${esc(T().servicios)}</th></tr>
    ${apps().map(a => `<tr><td>${esc(a.icono)} <b>${esc(a.nombre)}</b><div class="mono">${esc(a.carpeta)}</div></td><td class="mono">${a.version ? "v" + a.version : "—"}</td><td class="mono">${a.version_viva ? "v" + a.version_viva : a.vivo ? "viva" : "parada"}</td><td class="mono">${a.puente ? (a.puente_estado && a.puente_estado.instalado ? esc(a.puente_estado.instalado) + " (puente)" : "puente") : (a.etiqueta_remota || (a.remoto ? "sin etiquetas" : "solo local"))}</td><td class="mono">${a.app ? (a.app_desactualizada ? "⚠ antigua" : "✓") : "—"}</td><td class="mono">${Object.entries(a.servicios || {}).map(([k, v]) => `${v ? "●" : "○"} ${esc(k.replace("com.ag.", "").replace("AG Creations\\", ""))}`).join("<br>") || "—"}</td></tr>`).join("")}</table></div></div>`;
}
function pagInvitacion() {
  const inv = D.invitacion;
  const estado = AMIGO() ? (inv ? `<div class="caja"><p>🎟 Invitado como <b>${esc(inv.amigo)}</b>${inv.creada ? ` · invitación creada el ${esc(String(inv.creada).replace("T", " ").slice(0, 16))}` : ""}.</p>
      <p class="sub">Con ella el launcher descarga las apps privadas y conecta Bot Lab a la flota. Si Alejandro te pasa otra (porque caducó o la renovó), pégala debajo y sustituye a la actual.</p>
      <a class="boton peligro peq" onclick="if(confirm('¿Quitar la invitación de este ordenador? Las apps ya instaladas siguen funcionando.'))accion('invitacion',{borrar:true})">Quitar la invitación</a></div>`
      : `<div class="caja"><p>Todavía no hay invitación en ${esc(T().sistema)}.</p></div>`)
    : `<div class="caja"><p>Este ordenador es del <b>propietario</b>: no necesita invitación. Los códigos para amigos se generan con <span class="mono">python3 agc.py invitar "Nombre"</span> (necesita secrets/token_codigo y secrets/token_buzon).</p></div>`;
  return `<div class="hero"><h1>Invitación</h1><p>Alejandro te pasa un <b>código de invitación</b> (un texto largo). Es tu llave para descargar las apps privadas: contiene un acceso de solo lectura al código de Bot Lab y otro al buzón de prodigios de la flota. Se guarda solo en ${esc(T().sistema)} y nunca aparece en los registros.</p></div>
    <div class="seccion">${estado}
    ${AMIGO() ? `<div class="caja" style="margin-top:14px"><label>Pega aquí el código<textarea id="inv-codigo" rows="4" spellcheck="false" placeholder="eyJ2IjoxLCJhbWlnbyI6…"></textarea></label>
      <div class="fila"><a class="boton primario" onclick="guardarInvitacion()">💾 Guardar la invitación</a></div></div>` : ""}</div>`;
}
window.guardarInvitacion = async () => {const c = $("inv-codigo").value.trim(); if (!c) return aviso("Pega el código", true); const j = await accion("invitacion", {codigo: c}); if (j && j.ok) ir("biblioteca");};
function pagAcerca() {
  const repo = D.repo ? D.repo.replace(/\.git$/, "") : "";
  return `<div class="hero"><h1>AG Creations</h1><p>Las apps y herramientas de Alejandro Gómez Cabrera. Todas funcionan en tu propio ordenador, sin servidores ni cuentas en internet, con una sola cuenta por dispositivo.</p></div>
    <div class="seccion"><div class="caja"><p><b>AG Launcher</b> v${esc(D.launcher)} · núcleo agcore v${esc(D.agcore)} · modo <b>${esc(D.modo)}</b> · ${WIN() ? "Windows" : "macOS"} · Python ${esc(D.python)}${D.firmas ? " · firmas ✓" : " · <span style='color:var(--oro)'>sin cryptography: no se instalan actualizaciones</span>"}</p>
    <p class="mono">carpeta del launcher: ${esc(D.raiz)} · apps nuevas en: ${esc(T().datos)} · cuenta y invitación en: ${WIN() ? "%APPDATA%\\AG Creations" : "~/Library/Application Support/AG Creations"}</p>
    ${repo ? `<p>🐙 Código y versiones: <a href="${esc(repo)}" target="_blank" rel="noopener">${esc(repo)}</a> (las descargas están en <i>Releases</i>).</p>` : ""}
    <p style="color:var(--sub)">${esc(T().instalar)} Actualizar = solo versiones etiquetadas y firmadas por el propietario${WIN() ? " (con Git, o descargando el ZIP de la versión y verificando cada fichero)" : ""} + dependencias si cambiaron + reinicio. Quitar = ${esc(T().quitar)}</p>
    <p style="color:var(--sub)">Bot Lab, en las instalaciones de amigos, comprueba en cada sincronización que su código es exactamente el firmado: si se altera, se restaura solo y cuenta un <i>strike</i>; al tercero la instalación queda baneada (deja de recibir código y de compartir; tus datos no se tocan).</p>
    <div class="fila"><a class="boton" onclick="accion('relanzar')">↻ Relanzar el launcher</a>${D.modo === "propietario" ? `<span class="mono">publicar: python3 agc.py publicar "qué cambia" [--minor] · invitar: agc.py invitar "Nombre"</span>` : ""}</div></div></div>`;
}
const PAGINAS = {biblioteca: pagBiblioteca, actualizaciones: pagActualizaciones, invitacion: pagInvitacion, acerca: pagAcerca};
const NAV = [["biblioteca", "📚", "Biblioteca"], ["actualizaciones", "⬆", "Actualizaciones"], ["invitacion", "🎟", "Invitación"], ["acerca", "🏛", "Acerca de"]];
function pintarLateral() {
  const n = pendientes().length, sinInv = AMIGO() && !D.invitacion;
  $("nav").innerHTML = NAV.map(([k, i, t]) => `<a class="${UI.pagina === k ? "on" : ""}" onclick="ir('${k}')"><span>${i}</span>${t}${k === "actualizaciones" && n ? `<span class="n">${n}</span>` : ""}${k === "invitacion" && sinInv ? `<span class="n">!</span>` : ""}</a>`).join("");
  $("lateral-pie").innerHTML = D ? `launcher v${esc(D.launcher)} · agcore v${esc(D.agcore)}<br>${esc(D.modo)} · ${WIN() ? "Windows" : "macOS"}<br>© AG Creations` : "";
}
window.ir = k => {UI.pagina = k; localStorage.setItem("agl.pagina", k); pintar(true);};
function pintar(forzar) {
  if (!D) return;
  pintarLateral();
  const clave = UI.pagina + JSON.stringify(D.apps) + JSON.stringify((D.tareas || []).map(t => [t.id, t.fin])) + UI.menu + JSON.stringify(D.invitacion) + D.sin_git;
  if (!forzar && clave === UI.ultimo) return;
  UI.ultimo = clave;
  const scroll = $("principal").scrollTop;
  $("principal").innerHTML = (PAGINAS[UI.pagina] || pagBiblioteca)();
  $("principal").scrollTop = scroll;
}
window.actualizarTodo = async () => {for (const a of pendientes()) {if (a.instalada) await accion("actualizar", {app: a.id}); else if (a.receta === "bot-lab" && !a.extra) formularioBotLab(a.id); else await accion("instalar", {app: a.id});}};

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

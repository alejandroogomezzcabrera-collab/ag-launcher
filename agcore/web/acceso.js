/* acceso.js — AG Creations: acceso, chip de cuenta y menú. Se carga ANTES del app.js de cada app.
   Uso en la app:   AG.listo(() => { ...arrancar la app... });
   Además: añade la cabecera X-AG a todos los POST (CSRF) y vuelve a pedir la contraseña si una
   petición devuelve 401 (sesión caducada). */
(function () {
  "use strict";
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const _fetch = window.fetch.bind(window);
  const AG = window.AG = {cuenta: null, app: null, _cb: [], _listo: false};

  window.fetch = function (u, o) {
    o = o || {};
    if ((o.method || "GET").toUpperCase() !== "GET") o.headers = Object.assign({}, o.headers || {}, {"X-AG": "1"});
    return _fetch(u, o).then(r => {
      if (r.status === 401 && AG._listo && !String(u).startsWith("/ag/")) {AG._listo = false; AG.cuenta = null; mostrar();}
      return r;
    });
  };
  AG.post = async (ruta, cuerpo) => {
    const r = await _fetch(ruta, {method: "POST", headers: {"Content-Type": "application/json", "X-AG": "1"}, body: JSON.stringify(cuerpo || {})});
    let d = {}; try {d = await r.json();} catch (e) {}
    if (!r.ok) {const e = new Error(d.error || ("error " + r.status)); e.codigo = r.status; e.datos = d; throw e;}
    return d;
  };
  AG.listo = cb => {AG._cb.push(cb); if (AG._listo) cb(AG.cuenta);};
  const hace = s => {if (!s) return ""; const m = Math.round((Date.now() - new Date(s)) / 60000); return m < 1 ? "ahora mismo" : m < 60 ? `hace ${m} min` : m < 1440 ? `hace ${Math.round(m / 60)} h` : `hace ${Math.round(m / 1440)} d`;};
  const ini = c => ((c.nombre[0] || "") + (c.apellido[0] || "")).toUpperCase();

  // ── markdown mínimo (términos) ──────────────────────────────────────────────
  function mdMin(src) {
    const inl = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\*([^*]+)\*/g, "<em>$1</em>");
    const out = [], L = src.split("\n"); let i = 0;
    while (i < L.length) {const l = L[i];
      if (l.startsWith("```")) {const b = []; i++; while (i < L.length && !L[i].startsWith("```")) b.push(L[i++]); i++; out.push(`<pre><code>${esc(b.join("\n"))}</code></pre>`); continue;}
      if (/^#{1,3} /.test(l)) {const n = l.match(/^#+/)[0].length; out.push(`<h${n}>${inl(l.slice(n + 1))}</h${n}>`); i++; continue;}
      if (/^\s*[-*] /.test(l)) {const it = []; while (i < L.length && /^\s*[-*] /.test(L[i])) {let t = L[i++].replace(/^\s*[-*] /, ""); while (i < L.length && /^\s{2,}\S/.test(L[i]) && !/^\s*[-*] /.test(L[i])) t += " " + L[i++].trim(); it.push(t);} out.push(`<ul>${it.map(x => `<li>${inl(x)}</li>`).join("")}</ul>`); continue;}
      if (/^\s*\d+\. /.test(l)) {const it = []; while (i < L.length && /^\s*\d+\. /.test(L[i])) it.push(L[i++].replace(/^\s*\d+\. /, "")); out.push(`<ol>${it.map(x => `<li>${inl(x)}</li>`).join("")}</ol>`); continue;}
      if (l.startsWith("|")) {const f = []; while (i < L.length && L[i].startsWith("|")) f.push(L[i++]); const c = x => x.split("|").slice(1, -1).map(y => y.trim()); out.push(`<table><tr>${c(f[0]).map(x => `<th>${inl(x)}</th>`).join("")}</tr>${f.slice(2).map(r => `<tr>${c(r).map(x => `<td>${inl(x)}</td>`).join("")}</tr>`).join("")}</table>`); continue;}
      if (l.startsWith(">")) {out.push(`<blockquote>${inl(l.replace(/^> ?/, ""))}</blockquote>`); i++; continue;}
      if (!l.trim()) {i++; continue;}
      const b = []; while (i < L.length && L[i].trim() && !/^(#|```|\||\s*[-*] |\s*\d+\. |>)/.test(L[i])) b.push(L[i++]); out.push(`<p>${inl(b.join(" "))}</p>`);}
    return out.join("");
  }

  // ── pantalla de acceso ──────────────────────────────────────────────────────
  const S = {cuentas: [], sel: null, modo: "entrar", error: "", ocupado: false, terminos: false};
  function capa() {let c = $("#ag-acceso"); if (!c) {c = document.createElement("div"); c.id = "ag-acceso"; document.body.appendChild(c);} return c;}
  function pintar() {
    const a = AG.app || {}, crear = S.modo === "crear" || !S.cuentas.length, sel = S.cuentas.find(c => c.id === S.sel) || S.cuentas[0];
    const yaAcepto = sel && sel.terminos && sel.terminos[a.app] === a.terminos;
    const checkTerminos = `<label class="ag-check"><input type="checkbox" name="acepta" required><span>He leído y acepto los <a onclick="AG.verTerminos()">términos de ${esc(a.nombre || "esta app")}</a>: cortos, claros y sin trampas</span></label>`;
    capa().innerHTML = `<div class="ag-caja">
      <div class="ag-marca"><span class="ico">${esc(a.icono || "🧩")}</span><div><small>AG Creations</small><b>${esc(a.nombre || "")}</b></div></div>
      ${crear ? `<h2>${S.cuentas.length ? "Crear otra cuenta" : "Crea tu cuenta"}</h2><div class="ag-sub">Una cuenta para todas las apps de AG Creations en este dispositivo. No hay servidor: nada sale de aquí.</div>`
              : `<h2>Bienvenido de nuevo${sel ? ", " + esc(sel.nombre) : ""} 👋</h2><div class="ag-sub">${S.cuentas.length > 1 ? "Elige tu cuenta y escribe la contraseña." : "Escribe tu contraseña para entrar."}</div>`}
      <form id="ag-form" autocomplete="off">
      ${crear ? `<label>Nombre</label><input type="text" name="nombre" required maxlength="40" autofocus>
                 <label>Apellido</label><input type="text" name="apellido" required maxlength="40">
                 <label>Contraseña (mínimo 8 caracteres)</label><input type="password" name="contrasena" required minlength="8" maxlength="200">
                 <label>Repite la contraseña</label><input type="password" name="contrasena2" required minlength="8" maxlength="200">
                 ${checkTerminos}`
              : `<div class="ag-cuentas">${S.cuentas.map(c => `<button type="button" class="ag-cuenta ${c.id === sel.id ? "on" : ""}" onclick="AG._sel('${esc(c.id)}')"><span class="ag-ava">${esc(ini(c))}</span><span><b>${esc(c.nombre)} ${esc(c.apellido)}</b><small>${c.ultima && c.ultima[a.app] ? "última vez aquí " + hace(c.ultima[a.app]) : c.creada ? "cuenta creada " + hace(c.creada) + (Object.keys(c.ultima || {}).length ? " · usada en otras apps" : "") : ""}</small></span></button>`).join("")}</div>
                 <input type="hidden" name="id" value="${esc(sel.id)}">
                 <label>Contraseña</label><input type="password" name="contrasena" required maxlength="200" autofocus>
                 ${yaAcepto ? "" : `<div class="ag-sub" style="margin-top:10px">Es tu primera vez en ${esc(a.nombre)} con esta cuenta (o sus términos han cambiado).</div>${checkTerminos}`}`}
      <div class="ag-error">${esc(S.error)}</div>
      <button class="ag-boton" ${S.ocupado ? "disabled" : ""}>${S.ocupado ? "…" : crear ? "Crear cuenta y entrar" : "Entrar"}</button>
      </form>
      <div class="ag-links">${crear && S.cuentas.length ? `<a onclick="AG._modo('entrar')">← ya tengo cuenta</a>` : !crear ? `<a onclick="AG._modo('crear')">crear otra cuenta</a>` : "<span></span>"}<a onclick="AG.verTerminos()">Términos</a></div>
      <div class="ag-pie"><span><b>${esc(a.nombre || "")}</b> v${esc(a.version || "?")}</span><span>© AG Creations · tus datos se quedan en este dispositivo</span></div>
    </div>`;
    const f = $("#ag-form"); f.onsubmit = enviar;
    const foco = f.querySelector("[autofocus]"); if (foco) foco.focus();
  }
  AG._sel = id => {S.sel = id; S.error = ""; pintar();};
  AG._modo = m => {S.modo = m; S.error = ""; pintar();};
  async function enviar(ev) {
    ev.preventDefault();
    const f = new FormData(ev.target), crear = S.modo === "crear" || !S.cuentas.length;
    S.error = ""; S.ocupado = true; pintar();
    try {
      let d;
      if (crear) {
        if (f.get("contrasena") !== f.get("contrasena2")) throw new Error("las dos contraseñas no coinciden");
        d = await AG.post("/ag/auth/crear", {nombre: f.get("nombre"), apellido: f.get("apellido"), contrasena: f.get("contrasena"), acepta_terminos: !!f.get("acepta")});
      } else {
        d = await AG.post("/ag/auth/entrar", {id: f.get("id"), contrasena: f.get("contrasena"), acepta_terminos: !!f.get("acepta")});
      }
      entrar(d.cuenta);
    } catch (e) {
      S.ocupado = false;
      if (e.codigo === 428) {S.error = "tienes que aceptar los términos de esta app para entrar"; if (e.datos && e.datos.cuenta) {const c = S.cuentas.find(x => x.id === e.datos.cuenta.id); if (c) c.terminos = e.datos.cuenta.terminos;}}
      else S.error = e.message;
      pintar();
    }
    return false;
  }
  function entrar(cuenta) {
    AG.cuenta = cuenta; S.ocupado = false;
    const c = $("#ag-acceso"); if (c) c.remove();
    pintarChip();
    if (!AG._listo) {AG._listo = true; AG._cb.forEach(cb => {try {cb(cuenta);} catch (e) {console.error(e);}});}
  }
  async function mostrar() {
    try {const d = await (await _fetch("/ag/cuentas", {cache: "no-store"})).json(); S.cuentas = d.cuentas || []; AG.app = d.app;} catch (e) {S.cuentas = [];}
    S.cuentas.sort((a, b) => String((b.ultima || {})[AG.app && AG.app.app] || b.creada || "").localeCompare(String((a.ultima || {})[AG.app && AG.app.app] || a.creada || "")));
    S.sel = S.cuentas.length ? S.cuentas[0].id : null; S.modo = S.cuentas.length ? "entrar" : "crear"; S.error = "";
    pintar();
  }

  // ── chip y menú ─────────────────────────────────────────────────────────────
  function pintarChip() {
    let ch = $("#ag-chip"); if (!ch) {ch = document.createElement("div"); ch.id = "ag-chip"; document.body.appendChild(ch);}
    ch.innerHTML = `<span class="ag-ava">${esc(ini(AG.cuenta))}</span><b>${esc(AG.cuenta.nombre)}</b><small>▾</small>`;
    ch.title = `cuenta AG Creations de este dispositivo: ${AG.cuenta.nombre} ${AG.cuenta.apellido}`;
    ch.onclick = ev => {ev.stopPropagation(); menu();};
  }
  function menu() {
    if ($("#ag-menu")) {$("#ag-menu").remove(); return;}
    const a = AG.app || {}, c = AG.cuenta;
    const m = document.createElement("div"); m.id = "ag-menu";
    m.innerHTML = `<div class="ag-cab"><span class="ag-ava">${esc(ini(c))}</span><div><b>${esc(c.nombre)} ${esc(c.apellido)}</b><small>cuenta local · ${esc(a.nombre)} v${esc(a.version)}</small></div></div>
      <a class="it" onclick="AG.verTerminos()">📜 Términos de ${esc(a.nombre)}</a>
      <a class="it" onclick="AG.cambiarContrasena()">🔑 Cambiar contraseña</a>
      <a class="it" onclick="AG.acerca()">ℹ️ Acerca de · AG Creations</a>
      <div class="ag-apps">Apps de AG Creations en este equipo</div>
      ${(a.catalogo || []).map(x => `<a class="app ${x.id === a.app ? "esta" : ""}" ${x.puerto && x.id !== a.app ? `href="http://localhost:${x.puerto}/" target="_blank"` : ""}><span>${esc(x.icono)} ${esc(x.nombre)}</span><small>v${esc(x.version)}</small></a>`).join("")}
      <a class="it rojo" onclick="AG.salir()">Salir de la cuenta</a>`;
    document.body.appendChild(m);
    setTimeout(() => document.addEventListener("click", function h(ev) {if (!m.contains(ev.target)) {m.remove(); document.removeEventListener("click", h);}}), 0);
  }
  function modal(html, peq) {
    const v = $("#ag-modal"); if (v) v.remove();
    const m = document.createElement("div"); m.id = "ag-modal";
    m.innerHTML = `<div class="ag-hoja ${peq ? "peq" : ""}">${html}</div>`;
    m.onclick = ev => {if (ev.target === m) m.remove();};
    document.body.appendChild(m);
    return m;
  }
  AG.cerrarModal = () => {const v = $("#ag-modal"); if (v) v.remove();};
  AG.verTerminos = async () => {
    let md; try {md = await (await _fetch("/ag/terminos", {cache: "no-store"})).text();} catch (e) {md = "# Términos\n\nNo pude cargar TERMINOS.md";}
    modal(`<div class="ag-cab"><b>Términos de uso</b><a class="ag-cerrar" onclick="AG.cerrarModal()">✕</a></div><div class="ag-md">${mdMin(md)}</div><div class="ag-firma">© AG Creations · todas las apps pertenecen a AG Creations (Alejandro Gómez Cabrera)</div>`);
  };
  AG.cambiarContrasena = () => {
    const m = modal(`<div class="ag-cab"><b>Cambiar contraseña</b><a class="ag-cerrar" onclick="AG.cerrarModal()">✕</a></div>
      <form id="ag-pw"><label>Contraseña actual</label><input type="password" name="actual" required><label>Contraseña nueva (mínimo 8)</label><input type="password" name="nueva" required minlength="8"><label>Repite la nueva</label><input type="password" name="nueva2" required minlength="8">
      <div class="ag-error"></div><button class="ag-boton">Cambiar</button></form>
      <p style="color:#6b7686;font-size:11.5px;margin-top:10px">Vale para todas las apps de AG Creations en este dispositivo. Se cierran las sesiones abiertas.</p>`, true);
    m.querySelector("#ag-pw").onsubmit = async ev => {ev.preventDefault(); const f = new FormData(ev.target), err = m.querySelector(".ag-error");
      try {if (f.get("nueva") !== f.get("nueva2")) throw new Error("las dos contraseñas nuevas no coinciden"); await AG.post("/ag/auth/contrasena", {actual: f.get("actual"), nueva: f.get("nueva")}); location.reload();} catch (e) {err.textContent = e.message;} return false;};
  };
  AG.acerca = () => {
    const a = AG.app || {};
    modal(`<div class="ag-cab"><b>AG Creations</b><a class="ag-cerrar" onclick="AG.cerrarModal()">✕</a></div>
      <p style="color:#93a0b4">Las apps y herramientas de Alejandro Gómez Cabrera. Todas funcionan en tu propio ordenador, sin servidores ni cuentas en internet. Núcleo común agcore v${esc(a.agcore)}.</p>
      <div class="ag-acerca">${(a.catalogo || []).map(x => `<div class="fila"><span>${esc(x.icono)} <b>${esc(x.nombre)}</b> <span style="color:#6b7686">· ${esc(x.descripcion || "")}</span></span><small>v${esc(x.version)}${x.puerto ? " · :" + x.puerto : ""}</small></div>`).join("")}</div>
      <div class="ag-firma">© AG Creations · ${new Date().getFullYear()}</div>`);
  };
  AG.salir = async () => {try {await AG.post("/ag/auth/salir");} catch (e) {} location.reload();};

  // ── arranque ────────────────────────────────────────────────────────────────
  async function arrancar() {
    try {
      const r = await _fetch("/ag/yo", {cache: "no-store"});
      if (r.ok) {
        const d = await r.json();
        try {AG.app = await (await _fetch("/ag/version", {cache: "no-store"})).json();} catch (e) {}
        if (d.terminos_pendientes) {
          let md; try {md = await (await _fetch("/ag/terminos", {cache: "no-store"})).text();} catch (e) {md = "";}
          const m = modal(`<div class="ag-cab"><b>Los términos de ${esc((AG.app || {}).nombre || "esta app")} han cambiado</b></div><div class="ag-md" style="max-height:55vh;overflow:auto">${mdMin(md)}</div>
            <button class="ag-boton" id="ag-ok">Los he leído y los acepto</button> <button class="ag-boton sec" onclick="AG.salir()">Salir</button>`);
          m.onclick = null;
          m.querySelector("#ag-ok").onclick = async () => {await AG.post("/ag/auth/aceptar"); m.remove(); entrar(d.cuenta);};
          return;
        }
        entrar(d.cuenta); return;
      }
    } catch (e) {}
    mostrar();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arrancar); else arrancar();
})();

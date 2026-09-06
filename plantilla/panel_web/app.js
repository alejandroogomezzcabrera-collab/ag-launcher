/* __NOMBRE__ — interfaz. Arranca cuando la cuenta AG Creations tiene la sesión abierta (AG.listo). */
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const toast = t => {const el = document.createElement("div"); el.className = "toast"; el.textContent = t; document.body.appendChild(el); setTimeout(() => el.remove(), 3000);};
let D = null;

async function accion(nombre, cuerpo = {}) {
  const r = await fetch(`/accion/${nombre}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(cuerpo)});
  const j = await r.json(); toast(j.msg || (j.ok ? "hecho" : "no se pudo")); await refrescar(); return j;
}
function pintar() {
  $("principal").innerHTML = `<div class="caja"><h2>Hola, ${esc(AG.cuenta.nombre)}</h2><p>${esc(D.mensaje)}</p>
    <p>Contador: <b>${D.contador}</b> <a class="boton primario" onclick="accion('contar')">+1</a></p></div>
    <div class="caja"><p style="color:var(--sub)">Edita <code>panel_web/app.js</code> (interfaz), <code>panel.py</code> (datos y acciones) y <code>TERMINOS.md</code>. La cuenta, la seguridad y el menú de abajo a la derecha los pone agcore.</p></div>`;
}
async function refrescar() {
  try {D = await (await fetch("/estado", {cache: "no-store"})).json(); pintar();} catch (e) {console.warn(e);}
}
AG.listo(() => {refrescar(); setInterval(refrescar, 3000);});

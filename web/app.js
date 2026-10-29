"use strict";

const SYS_COLORS = { ps2: "#4c7dff", psp: "#a78bfa", ps3: "#ff4d6d", ps4: "#22b8ff", ps1: "#9aa3b5",
  nes: "#e4002b", n64: "#2fbf71", gba: "#7c4dff", nds: "#e0e4ee", gc: "#8a6bff", wii: "#3fc6ff" };
// logos à fond plein : affichés dans leurs couleurs d'origine plutôt qu'en silhouette blanche
const COLOR_LOGOS = new Set(["nes", "gba"]);
const SORTS = [
  { id: "az", label: "A → Z", fn: (a, b) => a.title.localeCompare(b.title, "fr") },
  { id: "recent", label: "Joués récemment", fn: (a, b) => (b.last_played || 0) - (a.last_played || 0) || a.title.localeCompare(b.title, "fr") },
  { id: "added", label: "Ajoutés récemment", fn: (a, b) => (b.added || 0) - (a.added || 0) },
];

const $ = (s) => document.querySelector(s);
const state = {
  games: [], systems: [], view: "all", sort: 0, query: "",
  zone: "grid", gi: 0, ni: 0, running: null, sig: "",
};
try { state.sort = +localStorage.getItem("formula.sort") || 0; state.view = localStorage.getItem("formula.view") || "all"; } catch (e) {}

const color = (sys) => SYS_COLORS[sys] || "#8b6cff";
const sysShort = (id) => (state.systems.find((s) => s.id === id) || {}).short || id.toUpperCase();
const coverUrl = (g) => (g.cover ? "/covers/" + g.cover : g.icon ? "/covers/" + g.icon : null);

// ------------------------------------------------------------ données
async function load() {
  try {
    const r = await fetch("/api/library", { cache: "no-store" });
    const d = await r.json();
    const sig = JSON.stringify([d.games.map((g) => [g.id, g.cover, g.fav, g.title]), d.systems.length]);
    state.systems = d.systems.sort((a, b) => a.order - b.order);
    setRunning(d.running);
    $("#status").classList.toggle("hidden", !d.scanning);
    $("#status").textContent = "Analyse de la bibliothèque…";
    if (sig !== state.sig) {
      const cur = visible()[state.gi];
      state.games = d.games;
      state.sig = sig;
      render(cur && cur.id);
    }
  } catch (e) { /* serveur en train de démarrer */ }
}

function visible() {
  let list = state.games.slice();
  if (state.view === "fav") list = list.filter((g) => g.fav);
  else if (state.view === "recent") list = list.filter((g) => g.last_played);
  else if (state.view !== "all") list = list.filter((g) => g.system === state.view);
  const q = state.query.trim().toLowerCase();
  if (q) list = list.filter((g) => g.title.toLowerCase().includes(q) || (g.serial || "").toLowerCase().includes(q));
  const sort = state.view === "recent" ? SORTS[1] : SORTS[state.sort];
  return list.sort(sort.fn);
}

// ------------------------------------------------------------ rendu
function navItems() {
  const count = (f) => state.games.filter(f).length;
  const items = [
    { id: "all", icon: "▦", label: "Bibliothèque", n: state.games.length },
    { id: "recent", icon: "◷", label: "Récents", n: count((g) => g.last_played) },
    { id: "fav", icon: "★", label: "Favoris", n: count((g) => g.fav) },
    { label: "Consoles" },
  ];
  for (const s of state.systems) items.push({ id: s.id, sys: s.short, label: s.name, n: count((g) => g.system === s.id) });
  return items;
}

function render(keepId) {
  const nav = $("#nav");
  nav.innerHTML = "";
  for (const it of navItems()) {
    if (!it.id) { nav.insertAdjacentHTML("beforeend", `<div class="nav-label">${it.label}</div>`); continue; }
    const b = document.createElement("button");
    b.className = "nav-item" + (state.view === it.id ? " active" : "");
    b.dataset.view = it.id;
    if (it.sys) b.style.setProperty("--c", color(it.id));
    if (it.sys) {
      // logo officiel de la console (web/logos/<id>.webp), sinon pastille texte
      b.title = it.label;
      b.classList.add("console");
      b.innerHTML = `<span class="logo-box${COLOR_LOGOS.has(it.id) ? " color" : ""}"><img src="logos/${it.id}.webp" alt="${esc(it.label)}"></span><em class="count">${it.n}</em>`;
      b.querySelector("img").onerror = (e) => { e.target.parentNode.outerHTML = `<em class="sys">${it.sys}</em><span>${esc(it.label)}</span>`; };
    } else {
      b.innerHTML = `<i>${it.icon}</i><span>${esc(it.label)}</span><em class="count">${it.n}</em>`;
    }
    b.onclick = () => setView(it.id);
    nav.appendChild(b);
  }
  $("#sort").textContent = "⇅ " + SORTS[state.sort].label;

  const list = visible();
  const titles = { all: "Tous les jeux", recent: "Joués récemment", fav: "Favoris" };
  const sysObj = state.systems.find((s) => s.id === state.view);
  $("#section-title").textContent = titles[state.view] || (sysObj ? sysObj.name : "");
  $("#count").textContent = list.length + (list.length > 1 ? " jeux" : " jeu");

  const grid = $("#grid");
  grid.innerHTML = "";
  list.forEach((g, i) => {
    const c = document.createElement("div");
    c.className = "card";
    c.dataset.i = i;
    c.style.setProperty("--c", color(g.system));
    const url = coverUrl(g);
    c.innerHTML = `<div class="art">
        <div class="ph"><b>${esc(g.title)}</b><small>${sysShort(g.system)}</small></div>
        ${url ? `<img loading="lazy" alt="" src="${url}">` : ""}
        <span class="badge">${sysShort(g.system)}</span>${g.fav ? '<span class="star">★</span>' : ""}
        <div class="shine"></div></div>
      <div class="name">${esc(g.title)}</div>`;
    const img = c.querySelector("img");
    if (img) {
      const ok = () => { img.classList.add("ok"); if (g.cover) c.querySelector(".ph").style.visibility = "hidden"; };
      if (img.complete && img.naturalWidth) ok(); else img.onload = ok;
      img.onerror = () => img.remove();
    }
    c.addEventListener("mousemove", () => { if (state.gi !== i || state.zone !== "grid") focusGrid(i, false); });
    c.addEventListener("click", () => {
      if (state.gi === i && state.zone === "grid" && lastPointer === "touch") return launch();
      focusGrid(i, false);
    });
    c.addEventListener("dblclick", () => launch());
    grid.appendChild(c);
  });
  $("#empty").classList.toggle("hidden", list.length > 0);
  grid.classList.toggle("hidden", list.length === 0);

  let gi = keepId ? list.findIndex((g) => g.id === keepId) : -1;
  if (gi < 0) gi = Math.min(state.gi, list.length - 1);
  state.gi = Math.max(0, gi);
  applyFocus(false);
}

function updateHero() {
  const g = visible()[state.gi];
  const art = $("#bg-art");
  $("#play").disabled = !g;
  $("#fav").disabled = !g;
  if (!g) {
    $("#hero-title").textContent = state.games.length ? "Aucun résultat" : "Bienvenue sur FORMULA";
    $("#hero-tags").innerHTML = "";
    $("#hero-meta").textContent = state.games.length ? "" : "Ajoute des jeux dans ~/Emulation/roms pour remplir ta bibliothèque.";
    $("#hero-cover").style.backgroundImage = "";
    art.classList.remove("on");
    return;
  }
  const url = coverUrl(g);
  $("#hero-title").textContent = g.title;
  $("#hero-tags").innerHTML = `<span class="tag sys" style="--c:${color(g.system)}">${sysShort(g.system)}</span>` +
    (g.region ? `<span class="tag">${esc(g.region)}</span>` : "");
  const meta = [];
  if (g.serial) meta.push(g.serial);
  if (g.plays) meta.push(`Lancé ${g.plays} fois`);
  if (g.last_played) meta.push("Dernière partie " + ago(g.last_played));
  if (g.size) meta.push((g.size / 1e9).toFixed(1).replace(".", ",") + " Go");
  $("#hero-meta").innerHTML = meta.map((m) => `<span>${esc(m)}</span>`).join("");
  $("#hero-cover").style.backgroundImage = url ? `url("${url}")` : "";
  const bg = g.hero ? "/covers/" + g.hero : url;
  art.style.backgroundImage = bg ? `url("${bg}")` : "";
  art.classList.toggle("on", !!bg);
  $("#fav").classList.toggle("on", !!g.fav);
  $("#fav").textContent = g.fav ? "★ Favori" : "☆ Favori";
  document.documentElement.style.setProperty("--a1", color(g.system));
}

// ------------------------------------------------------------ focus / navigation
function applyFocus(scroll = true) {
  document.querySelectorAll(".card.focus, .nav-item.focus").forEach((e) => e.classList.remove("focus"));
  if (state.zone === "grid") {
    const c = $(`.card[data-i="${state.gi}"]`);
    if (c) {
      c.classList.add("focus");
      if (scroll) c.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  } else {
    const items = railItems();
    state.ni = Math.max(0, Math.min(state.ni, items.length - 1));
    items[state.ni] && items[state.ni].classList.add("focus");
  }
  updateHero();
}
function focusGrid(i, scroll = true) { state.zone = "grid"; state.gi = i; applyFocus(scroll); }
const railItems = () => [...document.querySelectorAll("#rail .nav-item")];

function columns() {
  const cards = document.querySelectorAll(".card");
  if (cards.length < 2) return 1;
  const top = cards[0].offsetTop;
  let n = 0;
  for (const c of cards) { if (c.offsetTop !== top) break; n++; }
  return n;
}

function move(dx, dy) {
  if (state.zone === "rail") {
    if (dx > 0) { state.zone = "grid"; return applyFocus(); }
    state.ni += dy;
    return applyFocus();
  }
  const n = visible().length;
  if (!n) { if (dx < 0) { state.zone = "rail"; state.ni = railItems().findIndex((e) => e.classList.contains("active")); applyFocus(); } return; }
  const cols = columns();
  let i = state.gi;
  if (dx < 0 && i % cols === 0) {
    state.zone = "rail";
    state.ni = Math.max(0, railItems().findIndex((e) => e.classList.contains("active")));
    return applyFocus();
  }
  if (dx) i += dx;
  if (dy) i += dy * cols;
  if (i < 0 || i >= n) {
    if (dy > 0 && Math.floor(state.gi / cols) < Math.floor((n - 1) / cols)) i = n - 1; else return;
  }
  focusGrid(i);
}

function activate() {
  if (state.zone === "rail") { railItems()[state.ni]?.click(); return; }
  launch();
}

function back() {
  if (document.activeElement === $("#search")) { $("#search").blur(); return; }
  if (state.query) { state.query = ""; $("#search").value = ""; render(); return; }
  if (state.zone === "grid") { state.zone = "rail"; state.ni = Math.max(0, railItems().findIndex((e) => e.classList.contains("active"))); applyFocus(); }
}

function setView(v) {
  state.view = v;
  state.gi = 0;
  try { localStorage.setItem("formula.view", v); } catch (e) {}
  render();
  $("#grid").scrollTop = 0;
}
function cycleView(d) {
  const ids = navItems().filter((i) => i.id).map((i) => i.id);
  setView(ids[(ids.indexOf(state.view) + d + ids.length) % ids.length]);
  state.zone = "grid";
  applyFocus();
}
function cycleSort() {
  state.sort = (state.sort + 1) % SORTS.length;
  try { localStorage.setItem("formula.sort", state.sort); } catch (e) {}
  const cur = visible()[state.gi];
  render(cur && cur.id);
  toast("Tri : " + SORTS[state.sort].label);
}

// ------------------------------------------------------------ actions
async function launch() {
  const g = visible()[state.gi];
  if (!g || state.running) return;
  const c = $(`.card[data-i="${state.gi}"]`);
  if (c) { c.classList.remove("launch"); void c.offsetWidth; c.classList.add("launch"); }
  const r = await fetch("/api/launch", { method: "POST", body: JSON.stringify({ id: g.id }) });
  const d = await r.json();
  if (!d.ok) return toast(d.message || "Lancement impossible");
  setRunning(g.id);
}

async function toggleFav() {
  const g = visible()[state.gi];
  if (!g) return;
  await fetch("/api/fav", { method: "POST", body: JSON.stringify({ id: g.id }) });
  g.fav = !g.fav;
  state.sig = "";
  load();
}

function setRunning(id) {
  state.running = id;
  const g = id && state.games.find((x) => x.id === id);
  $("#running").classList.toggle("hidden", !id);
  if (g) {
    $("#run-title").textContent = g.title;
    const url = coverUrl(g);
    $("#run-cover").style.backgroundImage = url ? `url("${url}")` : "";
  }
}

let toastT;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.add("hidden"), 2200);
}

document.querySelector('[data-action="rescan"]').onclick = async () => {
  await fetch("/api/rescan", { method: "POST" });
  toast("Actualisation de la bibliothèque…");
  setTimeout(load, 800);
};
document.querySelector('[data-action="quit"]').onclick = async () => {
  try { await fetch("/api/quit", { method: "POST" }); } catch (e) {}
  window.close();
};
$("#play").onclick = launch;
$("#fav").onclick = toggleFav;
$("#sort").onclick = cycleSort;
$("#search").addEventListener("input", (e) => { state.query = e.target.value; state.gi = 0; render(); });

// ------------------------------------------------------------ clavier à l'écran (manette / tactile)
const OSK_ROWS = ["1234567890", "AZERTYUIOP", "QSDFGHJKLM", "WXCVBN'-:&"];
const OSK_REPEAT = new Set(["up", "down", "left", "right", "b"]);
const osk = { open: false, idx: 10, keys: [] };
(function buildOsk() {
  const box = $("#osk-keys");
  OSK_ROWS.forEach((row, r) => [...row].forEach((ch, c) => osk.keys.push({ k: ch, label: ch, r, c, s: 1 })));
  [["space", "Espace", 4], ["back", "⌫", 2], ["clear", "Tout effacer", 2], ["ok", "OK", 2]]
    .reduce((c, [k, label, s]) => { osk.keys.push({ k, label, r: 4, c, s }); return c + s; }, 0);
  osk.keys.forEach((key, i) => {
    const b = document.createElement("button");
    b.className = "key" + (key.s > 1 ? ` wide${key.s}` : "") + (key.k === "ok" ? " ok" : key.k.length > 1 ? " action" : "");
    b.textContent = key.label;
    b.onclick = () => { osk.idx = i; oskPress(key); paintOsk(); };
    key.el = b;
    box.appendChild(b);
  });
})();

function openOsk() {
  osk.open = true;
  $("#search").blur();
  $("#osk").classList.remove("hidden");
  paintOsk();
}
function closeOsk() { osk.open = false; $("#osk").classList.add("hidden"); stopRepeats(); }
function paintOsk() {
  $("#osk-text").textContent = state.query;
  osk.keys.forEach((k, i) => k.el.classList.toggle("focus", i === osk.idx));
}
function setQuery(q) {
  state.query = q;
  $("#search").value = q;
  state.gi = 0;
  render();
  paintOsk();
}
function oskPress(key) {
  if (key.k === "space") setQuery(state.query + " ");
  else if (key.k === "back") setQuery(state.query.slice(0, -1));
  else if (key.k === "clear") setQuery("");
  else if (key.k === "ok") closeOsk();
  else setQuery(state.query + key.k.toLowerCase());
}
function oskMove(dx, dy) {
  const cur = osk.keys[osk.idx];
  if (dx) {
    const row = osk.keys.filter((k) => k.r === cur.r);
    const i = row.indexOf(cur);
    osk.idx = osk.keys.indexOf(row[(i + dx + row.length) % row.length]);
  } else {
    const r = (cur.r + dy + 5) % 5;
    const mid = cur.c + (cur.s - 1) / 2;
    const target = osk.keys.find((k) => k.r === r && mid >= k.c && mid < k.c + k.s) || osk.keys.find((k) => k.r === r);
    osk.idx = osk.keys.indexOf(target);
  }
  paintOsk();
}
function oskHandle(name) {
  if (name === "up") oskMove(0, -1);
  else if (name === "down") oskMove(0, 1);
  else if (name === "left") oskMove(-1, 0);
  else if (name === "right") oskMove(1, 0);
  else if (name === "a") oskPress(osk.keys[osk.idx]);
  else if (name === "b") { if (state.query) setQuery(state.query.slice(0, -1)); else closeOsk(); }
  else if (name === "y") setQuery(state.query + " ");
  else if (name === "x" || name === "start" || name === "select") closeOsk();
}
$("#osk").addEventListener("click", (e) => { if (e.target.id === "osk") closeOsk(); });
$("#search").addEventListener("pointerdown", (e) => { if (e.pointerType === "touch") { e.preventDefault(); openOsk(); } });

// ------------------------------------------------------------ clavier
document.addEventListener("keydown", (e) => {
  if (osk.open) {
    const map = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Enter: "a", Escape: "x", Backspace: "b" };
    if (map[e.key]) oskHandle(map[e.key]);
    else if (e.key.length === 1) setQuery(state.query + e.key.toLowerCase());
    else return;
    e.preventDefault();
    return;
  }
  const inSearch = document.activeElement === $("#search");
  if (inSearch && !["Escape", "Enter", "ArrowDown"].includes(e.key)) return;
  const k = e.key;
  if (k === "ArrowLeft") move(-1, 0);
  else if (k === "ArrowRight") move(1, 0);
  else if (k === "ArrowUp") move(0, -1);
  else if (k === "ArrowDown") { if (inSearch) $("#search").blur(); move(0, inSearch ? 0 : 1); }
  else if (k === "Enter" || k === " ") { if (inSearch) $("#search").blur(); else activate(); }
  else if (k === "Escape" || k === "Backspace") back();
  else if (k === "q" || k === "PageUp") cycleView(-1);
  else if (k === "e" || k === "PageDown") cycleView(1);
  else if (k === "f") toggleFav();
  else if (k === "s") cycleSort();
  else if (k === "/") { $("#search").focus(); }
  else if (k === "x") openOsk();
  else return;
  e.preventDefault();
});

// ------------------------------------------------------------ manette (lue par le serveur)
// Le serveur ne transmet rien pendant qu'un jeu tourne : la manette appartient alors au jeu.
const PAD_ACTIONS = {
  up: [() => move(0, -1), true], down: [() => move(0, 1), true],
  left: [() => move(-1, 0), true], right: [() => move(1, 0), true],
  a: [() => activate()], b: [() => back()], x: [() => openOsk()], y: [() => toggleFav()],
  lb: [() => cycleView(-1), true], rb: [() => cycleView(1), true],
  start: [() => cycleSort()], select: [() => cycleSort()],
};
const repeats = {};
function stopRepeats() { for (const k in repeats) { clearTimeout(repeats[k]); delete repeats[k]; } }
let serverPads = 0;
function connectPad() {
  const es = new EventSource("/api/events");
  es.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.t === "hello") { serverPads = m.pads; return; }
    if (m.t === "resume") { stopRepeats(); load(); return; }
    serverPads = Math.max(serverPads, 1);
    const act = osk.open ? [() => oskHandle(m.b), OSK_REPEAT.has(m.b)] : PAD_ACTIONS[m.b];
    if (!act) return;
    clearTimeout(repeats[m.b]);
    delete repeats[m.b];
    if (!m.v || state.running || document.visibilityState !== "visible") return;
    act[0]();
    if (act[1]) {
      const rep = (delay) => { repeats[m.b] = setTimeout(() => { act[0](); rep(95); }, delay); };
      rep(380);
    }
  };
  es.onerror = () => { es.close(); stopRepeats(); setTimeout(connectPad, 1500); };
}
connectPad();
document.addEventListener("visibilitychange", stopRepeats);

// ------------------------------------------------------------ manette (API Gamepad, secours)
const pad = { held: {}, next: {} };
function padLoop(t) {
  const gp = serverPads ? null : [...(navigator.getGamepads ? navigator.getGamepads() : [])].find((g) => g && g.connected);
  if (gp && !state.running && document.hasFocus()) {
    const b = (i) => gp.buttons[i] && gp.buttons[i].pressed;
    const ax = (i) => gp.axes[i] || 0;
    const dirs = {
      up: b(12) || ax(1) < -0.5, down: b(13) || ax(1) > 0.5,
      left: b(14) || ax(0) < -0.5, right: b(15) || ax(0) > 0.5,
    };
    const act = { a: b(0), b: b(1), x: b(2), y: b(3), lb: b(4), rb: b(5), start: b(9), select: b(8) };
    const fire = (name, on, fn, repeat) => {
      if (!on) { pad.held[name] = false; return; }
      if (!pad.held[name]) { pad.held[name] = true; pad.next[name] = t + 380; fn(); }
      else if (repeat && t >= pad.next[name]) { pad.next[name] = t + 95; fn(); }
    };
    const run = (name) => () => (osk.open ? oskHandle(name) : PAD_ACTIONS[name][0]());
    for (const [name, on] of Object.entries(dirs)) fire(name, on, run(name), true);
    for (const [name, on] of Object.entries(act)) fire(name, on, run(name), !!PAD_ACTIONS[name][1] || (osk.open && OSK_REPEAT.has(name)));
  }
  requestAnimationFrame(padLoop);
}
requestAnimationFrame(padLoop);
window.addEventListener("gamepadconnected", () => toast("Manette détectée"));

// ------------------------------------------------------------ divers
let lastPointer = "mouse";
document.addEventListener("pointerdown", (e) => { lastPointer = e.pointerType; }, true);

function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function ago(ts) {
  const d = (Date.now() / 1000 - ts) / 86400;
  if (d < 1) return "aujourd'hui";
  if (d < 2) return "hier";
  if (d < 30) return `il y a ${Math.floor(d)} jours`;
  return new Date(ts * 1000).toLocaleDateString("fr-FR");
}
// ------------------------------------------------------------ synchro entre appareils
function fmtSize(b) { return b > 1e9 ? (b / 1e9).toFixed(1).replace(".", ",") + " Go" : Math.max(1, Math.round(b / 1e6)) + " Mo"; }
async function loadSync() {
  const el = $("#sync");
  try {
    const st = await (await fetch("/api/sync", { cache: "no-store" })).json();
    const peers = Object.values(st.peers || {});
    if (!st.state || !peers.length) { el.classList.add("hidden"); return; }
    let txt;
    if (st.state === "stopped") txt = "⇄ Synchro arrêtée";
    else if (st.current) {
      const pct = st.current_size ? Math.floor((100 * st.current_done) / st.current_size) : 0;
      const n = peers.reduce((a, p) => a + (p.pending || 0), 0);
      txt = `⇄ Copie depuis ${peers[0].name} : ${n} jeu${n > 1 ? "x" : ""} (${pct} %)`;
    } else {
      const off = peers.find((p) => !p.online && p.pending);
      txt = off ? `⇄ ${off.name} éteint : ${off.pending} jeu${off.pending > 1 ? "x" : ""} en attente (${fmtSize(off.pending_bytes)})`
                : "⇄ Bibliothèque à jour";
    }
    el.textContent = txt;
    el.classList.remove("hidden");
  } catch (e) { el.classList.add("hidden"); }
}
loadSync();
setInterval(loadSync, 5000);

function tick() { $("#clock").textContent = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }); }
tick();
setInterval(tick, 10000);
load();
setInterval(load, 2000);

"use strict";

const SYS_COLORS = { ps2: "#4c7dff", psp: "#a78bfa", ps3: "#ff4d6d", ps4: "#22b8ff", ps1: "#9aa3b5",
  nes: "#e4002b", n64: "#2fbf71", gba: "#7c4dff", nds: "#e0e4ee", gc: "#8a6bff", wii: "#3fc6ff",
  xbox: "#5cb82e", x360: "#9bdc3c", psvita: "#2f7bff" };
// logos à fond plein : affichés dans leurs couleurs d'origine plutôt qu'en silhouette blanche
const COLOR_LOGOS = new Set(["nes", "gba"]);
// width / height of each console's retail box front, so covers keep their real shape
// DVD keep case 135x190 mm (PS2, GameCube, Wii, Xbox, Xbox 360), Blu-ray case 135x171.5 (PS3, PS4),
// UMD case 104x180 (PSP), PS Vita case 105x135, DS case 125x137, NES box 5x7 in, N64 box 7x5 in (landscape),
// GBA box 4.5x5 in, PS1 jewel case insert 120x120
const BOX_RATIO = { ps2: 0.711, gc: 0.725, wii: 0.711, xbox: 0.72, x360: 0.711, ps3: 0.787, ps4: 0.787,
  psp: 0.578, psvita: 0.778, nds: 0.912, nes: 0.714, n64: 1.4, gba: 0.9, ps1: 1 };
const DVD_RATIO = 0.714;
const boxRatio = (sys) => BOX_RATIO[sys] || DVD_RATIO;

// ------------------------------------------------------------ langues (anglais par défaut)
const I18N = {
  en: {
    refresh: "Refresh", settings: "Settings", quit: "Quit", search: "Search for a game", searchShort: "Search",
    play: "Play", favorite: "Favorite", console: "Console", sort: "Sort", back: "Back", close: "Close",
    choose: "Choose", library: "Library", recent: "Recent", favorites: "Favorites", consoles: "Consoles",
    allGames: "All games", recentlyPlayed: "Recently played", recentlyAdded: "Recently added",
    games: (n) => `${n} game${n === 1 ? "" : "s"}`, noResult: "No result", welcome: "Welcome to FORMULA",
    welcomeHint: "Add games to your roms folder to fill your library.",
    empty: "No games here yet.", emptyHint: "Games go in <code>roms/&lt;console&gt;</code>, then “Refresh”.",
    playedTimes: (n) => `Played ${n} time${n === 1 ? "" : "s"}`, lastPlayed: (s) => `Last played ${s}`,
    today: "today", yesterday: "yesterday", daysAgo: (n) => `${n} days ago`,
    scanning: "Scanning library…", refreshing: "Refreshing library…", sortBy: (s) => `Sort: ${s}`,
    launchFailed: "Could not launch the game", padFound: "Controller detected",
    running: "Now playing", runningHint: "Quit the game from the emulator menu to come back here.",
    oskType: "Type", oskErase: "Erase", oskSpace: "Space", oskDone: "Done", oskSpaceKey: "Space", oskClear: "Clear",
    language: "Language", languageHint: "Language of the FORMULA interface.",
    syncStopped: "⇄ Sync stopped", syncCopy: (name, n, pct) => `⇄ Copying from ${name}: ${n} game${n === 1 ? "" : "s"} (${pct}%)`,
    syncOff: (name, n, size) => `⇄ ${name} offline: ${n} game${n === 1 ? "" : "s"} pending (${size})`,
    syncOk: "⇄ Library up to date", gb: "GB", mb: "MB", kb: "KB", locale: "en-GB", dec: ".",
    storage: "Storage", other: "Other", free: "Free", freeOf: (f, tot) => `${f} free of ${tot}`,
    emulators: "Emulators", emulatorsHint: "Untick to uninstall (saves and settings are kept), tick to install the latest version.",
    emulator: "Emulator", version: "Version", size: "Size", installed: "Installed", yes: "Yes", no: "No",
    confirmUninstall: (n) => `Warning: you are about to uninstall the emulator ${n}.`,
    installing: (p) => (p == null ? "Installing…" : `Downloading… ${p}%`), uninstalling: "Uninstalling…",
    installError: (e) => `Failed: ${e}`, busyGame: "Close the game first",
    display: "Display", displayHint: "FORMULA window on this PC (F11 also switches).",
    windowed: "Window", fullscreen: "Full screen", coverSize: "Cover size",
    whoPlays: "Who's playing?", manageProfiles: "Manage profiles", doneManaging: "Done", addProfile: "Add",
    newProfile: "New profile", editProfile: "Edit profile", profileName: "Name", profileDefault: "Player",
    parentQuestion: "Parent account?", parentHint: "A parent account is opened with a 4-digit code, also asked to add, edit or delete profiles.",
    changePin: "Change the code", save: "Save", cancel: "Cancel", deleteProfile: "Delete",
    pinFor: (n) => `Code for ${n}`, pinParent: "Parent code", pinNew: "Choose a 4-digit code", pinConfirm: "Type the code again",
    pinWrong: "Wrong code", pinMismatch: "The codes don't match",
    confirmDeleteProfile: (n) => `Delete the profile ${n}? Its saves are kept in kDrive (Saves/Profils/_supprimes).`,
    profile: "Profile", profileHint: "Each profile has its own saves, favourites and recently played games.",
    switchProfile: "Switch profile", profileFull: "4 profiles maximum", profileError: "Could not save the profile",
    needProfile: "Choose a profile first",
    image: "Picture", imagePick: "Choose a picture…", imageClear: "Remove the picture",
    imageHint: "Best: a square picture, 1000 x 1000 pixels, JPEG, PNG or WebP. Other sizes are cropped to the centre. It is saved as a JPEG in kDrive and shows on every device.",
    imagePadHint: "In the file window, with the controller: D-pad to move, A to open or choose, X to go up a folder, LB/RB to switch area, B to cancel.",
    imageChosen: (w, h) => `Picture chosen: ${w} x ${h} px` + (w && h && w !== h ? ", cropped to the centre" : ""),
    imageOpening: "Opening the file explorer…", imageBad: "This file is not a JPEG, PNG or WebP picture",
    imageBig: "Picture too large (20 MB maximum)", imageRead: "Could not read this file",
    imageNoDialog: "No file explorer available on this device",
    journal: "Library log", journalTitle: "Library log", journalEmpty: "No game added or removed yet.",
    journalAdd: "Added", journalRemove: "Removed",
    gameOpenWarn: (n) => `${n} is still open. It will be closed, unsaved progress will be lost. Switch profile?`,
    gameManager: "Game manager", gmAll: "All", gmSummary: (n, size) => `${n} game${n === 1 ? "" : "s"} · ${size}`,
    gmMeasuring: "measuring…", gmTrash: (size, path) => `FORMULA bin: ${size}, in ${path}. Empty it yourself to free the space.`,
    gmTrashEmpty: (path) => `FORMULA bin is empty (${path}).`, gmRemove: "Remove", gmEmpty: "No game on this device.",
    gmConfirm: (title, sys, size, path) => `Remove “${title}” (${sys}, ${size}) from this device?\n\n` +
      `Saves are not touched. The game goes to the FORMULA bin (${path}), which you empty yourself to free the space. ` +
      `The other device keeps its copy and will not send it back here.`,
    gmRemoved: (n) => `${n} moved to the FORMULA bin`, gmFailed: "Could not remove the game (file in use?)",
    gmBusy: "Quit the game first", gmTop: "Back to top", gmParents: "Parent accounts only", holdYes: "Hold 2 s",
  },
  fr: {
    refresh: "Actualiser", settings: "Paramètres", quit: "Quitter", search: "Rechercher un jeu", searchShort: "Rechercher",
    play: "Jouer", favorite: "Favori", console: "Console", sort: "Trier", back: "Retour", close: "Fermer",
    choose: "Choisir", library: "Bibliothèque", recent: "Récents", favorites: "Favoris", consoles: "Consoles",
    allGames: "Tous les jeux", recentlyPlayed: "Joués récemment", recentlyAdded: "Ajoutés récemment",
    games: (n) => `${n} jeu${n > 1 ? "x" : ""}`, noResult: "Aucun résultat", welcome: "Bienvenue sur FORMULA",
    welcomeHint: "Ajoute des jeux dans le dossier roms pour remplir ta bibliothèque.",
    empty: "Aucun jeu ici pour l'instant.", emptyHint: "Les jeux se rangent dans <code>roms/&lt;console&gt;</code>, puis « Actualiser ».",
    playedTimes: (n) => `Lancé ${n} fois`, lastPlayed: (s) => `Dernière partie ${s}`,
    today: "aujourd'hui", yesterday: "hier", daysAgo: (n) => `il y a ${n} jours`,
    scanning: "Analyse de la bibliothèque…", refreshing: "Actualisation de la bibliothèque…", sortBy: (s) => `Tri : ${s}`,
    launchFailed: "Lancement impossible", padFound: "Manette détectée",
    running: "En cours", runningHint: "Quitte le jeu depuis le menu de l'émulateur pour revenir ici.",
    oskType: "Taper", oskErase: "Effacer", oskSpace: "Espace", oskDone: "Valider", oskSpaceKey: "Espace", oskClear: "Tout effacer",
    language: "Langue", languageHint: "Langue de l'interface de FORMULA.",
    syncStopped: "⇄ Synchro arrêtée", syncCopy: (name, n, pct) => `⇄ Copie depuis ${name} : ${n} jeu${n > 1 ? "x" : ""} (${pct} %)`,
    syncOff: (name, n, size) => `⇄ ${name} éteint : ${n} jeu${n > 1 ? "x" : ""} en attente (${size})`,
    syncOk: "⇄ Bibliothèque à jour", gb: "Go", mb: "Mo", kb: "Ko", locale: "fr-FR", dec: ",",
    storage: "Stockage", other: "Autres", free: "Libre", freeOf: (f, tot) => `${f} libres sur ${tot}`,
    emulators: "Émulateurs", emulatorsHint: "Décocher pour désinstaller (sauvegardes et réglages conservés), cocher pour installer la dernière version.",
    emulator: "Émulateur", version: "Version", size: "Taille", installed: "Installé", yes: "Oui", no: "Non",
    confirmUninstall: (n) => `Attention, vous allez désinstaller l'émulateur ${n}.`,
    installing: (p) => (p == null ? "Installation…" : `Téléchargement… ${p} %`), uninstalling: "Désinstallation…",
    installError: (e) => `Échec : ${e}`, busyGame: "Ferme d'abord le jeu",
    display: "Affichage", displayHint: "Fenêtre de FORMULA sur ce PC (F11 bascule aussi).",
    windowed: "Fenêtre", fullscreen: "Plein écran", coverSize: "Taille des jaquettes",
    whoPlays: "Qui joue ?", manageProfiles: "Gérer les profils", doneManaging: "Terminé", addProfile: "Ajouter",
    newProfile: "Nouveau profil", editProfile: "Modifier le profil", profileName: "Nom", profileDefault: "Joueur",
    parentQuestion: "Compte parent ?", parentHint: "Un compte parent s'ouvre avec un code à 4 chiffres, demandé aussi pour ajouter, modifier ou supprimer un profil.",
    changePin: "Changer le code", save: "Enregistrer", cancel: "Annuler", deleteProfile: "Supprimer",
    pinFor: (n) => `Code de ${n}`, pinParent: "Code parent", pinNew: "Choisis un code à 4 chiffres", pinConfirm: "Retape le code",
    pinWrong: "Code incorrect", pinMismatch: "Les deux codes sont différents",
    confirmDeleteProfile: (n) => `Supprimer le profil ${n} ? Ses sauvegardes sont conservées dans kDrive (Saves/Profils/_supprimes).`,
    profile: "Profil", profileHint: "Chaque profil a ses propres sauvegardes, favoris et jeux récents.",
    switchProfile: "Changer de profil", profileFull: "4 profils au maximum", profileError: "Enregistrement du profil impossible",
    needProfile: "Choisis d'abord un profil",
    image: "Image", imagePick: "Choisir une image…", imageClear: "Retirer l'image",
    imageHint: "Conseillé : une image carrée de 1000 x 1000 pixels, en JPEG, PNG ou WebP. Une autre taille est recadrée au centre. Elle est enregistrée en JPEG dans kDrive et s'affiche sur tous les appareils.",
    imagePadHint: "Dans la fenêtre de l'explorateur, à la manette : croix pour se déplacer, A pour ouvrir ou choisir, X pour remonter d'un dossier, LB/RB pour changer de zone, B pour annuler.",
    imageChosen: (w, h) => `Image choisie : ${w} x ${h} px` + (w && h && w !== h ? ", recadrée au centre" : ""),
    imageOpening: "Ouverture de l'explorateur de fichiers…", imageBad: "Ce fichier n'est pas une image JPEG, PNG ou WebP",
    imageBig: "Image trop lourde (20 Mo au maximum)", imageRead: "Lecture du fichier impossible",
    imageNoDialog: "Aucun explorateur de fichiers disponible sur cet appareil",
    journal: "Journal", journalTitle: "Journal de la bibliothèque", journalEmpty: "Aucun jeu ajouté ni supprimé pour l'instant.",
    journalAdd: "Ajouté", journalRemove: "Supprimé",
    gameOpenWarn: (n) => `${n} est encore ouvert. Il sera fermé et la progression non sauvegardée sera perdue. Changer de profil ?`,
    gameManager: "Gestionnaire de jeux", gmAll: "Tous", gmSummary: (n, size) => `${n} jeu${n > 1 ? "x" : ""} · ${size}`,
    gmMeasuring: "calcul…", gmTrash: (size, path) => `Corbeille FORMULA : ${size}, dans ${path}. À vider vous-même pour libérer la place.`,
    gmTrashEmpty: (path) => `Corbeille FORMULA vide (${path}).`, gmRemove: "Retirer", gmEmpty: "Aucun jeu sur cet appareil.",
    gmConfirm: (title, sys, size, path) => `Retirer « ${title} » (${sys}, ${size}) de cet appareil ?\n\n` +
      `Les sauvegardes ne sont pas touchées. Le jeu va dans la corbeille FORMULA (${path}), à vider vous-même pour libérer la place. ` +
      `L'autre appareil garde sa copie et ne la renverra pas ici.`,
    gmRemoved: (n) => `${n} est dans la corbeille FORMULA`, gmFailed: "Impossible de retirer le jeu (fichier ouvert ?)",
    gmBusy: "Quittez d'abord le jeu", gmTop: "Remonter en haut", gmParents: "Réservé aux comptes parents", holdYes: "Maintenir 2 s",
  },
};
let LANG = "en";
try { LANG = localStorage.getItem("formula.lang") || "en"; } catch (e) {}
function t(key, ...args) {
  const v = (I18N[LANG] || I18N.en)[key] ?? I18N.en[key] ?? key;
  return typeof v === "function" ? v(...args) : v;
}
const SORTS = [
  { id: "az", label: () => "A → Z", fn: (a, b) => a.title.localeCompare(b.title, t("locale")) },
  { id: "recent", label: () => t("recentlyPlayed"), fn: (a, b) => (b.last_played || 0) - (a.last_played || 0) || a.title.localeCompare(b.title, t("locale")) },
  { id: "added", label: () => t("recentlyAdded"), fn: (a, b) => (b.added || 0) - (a.added || 0) },
];

function applyI18n() {
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach((e) => { e.textContent = t(e.dataset.i18n); });
  document.querySelectorAll("[data-i18n-html]").forEach((e) => { e.innerHTML = t(e.dataset.i18nHtml); });
  document.querySelectorAll("[data-i18n-ph]").forEach((e) => { e.placeholder = t(e.dataset.i18nPh); });
  document.querySelectorAll("[data-i18n-title]").forEach((e) => { e.title = t(e.dataset.i18nTitle); });
  buildOsk();
  render();
  paintSettings();
  paintZoom();
  if (pf.open) renderProfiles();
  if (pinBox.open) paintPin();
  if (pe.open) paintEdit();
}
async function setLang(lang) {
  if (!I18N[lang]) return;
  LANG = lang;
  try { localStorage.setItem("formula.lang", lang); } catch (e) {}
  applyI18n();
  try { await fetch("/api/settings", { method: "POST", body: JSON.stringify({ lang }) }); } catch (e) {}
}

const $ = (s) => document.querySelector(s);
const state = {
  games: [], systems: [], view: "all", sort: 0, query: "",
  zone: "grid", gi: 0, ni: 0, running: null, sig: "",
};
try { state.sort = +localStorage.getItem("formula.sort") || 0; state.view = localStorage.getItem("formula.view") || "all"; } catch (e) {}

const color = (sys) => SYS_COLORS[sys] || "#8b6cff";
const sysShort = (id) => (state.systems.find((s) => s.id === id) || {}).short || id.toUpperCase();
// ?v= = date of the image files: a cover replaced under the same name is not served from the browser cache
const assetUrl = (g, name) => "/covers/" + name + (g.av ? "?v=" + g.av : "");
const coverUrl = (g) => (g.cover ? assetUrl(g, g.cover) : g.icon ? assetUrl(g, g.icon) : null);

// ------------------------------------------------------------ données
let firstLoad = true;
let PLATFORM = "";
async function load() {
  try {
    const r = await fetch("/api/library", { cache: "no-store" });
    const d = await r.json();
    if (firstLoad) {
      firstLoad = false;
      PLATFORM = d.platform || "";
      $("#version").textContent = `v${d.version}${d.platform ? " · " + d.platform : ""}`;
      display.fullscreen = !!(d.settings && d.settings.fullscreen);
      $("#set-display-sec").classList.toggle("hidden", !hasHost());
      paintSettings();
      if (d.settings && d.settings.lang && d.settings.lang !== LANG) { LANG = d.settings.lang; applyI18n(); }
    }
    if (!d.profile && !pf.open && !state.running) await openProfiles();
    if (splash.on) splash.ready();
    if (d.profile !== pf.cur) { pf.cur = d.profile; if (!pf.list.length) await fetchProfiles(); paintWho(); }
    const sig = JSON.stringify([d.profile, d.games.map((g) => [g.id, g.cover, g.fav, g.title]), d.systems.length]);
    state.systems = d.systems.sort((a, b) => a.order - b.order);
    setRunning(d.running);
    $("#status").classList.toggle("hidden", !d.scanning);
    $("#status").textContent = t("scanning");
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
    { id: "all", icon: "▦", label: t("library"), n: state.games.length },
    { id: "recent", icon: "◷", label: t("recent"), n: count((g) => g.last_played) },
    { id: "fav", icon: "★", label: t("favorites"), n: count((g) => g.fav) },
    { label: t("consoles") },
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
  $("#sort").textContent = "⇅ " + SORTS[state.sort].label();

  const list = visible();
  const titles = { all: t("allGames"), recent: t("recentlyPlayed"), fav: t("favorites") };
  const sysObj = state.systems.find((s) => s.id === state.view);
  $("#section-title").textContent = titles[state.view] || (sysObj ? sysObj.name : "");
  $("#count").textContent = t("games", list.length);

  const grid = $("#grid");
  grid.innerHTML = "";
  // one console shown: columns sized for its box (same height as a DVD case, wide boxes up to x1.5)
  grid.style.setProperty("--card-f", sysObj ? Math.min(1.5, boxRatio(state.view) / DVD_RATIO).toFixed(3) : 1);
  list.forEach((g, i) => {
    const c = document.createElement("div");
    c.className = "card";
    c.dataset.i = i;
    c.style.setProperty("--c", color(g.system));
    c.style.setProperty("--ar", boxRatio(g.system));
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
    $("#hero-title").textContent = state.games.length ? t("noResult") : t("welcome");
    $("#hero-tags").innerHTML = "";
    $("#hero-meta").textContent = state.games.length ? "" : t("welcomeHint");
    $("#hero-cover").style.backgroundImage = "";
    $("#fav").textContent = "☆ " + t("favorite");
    art.classList.remove("on");
    return;
  }
  const url = coverUrl(g);
  $("#hero-cover").style.setProperty("--ar", boxRatio(g.system));
  $("#hero-title").textContent = g.title;
  $("#hero-tags").innerHTML = `<span class="tag sys" style="--c:${color(g.system)}">${sysShort(g.system)}</span>` +
    (g.region ? `<span class="tag">${esc(g.region)}</span>` : "");
  const meta = [];
  if (g.serial) meta.push(g.serial);
  if (g.plays) meta.push(t("playedTimes", g.plays));
  if (g.last_played) meta.push(t("lastPlayed", ago(g.last_played)));
  if (g.size) meta.push((g.size / 1e9).toFixed(1).replace(".", t("dec")) + " " + t("gb"));
  $("#hero-meta").innerHTML = meta.map((m) => `<span>${esc(m)}</span>`).join("");
  $("#hero-cover").style.backgroundImage = url ? `url("${url}")` : "";
  const bg = g.hero ? assetUrl(g, g.hero) : url;
  art.style.backgroundImage = bg ? `url("${bg}")` : "";
  art.classList.toggle("on", !!bg);
  $("#fav").classList.toggle("on", !!g.fav);
  $("#fav").textContent = (g.fav ? "★ " : "☆ ") + t("favorite");
  document.documentElement.style.setProperty("--a1", color(g.system));
}

// ------------------------------------------------------------ focus / navigation
function applyFocus(scroll = true) {
  document.querySelectorAll(".card.focus, .nav-item.focus, .top-item.focus").forEach((e) => e.classList.remove("focus"));
  if (state.zone === "top") {
    const items = topItems();
    state.ti = Math.max(0, Math.min(state.ti || 0, items.length - 1));
    items[state.ti]?.classList.add("focus");
  } else if (state.zone === "grid") {
    const c = $(`.card[data-i="${state.gi}"]`);
    if (c) {
      c.classList.add("focus");
      if (scroll) c.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  } else {
    const items = railItems();
    state.ni = Math.max(0, Math.min(state.ni, items.length - 1));
    const it = items[state.ni];
    if (it) {
      it.classList.add("focus");
      // the console column follows the gamepad / keyboard selection
      if (scroll) it.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }
  updateHero();
}
function focusGrid(i, scroll = true) { state.zone = "grid"; state.gi = i; applyFocus(scroll); }
const railItems = () => [...document.querySelectorAll("#rail .nav-item")].filter((e) => !e.classList.contains("hidden"));
// barre du haut à la manette : recherche, tri, synchro / journal, profil
const topItems = () => [...document.querySelectorAll("#top .top-item")].filter((e) => !e.classList.contains("hidden"));

function columns() {
  const cards = document.querySelectorAll(".card");
  if (cards.length < 2) return 1;
  const top = cards[0].offsetTop;
  let n = 0;
  for (const c of cards) { if (c.offsetTop !== top) break; n++; }
  return n;
}

function move(dx, dy) {
  if (state.zone === "top") {
    if (dx) { state.ti = Math.max(0, Math.min(topItems().length - 1, state.ti + dx)); return applyFocus(); }
    if (dy > 0) {
      if (visible().length) return focusGrid(Math.min(state.gi, visible().length - 1));
      state.zone = "rail"; state.ni = Math.max(0, railItems().findIndex((e) => e.classList.contains("active")));
      return applyFocus();
    }
    return;
  }
  if (state.zone === "rail") {
    if (dx > 0) { state.zone = "grid"; return applyFocus(); }
    state.ni += dy;
    return applyFocus();
  }
  const n = visible().length;
  if (!n) { if (dx < 0) { state.zone = "rail"; state.ni = railItems().findIndex((e) => e.classList.contains("active")); applyFocus(); } return; }
  const cols = columns();
  let i = state.gi;
  if (dy < 0 && i < cols) { state.zone = "top"; state.ti = 0; return applyFocus(); }
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

// ------------------------------------------------------------ stick droit : saut d'une section à l'autre
// Sections : 1 = Bibliothèque / Récents / Favoris, 2 = consoles, 3 = Actualiser → Quitter,
// 4 = catalogue, 5 = barre du haut. Angle : 0° = droite, sens antihoraire (90° = haut).
// Plages (multiples de 30°) : 60-120 haut, 120-150 haut-gauche, 150-210 gauche, 210-240 bas-gauche,
// 240-300 bas, 300-30 droite, 30-60 haut-droite. La section visée dépend de la section courante.
function stickDir(a) {
  a = ((a % 360) + 360) % 360;
  if (a >= 30 && a < 60) return "ur";
  if (a >= 60 && a < 120) return "up";
  if (a >= 120 && a < 150) return "ul";
  if (a >= 150 && a < 210) return "left";
  if (a >= 210 && a < 240) return "dl";
  if (a >= 240 && a < 300) return "down";
  return "right";
}
const SECTION_JUMPS = {
  1: { up: 5, ur: 5, down: 2, right: 4 },
  2: { up: 1, down: 3, right: 4 },
  3: { up: 2, right: 4 },
  4: { up: 5, ul: 1, left: 2, dl: 3 },
  5: { down: 4, dl: 1, right: 4 },
};
const railSection = (e) => (e.dataset.action ? 3 : e.classList.contains("console") ? 2 : 1);
function currentSection() {
  if (state.zone === "top") return 5;
  if (state.zone === "grid") return 4;
  const it = railItems()[state.ni];
  return it ? railSection(it) : 1;
}
function gotoSection(s) {
  if (s === 5) { state.zone = "top"; state.ti = 0; return applyFocus(); }
  if (s === 4) {
    const n = visible().length;
    if (n) focusGrid(Math.min(state.gi, n - 1));
    return;
  }
  // colonne de gauche : l'entrée active si elle est dans la section, sinon la première
  const items = railItems();
  let i = items.findIndex((e) => railSection(e) === s && e.classList.contains("active"));
  if (i < 0) i = items.findIndex((e) => railSection(e) === s);
  if (i < 0) return;
  state.zone = "rail";
  state.ni = i;
  applyFocus();
}
function jumpSection(angle) {
  const to = SECTION_JUMPS[currentSection()][stickDir(angle)];
  if (to) gotoSection(to);
}

function activate() {
  if (state.zone === "rail") { railItems()[state.ni]?.click(); return; }
  if (state.zone === "top") {
    const el = topItems()[state.ti];
    if (!el) return;
    if (el.id === "search-box") return openOsk();
    if (el.id === "who") return openWho();
    return el.click();
  }
  launch();
}

function back() {
  if (document.activeElement === $("#search")) { $("#search").blur(); return; }
  if (state.query) { state.query = ""; $("#search").value = ""; render(); return; }
  if (state.zone === "top") { move(0, 1); return; }
  if (state.zone === "grid") { state.zone = "rail"; state.ni = Math.max(0, railItems().findIndex((e) => e.classList.contains("active"))); applyFocus(); }
  // B une seconde fois dans la colonne de gauche : « Quitter » présélectionné, A pour valider
  else { state.ni = railItems().findIndex((e) => e.dataset.action === "quit"); applyFocus(); }
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
  toast(t("sortBy", SORTS[state.sort].label()));
}

// ------------------------------------------------------------ taille des jaquettes (LT / RT, −/+, 50 à 200 %)
const zoom = { pct: 100 };
try { zoom.pct = +localStorage.getItem("formula.zoom") || 100; } catch (e) {}
function paintZoom() {
  document.documentElement.style.setProperty("--card-w", Math.round(148 * zoom.pct / 100) + "px");
  $("#zoom-range").value = zoom.pct;
  $("#zoom-val").textContent = zoom.pct + " %";
}
function setZoom(pct) {
  pct = Math.max(50, Math.min(200, Math.round(pct / 10) * 10));
  if (pct === zoom.pct) return;
  zoom.pct = pct;
  try { localStorage.setItem("formula.zoom", pct); } catch (e) {}
  paintZoom();
  if (state.zone === "grid") applyFocus();   // les colonnes changent : on garde le jeu sélectionné visible
}
const zoomStep = (d) => setZoom(zoom.pct + d * 10);
$("#zoom-out").onclick = () => zoomStep(-1);
$("#zoom-in").onclick = () => zoomStep(1);
$("#zoom-range").addEventListener("input", (e) => setZoom(+e.target.value));
$("#zoom-range").addEventListener("pointerup", (e) => e.target.blur());

// ------------------------------------------------------------ affichage (Windows : fenêtre FORMULA.exe)
// La page n'envoie à FORMULA.exe que deux messages : "fullscreen:1" et "fullscreen:0" (réglage ou F11).
const display = { fullscreen: false };
const hasHost = () => !!(window.chrome && window.chrome.webview);
function setFullscreen(on) {
  if (!hasHost()) return;
  display.fullscreen = on;
  window.chrome.webview.postMessage(on ? "fullscreen:1" : "fullscreen:0");
  fetch("/api/settings", { method: "POST", body: JSON.stringify({ fullscreen: on }) }).catch(() => {});
  paintSettings();
}
document.addEventListener("keydown", (e) => {
  if (e.key === "F11" && hasHost()) { e.preventDefault(); e.stopImmediatePropagation(); setFullscreen(!display.fullscreen); }
}, true);

// ------------------------------------------------------------ actions
async function launch() {
  const g = visible()[state.gi];
  if (!g || state.running) return;
  const c = $(`.card[data-i="${state.gi}"]`);
  if (c) { c.classList.remove("launch"); void c.offsetWidth; c.classList.add("launch"); }
  const r = await fetch("/api/launch", { method: "POST", body: JSON.stringify({ id: g.id }) });
  const d = await r.json();
  if (!d.ok) return toast(pf.cur ? t("launchFailed") : t("needProfile"));
  setRunning(g.id);
}

async function toggleFav() {
  const g = visible()[state.gi];
  if (!g) return;
  const r = await fetch("/api/fav", { method: "POST", body: JSON.stringify({ id: g.id }) });
  if (r.ok) g.fav = !g.fav;
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
    $("#run-cover").style.setProperty("--ar", boxRatio(g.system));
    $("#run-cover").style.backgroundImage = url ? `url("${url}")` : "";
  }
}

let toastT;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toastT);
  toastT = setTimeout(() => el.classList.add("hidden"), 2200);
}

document.querySelector('[data-action="rescan"]').onclick = async () => {
  await fetch("/api/rescan", { method: "POST" });
  toast(t("refreshing"));
  setTimeout(load, 800);
};
document.querySelector('[data-action="settings"]').onclick = () => openSettings();
document.querySelector('[data-action="quit"]').onclick = async () => {
  try { await fetch("/api/quit", { method: "POST" }); } catch (e) {}
  window.close();
};
$("#play").onclick = launch;
$("#fav").onclick = toggleFav;
$("#sort").onclick = cycleSort;
$("#search").addEventListener("input", (e) => { state.query = e.target.value; state.gi = 0; render(); });

// ------------------------------------------------------------ paramètres
// navigation par lignes : ligne 0 = langues (gauche/droite), puis une ligne par émulateur (sa case à cocher)
const settings = { open: false, row: 0, col: 0, emus: [], timer: null };
function openSettings() {
  settings.open = true;
  settings.row = 0;
  settings.col = 0;
  $("#settings").classList.remove("hidden");
  loadEmus();
  clearInterval(settings.timer);
  settings.timer = setInterval(loadEmus, 1500);
  paintSettings();
}
function closeSettings() {
  settings.open = false;
  clearInterval(settings.timer);
  $("#settings").classList.add("hidden");
  stopRepeats();
}
function fmtBytes(b) {
  if (b >= 1e9) return (b / 1e9).toFixed(b >= 1e11 ? 0 : 1).replace(".", t("dec")) + " " + t("gb");
  if (b >= 1e6) return Math.round(b / 1e6) + " " + t("mb");
  return Math.max(1, Math.round(b / 1e3)) + " " + t("kb");
}
async function loadEmus() {
  try {
    const d = await (await fetch("/api/emulators", { cache: "no-store" })).json();
    settings.emus = d.emulators;
    if (d.disk) {
      const k = d.disk;
      $("#st-free").textContent = t("freeOf", fmtBytes(k.free), fmtBytes(k.total));
      $("#st-formula").textContent = fmtBytes(k.formula);
      $("#st-other").textContent = fmtBytes(k.other);
      $("#storage .st-formula").style.width = (100 * k.formula / k.total) + "%";
      $("#storage .st-other").style.width = (100 * k.other / k.total) + "%";
    }
    renderEmus();
  } catch (e) { /* serveur occupé */ }
}
function renderEmus() {
  const box = $("#emu-list");
  box.innerHTML = "";
  settings.emus.forEach((e, i) => {
    const row = document.createElement("div");
    const busy = e.job === "installing" || e.job === "uninstalling";
    row.className = "emu-row" + (e.installed ? "" : " off");
    const sys = e.systems.map((s) => sysShort(s)).join(" · ");
    row.innerHTML = `<img src="emulogos/${e.id}.webp" alt="">
      <span class="emu-name">${esc(e.name)}</span><span class="emu-sys">${esc(sys)}</span>
      <span class="emu-ver">${e.installed ? esc(e.version || "?") : "—"}</span>
      <span class="emu-size">${e.installed ? fmtBytes(e.size) : "—"}</span>
      <button class="check${e.installed ? " on" : ""}${busy ? " busy" : ""}">${e.installed && !busy ? "✓" : ""}</button>`;
    if (busy || e.job === "error") {
      const st = document.createElement("div");
      st.className = "emu-state" + (e.job === "error" ? " err" : "");
      st.textContent = e.job === "error" ? t("installError", e.error) : e.job === "installing" ? t("installing", e.progress) : t("uninstalling");
      row.appendChild(st);
    }
    row.querySelector(".check").onclick = () => { settings.row = i + optRows().length; paintSettings(); toggleEmu(e); };
    box.appendChild(row);
  });
  paintSettings();
}
function toggleEmu(e) {
  if (e.job === "installing" || e.job === "uninstalling") return;
  if (state.running) return toast(t("busyGame"));
  if (e.installed) {
    openConfirm(t("confirmUninstall", e.name), () => emuAction(e, "uninstall"));
  } else {
    emuAction(e, "install");
  }
}
async function emuAction(e, action) {
  try { await fetch(`/api/emulators/${action}`, { method: "POST", body: JSON.stringify({ id: e.id }) }); } catch (err) {}
  loadEmus();
}
// lignes d'options avant la liste des émulateurs : langue, puis affichage (fenêtre FORMULA.exe uniquement)
const optRows = () => (hasHost() ? ["#set-profile", "#set-lang", "#set-display"] : ["#set-profile", "#set-lang"]);
function paintSettings() {
  document.querySelectorAll("#set-lang .set-opt").forEach((b) => b.classList.toggle("on", b.dataset.lang === LANG));
  document.querySelectorAll("#set-display .set-opt").forEach((b) => b.classList.toggle("on", (b.dataset.fs === "1") === display.fullscreen));
  optRows().forEach((sel, r) => document.querySelectorAll(sel + " .set-opt").forEach((b, i) => {
    b.classList.toggle("focus", settings.open && settings.row === r && settings.col === i);
  }));
  const first = optRows().length;
  document.querySelectorAll("#emu-list .emu-row").forEach((r, i) => {
    const cur = settings.open && settings.row === i + first;
    r.classList.toggle("cur", cur);
    r.querySelector(".check").classList.toggle("focus", cur);
    if (cur && settings.scroll) r.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
  settings.scroll = false;
}
// colonne présélectionnée sur une ligne d'options : l'option active
function optCol(r) { return [...document.querySelectorAll(optRows()[r] + " .set-opt")].findIndex((b) => b.classList.contains("on")); }
function settingsHandle(name) {
  const opts = optRows().length;
  const rows = opts + settings.emus.length;
  if (name === "up" || name === "down") {
    settings.row = (settings.row + (name === "up" ? -1 : 1) + rows) % rows;
    settings.scroll = true;
    if (settings.row < opts) settings.col = Math.max(0, optCol(settings.row));
  }
  else if ((name === "left" || name === "right") && settings.row < opts) {
    const n = document.querySelectorAll(optRows()[settings.row] + " .set-opt").length;
    settings.col = Math.max(0, Math.min(n - 1, settings.col + (name === "left" ? -1 : 1)));
  }
  else if (name === "a") {
    if (settings.row < opts) document.querySelectorAll(optRows()[settings.row] + " .set-opt")[settings.col]?.click();
    else toggleEmu(settings.emus[settings.row - opts]);
  }
  else if (name === "l3" || name === "r3") { closeSettings(); return openProfiles(); }
  else if (name === "b" || name === "select" || name === "start") return closeSettings();
  paintSettings();
}
document.querySelectorAll("#set-lang .set-opt").forEach((b) => { b.onclick = () => setLang(b.dataset.lang); });
$("#set-switch").onclick = () => { closeSettings(); openProfiles(); };
$("#set-manage").onclick = () => { closeSettings(); openProfiles(true); };
document.querySelectorAll("#set-display .set-opt").forEach((b) => { b.onclick = () => setFullscreen(b.dataset.fs === "1"); });
$("#settings .set-close").onclick = closeSettings;
$("#settings").addEventListener("click", (e) => { if (e.target.id === "settings") closeSettings(); });

// ------------------------------------------------------------ fenêtre de confirmation (Oui = A, Non = B)
// hold (ms) : « Oui » ne valide qu'en maintenant A (ou Entrée, ou le clic) pendant ce temps ; relâcher annule
const confirmBox = { open: false, onYes: null, sel: 1, hold: 0, holdT: null };
function openConfirm(text, onYes, hold = 0) {
  confirmBox.open = true;
  confirmBox.onYes = onYes;
  confirmBox.sel = 1;   // « Non » présélectionné à la souris/clavier
  confirmBox.hold = hold;
  $("#confirm-text").textContent = text;
  $("#confirm-yes span").textContent = t(hold ? "holdYes" : "yes");
  $("#confirm-yes").style.setProperty("--hold", hold / 1000 + "s");
  $("#confirm").classList.toggle("hold", !!hold);
  $("#confirm").classList.remove("hidden");
}
function closeConfirm(yes) {
  holdStop();
  confirmBox.open = false;
  $("#confirm").classList.add("hidden");
  stopRepeats();
  if (yes && confirmBox.onYes) confirmBox.onYes();
}
function holdStart() {
  if (!confirmBox.open || confirmBox.holdT) return;
  $("#confirm-yes").classList.add("holding");
  confirmBox.holdT = setTimeout(() => { confirmBox.holdT = null; closeConfirm(true); }, confirmBox.hold);
}
function holdStop() {
  clearTimeout(confirmBox.holdT);
  confirmBox.holdT = null;
  $("#confirm-yes").classList.remove("holding");
}
// bouton relâché (manette, clavier) : annule une validation en cours de maintien
function padRelease(name) { if (confirmBox.open && name === "a") holdStop(); }
function confirmHandle(name) {
  if (name === "a") return confirmBox.hold ? holdStart() : closeConfirm(true);
  if (name === "b" || name === "start" || name === "select") closeConfirm(false);
}
$("#confirm-yes").onclick = () => { if (!confirmBox.hold) closeConfirm(true); };
$("#confirm-yes").addEventListener("pointerdown", () => { if (confirmBox.hold) holdStart(); });
["pointerup", "pointerleave", "pointercancel"].forEach((ev) => $("#confirm-yes").addEventListener(ev, holdStop));
document.addEventListener("keyup", (e) => { if (e.key === "Enter" || e.key === " ") padRelease("a"); });
$("#confirm-no").onclick = () => closeConfirm(false);
$("#confirm").addEventListener("click", (e) => { if (e.target.id === "confirm") closeConfirm(false); });

// ------------------------------------------------------------ clavier à l'écran (manette / tactile)
const OSK_LAYOUTS = {
  fr: ["1234567890", "AZERTYUIOP", "QSDFGHJKLM", "WXCVBN'-:&"],
  en: ["1234567890", "QWERTYUIOP", "ASDFGHJKL'", "ZXCVBNM-:&"],
};
const OSK_REPEAT = new Set(["up", "down", "left", "right", "b"]);
const osk = { open: false, idx: 10, keys: [] };
function buildOsk() {
  const box = $("#osk-keys");
  box.innerHTML = "";
  osk.keys = [];
  (OSK_LAYOUTS[LANG] || OSK_LAYOUTS.en).forEach((row, r) => [...row].forEach((ch, c) => osk.keys.push({ k: ch, label: ch, r, c, s: 1 })));
  [["space", t("oskSpaceKey"), 4], ["back", "⌫", 2], ["clear", t("oskClear"), 2], ["ok", "OK", 2]]
    .reduce((c, [k, label, s]) => { osk.keys.push({ k, label, r: 4, c, s }); return c + s; }, 0);
  osk.keys.forEach((key, i) => {
    const b = document.createElement("button");
    b.className = "key" + (key.s > 1 ? ` wide${key.s}` : "") + (key.k === "ok" ? " ok" : key.k.length > 1 ? " action" : "");
    b.textContent = key.label;
    b.onclick = () => { osk.idx = i; oskPress(key); paintOsk(); };
    key.el = b;
    box.appendChild(b);
  });
}

function openOsk() {
  // PC : un vrai clavier est disponible, la recherche se tape directement dans le champ
  if (PLATFORM === "Windows") { $("#search").focus(); return; }
  osk.open = true;
  $("#search").blur();
  $("#osk").classList.remove("hidden");
  paintOsk();
}
function closeOsk() {
  osk.open = false;
  $("#osk").classList.add("hidden");
  stopRepeats();
  const tg = osk.target;
  osk.target = null;
  if (tg && tg.done) tg.done();
}
function openOskFor(target) {
  osk.target = target;
  osk.open = true;
  $("#osk").classList.remove("hidden");
  paintOsk();
}
// le clavier écrit dans la recherche, ou dans un autre champ (nom du profil) : osk.target = { get, set, done }
const oskGet = () => (osk.target ? osk.target.get() : state.query);
const oskSet = (v) => (osk.target ? (osk.target.set(v), paintOsk()) : setQuery(v));
function paintOsk() {
  $("#osk-text").textContent = oskGet();
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
  if (key.k === "space") oskSet(oskGet() + " ");
  else if (key.k === "back") oskSet(oskGet().slice(0, -1));
  else if (key.k === "clear") oskSet("");
  else if (key.k === "ok") closeOsk();
  // recherche en minuscules ; nom de profil : majuscule au début seulement
  else oskSet(oskGet() + (osk.target && !oskGet() ? key.k : key.k.toLowerCase()));
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
  else if (name === "b") { if (oskGet()) oskSet(oskGet().slice(0, -1)); else closeOsk(); }
  else if (name === "y") oskSet(oskGet() + " ");
  else if (name === "x" || name === "start" || name === "select") closeOsk();
}
$("#osk").addEventListener("click", (e) => { if (e.target.id === "osk") closeOsk(); });
$("#search").addEventListener("pointerdown", (e) => { if (e.pointerType === "touch") { e.preventDefault(); openOsk(); } });

// ------------------------------------------------------------ profils (« Qui joue ? »)
// Jusqu'à 4 profils, chacun avec ses sauvegardes (dans kDrive), ses favoris et ses jeux récents.
// Un compte parent s'ouvre avec un code à 4 chiffres ; dès qu'il en existe un, ajouter, modifier ou
// supprimer un profil demande aussi un code parent.
const pf = { open: false, list: [], cur: null, last: null, max: 4, parents: false, idx: 0, row: 0, manage: false, auth: null };
const FACE = '<svg class="face" viewBox="0 0 64 64" aria-hidden="true"><circle class="eye" cx="22" cy="25" r="4.5"/><circle class="eye" cx="42" cy="25" r="4.5"/><path d="M19 39c7 8 19 8 26 0"/></svg>';
const LOCK = '<span class="lock"><svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg></span>';
// image du profil (Profils/_avatars, synchronisée par kDrive) ; tant qu'elle n'est pas arrivée : le visage
const avatarSrc = (p) => (p.avatarUrl !== undefined ? p.avatarUrl : p.avatar ? `/api/avatar/${encodeURIComponent(p.id)}?v=${encodeURIComponent(p.avatar)}` : null);
function avatarHtml(p) {
  const src = avatarSrc(p);
  const img = src ? `<img src="${esc(src)}" alt="" draggable="false" onerror="this.remove()">` : "";
  return `<div class="avatar" style="--pc:${esc(p.color || "#8b6cff")}">${FACE}${img}${p.parent ? LOCK : ""}</div>`;
}
async function fetchProfiles() {
  try {
    const d = await (await fetch("/api/profiles", { cache: "no-store" })).json();
    Object.assign(pf, { list: d.profiles, cur: d.current, last: d.last, max: d.max, parents: d.parents });
  } catch (e) { /* serveur en train de démarrer */ }
}
function paintWho() {
  const p = pf.list.find((x) => x.id === pf.cur);
  document.querySelector('[data-action="games"]').classList.toggle("hidden", !gmAllowed());
  $("#who").classList.toggle("hidden", !p);
  if (!p) return;
  $("#who-avatar").innerHTML = avatarHtml(p);
  $("#who-name").textContent = p.name;
}
async function openProfiles(manage = false) {
  if (state.running) return;
  pf.open = true;
  pf.row = 0;
  pf.manage = false;
  $("#profiles").classList.remove("hidden");
  await fetchProfiles();
  const want = pf.cur || pf.last;
  pf.idx = Math.max(0, pf.list.findIndex((p) => p.id === want));
  renderProfiles();
  if (manage) startManage();
}
function closeProfiles() {
  pf.open = false;
  pf.manage = false;
  $("#profiles").classList.add("hidden");
  stopRepeats();
}
const pfTiles = () => pf.list.length + (pf.manage && pf.list.length < pf.max ? 1 : 0);
function renderProfiles() {
  $("#pf-title").textContent = pf.manage ? t("manageProfiles") : t("whoPlays");
  const box = $("#pf-list");
  box.innerHTML = "";
  pf.list.forEach((p, i) => {
    const b = document.createElement("button");
    b.className = "pf-tile" + (p.id === pf.cur ? " cur" : "");
    b.innerHTML = avatarHtml(p) + `<span class="pf-name">${esc(p.name)}</span>`;
    if (pf.manage) { b.classList.add("managing"); b.querySelector(".avatar").insertAdjacentHTML("beforeend", '<span class="edit">✎</span>'); }
    b.onclick = () => { pf.idx = i; pf.row = 0; paintProfiles(); pickTile(); };
    box.appendChild(b);
  });
  if (pf.manage && pf.list.length < pf.max) {
    const b = document.createElement("button");
    b.className = "pf-tile";
    b.innerHTML = `<div class="avatar add"><b>+</b></div><span class="pf-name">${esc(t("addProfile"))}</span>`;
    b.onclick = () => { pf.idx = pf.list.length; pf.row = 0; paintProfiles(); pickTile(); };
    box.appendChild(b);
  }
  $("#pf-manage").textContent = pf.manage ? t("doneManaging") : t("manageProfiles");
  // retour possible seulement si un profil est déjà ouvert (changement de profil)
  $("#pf-back-hint").classList.toggle("hidden", !pf.cur && !pf.manage);
  paintProfiles();
}
function paintProfiles() {
  pf.idx = Math.max(0, Math.min(pf.idx, pfTiles() - 1));
  document.querySelectorAll("#pf-list .pf-tile").forEach((b, i) => b.classList.toggle("focus", pf.row === 0 && i === pf.idx));
  $("#pf-manage").classList.toggle("focus", pf.row === 1);
}
function pickTile() {
  if (pf.manage) {
    const p = pf.list[pf.idx];
    return openEdit(p || null);
  }
  const p = pf.list[pf.idx];
  if (!p) return;
  if (p.parent) askPin({ title: t("pinFor", p.name), profile: p, onDone: (pin) => selectProfile(p, pin) });
  else selectProfile(p);
}
async function selectProfile(p, pin) {
  const r = await fetch("/api/profiles/select", { method: "POST", body: JSON.stringify({ id: p.id, pin }) });
  const d = await r.json();
  if (!d.ok) {
    if (pinBox.open) return pinError(t("pinWrong"));
    return toast(t("launchFailed"));
  }
  closePin();
  pf.cur = d.current;
  pf.list = d.profiles;
  closeProfiles();
  paintWho();
  state.sig = "";
  load();
}
// gestion : code parent demandé une fois à l'entrée (s'il existe un compte parent), gardé jusqu'à la sortie
function startManage() {
  const go = (auth) => { pf.auth = auth || null; pf.manage = true; pf.idx = 0; pf.row = 0; closePin(); renderProfiles(); };
  if (!pf.parents) return go();
  askPin({
    title: t("pinParent"),
    onDone: async (pin) => {
      const r = await fetch("/api/profiles/auth", { method: "POST", body: JSON.stringify({ auth: pin }) });
      const d = await r.json();
      if (d.ok) go(pin); else pinError(t("pinWrong"));
    },
  });
}
function stopManage() { pf.manage = false; pf.auth = null; pf.idx = Math.max(0, pf.list.findIndex((p) => p.id === pf.cur)); renderProfiles(); }
function profilesHandle(name) {
  const n = pfTiles();
  if (name === "left" && pf.row === 0) pf.idx = (pf.idx - 1 + n) % n;
  else if (name === "right" && pf.row === 0) pf.idx = (pf.idx + 1) % n;
  else if (name === "down") pf.row = 1;
  else if (name === "up") pf.row = 0;
  else if (name === "a") return pf.row === 1 ? $("#pf-manage").click() : pickTile();
  else if (name === "y") return $("#pf-manage").click();
  else if (name === "b") {
    if (pf.manage) return stopManage();
    if (pf.cur) return closeProfiles();
  }
  paintProfiles();
}
$("#pf-manage").onclick = () => (pf.manage ? stopManage() : startManage());
$("#who").onclick = () => openWho();
$("#sync").onclick = () => openJournal();

// ------------------------------------------------------------ menu déroulant du profil (barre du haut)
// Choisir un profil : code (compte parent), puis avertissement si un jeu est encore ouvert, puis changement.
const who = { open: false, idx: 0 };
async function openWho() {
  if (who.open) return closeWho();
  await fetchProfiles();
  who.open = true;
  who.idx = Math.max(0, pf.list.findIndex((p) => p.id === pf.cur));
  const box = $("#whomenu");
  box.innerHTML = "";
  pf.list.forEach((p, i) => {
    const b = document.createElement("button");
    b.className = "wm-item" + (p.id === pf.cur ? " cur" : "");
    b.innerHTML = `<span class="wm-av">${avatarHtml(p)}</span><span class="wm-name">${esc(p.name)}</span>` +
      (p.parent ? `<span class="wm-lock">${LOCK}</span>` : "") + (p.id === pf.cur ? '<span class="wm-cur">✓</span>' : "");
    b.onclick = (e) => { e.stopPropagation(); who.idx = i; whoPick(p); };
    box.appendChild(b);
  });
  const r = $("#who").getBoundingClientRect();
  box.style.top = r.bottom + 8 + "px";
  box.style.right = Math.max(8, window.innerWidth - r.right) + "px";
  box.classList.remove("hidden");
  paintWhoMenu();
}
function closeWho() { who.open = false; $("#whomenu").classList.add("hidden"); stopRepeats(); }
function paintWhoMenu() { document.querySelectorAll("#whomenu .wm-item").forEach((e, i) => e.classList.toggle("focus", i === who.idx)); }
function whoHandle(name) {
  const n = pf.list.length;
  if (name === "up" || name === "down") who.idx = (who.idx + (name === "up" ? -1 : 1) + n) % n;
  else if (name === "a") return pf.list[who.idx] && whoPick(pf.list[who.idx]);
  else if (name === "b" || name === "select" || name === "start" || name === "left" || name === "right") return closeWho();
  paintWhoMenu();
}
function whoPick(p) {
  closeWho();
  if (p.id === pf.cur) return;
  const go = async (pin) => {
    let d;
    try { d = await (await fetch("/api/profiles/check", { method: "POST", body: JSON.stringify({ id: p.id, pin }) })).json(); }
    catch (e) { return toast(t("profileError")); }
    if (!d.ok) return pinBox.open ? pinError(t("pinWrong")) : toast(t("profileError"));
    closePin();
    if (d.running) openConfirm(t("gameOpenWarn", d.running), () => switchTo(p, pin, true));
    else switchTo(p, pin, false);
  };
  if (p.parent) askPin({ title: t("pinFor", p.name), profile: p, onDone: go });
  else go();
}
async function switchTo(p, pin, force) {
  const d = await (await fetch("/api/profiles/select", { method: "POST", body: JSON.stringify({ id: p.id, pin, force }) })).json();
  if (!d.ok) return toast(t("profileError"));
  pf.cur = d.current;
  pf.list = d.profiles;
  paintWho();
  state.sig = "";
  load();
}
document.addEventListener("click", (e) => { if (who.open && !e.target.closest("#whomenu, #who")) closeWho(); });

// ------------------------------------------------------------ journal de la bibliothèque (ajouts / suppressions)
const journal = { open: false };
async function openJournal() {
  journal.open = true;
  const list = $("#journal-list");
  list.innerHTML = "";
  $("#journal").classList.remove("hidden");
  let entries = [];
  try { entries = (await (await fetch("/api/journal", { cache: "no-store" })).json()).entries; } catch (e) {}
  if (!entries.length) { list.innerHTML = `<p class="jr-empty">${esc(t("journalEmpty"))}</p>`; return; }
  const fmt = (ts) => new Date(ts * 1000).toLocaleString(t("locale"), { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  list.innerHTML = entries.map((e) => `<div class="jr-row ${e.action}"><span class="jr-when">${esc(fmt(e.ts))}</span>` +
    `<span class="jr-act">${e.action === "add" ? "+ " + esc(t("journalAdd")) : "− " + esc(t("journalRemove"))}</span>` +
    `<span class="jr-title">${esc(e.title)}</span><span class="jr-sys">${esc(sysShort(e.system || ""))}</span></div>`).join("");
  list.scrollTop = 0;
}
function closeJournal() { journal.open = false; $("#journal").classList.add("hidden"); stopRepeats(); }
function journalHandle(name) {
  const list = $("#journal-list");
  if (name === "up" || name === "down") list.scrollBy({ top: name === "up" ? -90 : 90, behavior: "smooth" });
  else if (["a", "b", "select", "start"].includes(name)) closeJournal();
}
$("#journal").addEventListener("click", (e) => { if (e.target.id === "journal" || e.target.closest(".set-close")) closeJournal(); });

// ------------------------------------------------------------ gestionnaire de jeux (taille, retirer de cet appareil)
// haut / bas : jeux (du plus gros au plus petit), LB / RB (ou gauche / droite) : console, A : retirer, B : fermer
const TRASH_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13M10 11v6M14 11v6"/></svg>';
const gm = { open: false, games: [], sys: "", idx: 0, data: null, timer: null, removing: new Set() };
// réservé aux comptes parents dès qu'il en existe un (sinon ouvert à tous)
const gmAllowed = () => !pf.parents || !!(pf.list.find((p) => p.id === pf.cur) || {}).parent;
async function openGames() {
  if (!gmAllowed()) return toast(t("gmParents"));
  gm.open = true;
  gm.idx = 0;
  gm.sys = "";
  $("#games").classList.remove("hidden");
  $("#gm-list").innerHTML = "";
  await loadGames();
}
function closeGames() {
  gm.open = false;
  clearTimeout(gm.timer);
  $("#games").classList.add("hidden");
  stopRepeats();
}
async function loadGames() {
  clearTimeout(gm.timer);
  let d;
  try { d = await (await fetch("/api/games", { cache: "no-store" })).json(); } catch (e) { return; }
  if (!gm.open) return;
  gm.data = d;
  renderGames();
  if (d.pending || d.trash == null) gm.timer = setTimeout(loadGames, 1000);
}
function gmSystems() {
  const have = new Set(gm.data.games.map((g) => g.system));
  return [""].concat(state.systems.filter((s) => have.has(s.id)).sort((a, b) => a.order - b.order).map((s) => s.id));
}
function gmList() {
  return gm.data.games.filter((g) => !gm.sys || g.system === gm.sys)
    .sort((a, b) => (b.size ?? -1) - (a.size ?? -1) || String(a.title).localeCompare(String(b.title)));
}
function renderGames() {
  const d = gm.data;
  if (!gmSystems().includes(gm.sys)) gm.sys = "";
  const curId = gm.games[gm.idx] && gm.games[gm.idx].id;
  gm.games = gmList();
  const keep = gm.games.findIndex((g) => g.id === curId);
  gm.idx = Math.max(0, Math.min(keep >= 0 ? keep : gm.idx, gm.games.length - 1));
  const total = gm.games.reduce((n, g) => n + (g.size || 0), 0);
  $("#gm-summary").textContent = t("gmSummary", gm.games.length, d.pending ? t("gmMeasuring") : fmtBytes(total)) +
    (d.disk ? " — " + t("freeOf", fmtBytes(d.disk.free), fmtBytes(d.disk.total)) : "");
  $("#gm-filter").innerHTML = gmSystems().map((s) =>
    `<button class="gm-chip${s === gm.sys ? " on" : ""}" data-sys="${esc(s)}">${esc(s ? sysShort(s) : t("gmAll"))}</button>`).join("");
  $("#gm-filter").querySelectorAll(".gm-chip").forEach((b) => { b.onclick = () => { gm.sys = b.dataset.sys; gm.idx = 0; renderGames(); }; });
  const list = $("#gm-list");
  const top = list.scrollTop;
  if (!gm.games.length) list.innerHTML = `<p class="jr-empty">${esc(t("gmEmpty"))}</p>`;
  else list.innerHTML = gm.games.map((g, i) => {
    const img = coverUrl(g);
    // part du disque entier (pas de la liste affichée) : un jeu NES ne se voit pas, 125 Go sur 500 = un quart
    const disk = d.diskTotal || (d.disk && d.disk.total) || 0;
    const pct = g.size != null && disk ? Math.min(100, 100 * g.size / disk) : 0;
    const pctTxt = g.size == null ? "" : " · " + (pct >= 10 ? Math.round(pct) : pct >= 0.1 ? pct.toFixed(1) : pct > 0 ? "< 0.1" : "0").toString().replace(".", t("dec")) + " %";
    return `<div class="gm-row${gm.removing.has(g.id) ? " removing" : ""}" data-i="${i}">
      <div class="gm-cover" style="--c:${color(g.system)}">${img ? `<img loading="lazy" src="${esc(img)}" alt="">` : ""}</div>
      <div class="gm-name"><b>${esc(g.title)}</b><span>${esc(sysShort(g.system))}</span></div>
      <div class="gm-size"><div class="gm-bar"><i style="width:${pct.toFixed(2)}%"></i></div>
        <span>${g.size == null ? esc(t("gmMeasuring")) : esc(fmtBytes(g.size)) + pctTxt}</span></div>
      <button class="gm-trash" title="${esc(t("gmRemove"))}">${TRASH_SVG}</button></div>`;
  }).join("");
  list.scrollTop = top;
  list.querySelectorAll(".gm-row").forEach((r) => {
    r.onmouseenter = () => { gm.idx = +r.dataset.i; paintGames(false); };
    r.querySelector(".gm-trash").onclick = (e) => { e.stopPropagation(); gm.idx = +r.dataset.i; paintGames(false); gmRemove(); };
  });
  $("#gm-trash").textContent = d.trash ? t("gmTrash", fmtBytes(d.trash), d.trashPath) : d.trash === 0 ? t("gmTrashEmpty", d.trashPath) : "";
  paintGames(false);
}
function gmTop() {
  gm.idx = 0;
  $("#gm-list").scrollTo({ top: 0, behavior: "smooth" });
  paintGames(false);
}
function paintGames(scroll = true) {
  document.querySelectorAll("#gm-list .gm-row").forEach((r, i) => {
    r.classList.toggle("cur", i === gm.idx);
    if (i === gm.idx && scroll) r.scrollIntoView({ block: "nearest" });
  });
}
// poubelle : détail du jeu, puis confirmation à maintenir 2 s ; la ligne est grisée pendant le déplacement
// et disparaît de la liste dès qu'il est fait
async function gmRemove() {
  const g = gm.games[gm.idx];
  if (!g || gm.removing.has(g.id)) return;
  if (state.running || gm.data.running) return toast(t("gmBusy"));
  let info;
  try { info = await (await fetch("/api/games/preview", { method: "POST", body: JSON.stringify({ id: g.id }) })).json(); }
  catch (e) { return toast(t("gmFailed")); }
  if (!info || !info.items) return toast(t("gmFailed"));
  openConfirm(t("gmConfirm", info.title, sysShort(info.system), fmtBytes(info.size), info.trash), () => gmSend(g), 2000);
}
async function gmSend(g) {
  gm.removing.add(g.id);
  renderGames();
  let r;
  try { r = await (await fetch("/api/games/remove", { method: "POST", body: JSON.stringify({ id: g.id }) })).json(); }
  catch (e) { r = {}; }
  gm.removing.delete(g.id);
  if (r.ok && gm.data) gm.data.games = gm.data.games.filter((x) => x.id !== g.id);
  if (gm.open && gm.data) renderGames();
  if (!r.ok) return toast(r.error === "running" ? t("gmBusy") : r.error === "parent" ? t("gmParents") : t("gmFailed"));
  toast(t("gmRemoved", g.title));
  state.sig = "";
  load();
  if (gm.open) loadGames();      // taille de la corbeille
}
function gmHandle(name) {
  const n = gm.games.length;
  if (name === "up" || name === "down") {
    if (n) gm.idx = Math.max(0, Math.min(n - 1, gm.idx + (name === "up" ? -1 : 1)));
    return paintGames();
  }
  if (["lb", "rb", "left", "right"].includes(name)) {
    const sys = gmSystems();
    const d = name === "lb" || name === "left" ? -1 : 1;
    gm.sys = sys[(sys.indexOf(gm.sys) + d + sys.length) % sys.length];
    gm.idx = 0;
    $("#gm-list").scrollTop = 0;
    return renderGames();
  }
  if (name === "y") return gmTop();
  if (name === "a" || name === "x") return gmRemove();
  if (name === "b" || name === "select" || name === "start") return closeGames();
}
document.querySelector('[data-action="games"]').onclick = () => openGames();
$("#gm-top").onclick = () => gmTop();
$("#games").addEventListener("click", (e) => { if (e.target.id === "games" || e.target.closest(".set-close")) closeGames(); });

// ------------------------------------------------------------ pavé du code (4 chiffres)
const pinBox = { open: false, digits: "", idx: 4, opts: null, first: null };
const PIN_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "back", "0", "cancel"];
function buildPin() {
  const box = $("#pin-keys");
  box.innerHTML = "";
  PIN_KEYS.forEach((k, i) => {
    const b = document.createElement("button");
    b.className = "key" + (k.length > 1 ? " action" : "");
    b.textContent = k === "back" ? "⌫" : k === "cancel" ? "✕" : k;
    b.onclick = () => { pinBox.idx = i; pinKey(k); };
    box.appendChild(b);
  });
}
// opts : { title, profile?, confirm? (nouveau code tapé deux fois), onDone(pin), onCancel? }
function askPin(opts) {
  Object.assign(pinBox, { open: true, digits: "", idx: 4, opts, first: null });
  $("#pin-avatar").innerHTML = opts.profile ? avatarHtml(opts.profile) : "";
  $("#pin").classList.remove("hidden");
  $("#pin-msg").textContent = "";
  paintPin();
}
function closePin(cancelled) {
  if (!pinBox.open) return;
  pinBox.open = false;
  $("#pin").classList.add("hidden");
  stopRepeats();
  if (cancelled && pinBox.opts && pinBox.opts.onCancel) pinBox.opts.onCancel();
}
function paintPin() {
  const o = pinBox.opts || {};
  $("#pin-title").textContent = pinBox.first != null ? t("pinConfirm") : o.title || "";
  document.querySelectorAll("#pin-dots i").forEach((e, i) => e.classList.toggle("on", i < pinBox.digits.length));
  document.querySelectorAll("#pin-keys .key").forEach((e, i) => e.classList.toggle("focus", i === pinBox.idx));
}
function pinError(msg) {
  pinBox.digits = "";
  $("#pin-msg").textContent = msg;
  const dots = $("#pin-dots");
  dots.classList.remove("shake"); void dots.offsetWidth; dots.classList.add("shake");
  paintPin();
}
function pinDigit(d) {
  if (pinBox.digits.length >= 4) return;
  pinBox.digits += d;
  $("#pin-msg").textContent = "";
  paintPin();
  if (pinBox.digits.length < 4) return;
  const pin = pinBox.digits;
  const o = pinBox.opts;
  if (o.confirm && pinBox.first == null) { pinBox.first = pin; pinBox.digits = ""; return setTimeout(paintPin, 120); }
  if (o.confirm && pinBox.first !== pin) { pinBox.first = null; return pinError(t("pinMismatch")); }
  setTimeout(() => o.onDone(pin), 120);
}
function pinKey(k) {
  if (k === "back") { pinBox.digits = pinBox.digits.slice(0, -1); paintPin(); }
  else if (k === "cancel") closePin(true);
  else pinDigit(k);
}
function pinHandle(name) {
  const i = pinBox.idx;
  if (name === "left") pinBox.idx = i % 3 ? i - 1 : i + 2;
  else if (name === "right") pinBox.idx = i % 3 < 2 ? i + 1 : i - 2;
  else if (name === "up") pinBox.idx = (i + 9) % 12;
  else if (name === "down") pinBox.idx = (i + 3) % 12;
  else if (name === "a") return pinKey(PIN_KEYS[pinBox.idx]);
  else if (name === "b") { if (pinBox.digits) pinKey("back"); else closePin(true); return; }
  else if (name === "start" || name === "select") return closePin(true);
  paintPin();
}
$("#pin").addEventListener("click", (e) => { if (e.target.id === "pin") closePin(true); });

// ------------------------------------------------------------ ajout / modification d'un profil
// lignes : nom, image, compte parent (Non / Oui), changer le code (parent existant), boutons
// pe.img : undefined = image inchangée, null = retirée, { token, url, w, h } = nouvelle image choisie
const pe = { open: false, p: null, name: "", parent: false, pin: null, img: undefined, picking: false, row: 0, col: 0 };
function openEdit(p) {
  if (!p && pf.list.length >= pf.max) return toast(t("profileFull"));
  Object.assign(pe, { open: true, p, name: p ? p.name : "", parent: !!(p && p.parent), pin: null, img: undefined, row: 0, col: 0 });
  $("#pe-name").value = pe.name;
  $("#pedit").classList.remove("hidden");
  paintEdit();
}
function closeEdit() {
  pe.open = false;
  $("#pe-name").blur();
  $("#pedit").classList.add("hidden");
  stopRepeats();
}
const editRows = () => ["name", "image", "parent"].concat(pe.p && pe.p.parent && pe.parent ? ["pin"] : [], ["actions"]);
const editActions = () => ["#pe-save"].concat(pe.p && pf.list.length > 1 ? ["#pe-delete"] : [], ["#pe-cancel"]);
function paintEdit() {
  if (!pe.open) return;
  $("#pe-title").textContent = pe.p ? t("editProfile") : t("newProfile");
  const color = pe.p ? pe.p.color : ["#8b6cff", "#22b8ff", "#2fbf71", "#ff8a3d"].find((c) => !pf.list.some((p) => p.color === c));
  $("#pe-avatar").innerHTML = avatarHtml({ color, parent: pe.parent, avatarUrl: editImageUrl() });
  $("#pe-img-clear").classList.toggle("hidden", !editImageUrl());
  $("#pe-img-info").textContent = pe.img ? t("imageChosen", pe.img.w, pe.img.h) : "";
  $("#pe-pin-row").classList.toggle("hidden", !editRows().includes("pin"));
  $("#pe-delete").classList.toggle("hidden", !editActions().includes("#pe-delete"));
  const rows = editRows();
  pe.row = Math.min(pe.row, rows.length - 1);
  const row = rows[pe.row];
  $("#pe-name").classList.toggle("focus", row === "name");
  document.querySelectorAll("#pe-parent .set-opt").forEach((b, i) => {
    b.classList.toggle("on", (b.dataset.v === "1") === pe.parent);
    b.classList.toggle("focus", row === "parent" && pe.col === i);
  });
  $("#pe-pin").classList.toggle("focus", row === "pin");
  imageButtons().forEach((b, i) => b.classList.toggle("focus", row === "image" && pe.col === i));
  const acts = editActions();
  document.querySelectorAll(".pe-actions .btn").forEach((b) => b.classList.toggle("focus", row === "actions" && acts[pe.col] === "#" + b.id));
}
function editName() {
  // Deck : clavier à l'écran ; PC : saisie directe dans le champ
  if (PLATFORM === "Windows") { $("#pe-name").focus(); return; }
  openOskFor({ get: () => pe.name, set: (v) => { pe.name = v.slice(0, 20); $("#pe-name").value = pe.name; }, done: paintEdit });
}
function setParent(on) {
  if (!on) { pe.parent = false; pe.pin = null; return paintEdit(); }
  if (pe.parent) return;
  if (pe.p && pe.p.parent) { pe.parent = true; return paintEdit(); }   // code existant gardé
  askPin({
    title: t("pinNew"), confirm: true,
    onDone: (pin) => { pe.pin = pin; pe.parent = true; closePin(); paintEdit(); },
  });
}
function changePin() {
  askPin({ title: t("pinNew"), confirm: true, onDone: (pin) => { pe.pin = pin; closePin(); paintEdit(); } });
}
// ---- image du profil : l'explorateur de fichiers du système s'ouvre (Windows : celui de FORMULA.exe,
// Deck : ouvert par le serveur) ; la manette y tape au clavier tant qu'il est ouvert
const editImageUrl = () => (pe.img ? pe.img.url : pe.img === null ? null : pe.p && pe.p.avatar ? avatarSrc(pe.p) : null);
const imageButtons = () => ["#pe-img-pick"].concat(editImageUrl() ? ["#pe-img-clear"] : []).map((s) => $(s));
let hostPick = false;          // FORMULA.exe sait ouvrir son propre sélecteur (message "pick-image")
if (hasHost()) {
  window.chrome.webview.addEventListener("message", (e) => {
    const m = String(e.data || "");
    if (m === "caps:pick-image") hostPick = true;
    else if (m.startsWith("picked:")) hostPicked(m.slice(7));
  });
  window.chrome.webview.postMessage("caps?");
}
// image choisie -> JPEG carré 1000 x 1000 (recadrée au centre, fond à la couleur du profil), renvoyé au serveur
const AVATAR_SIZE = 1000;
async function convertImage(url, color) {
  const img = new Image();
  img.src = url;
  await img.decode();
  const w = img.naturalWidth, h = img.naturalHeight, side = Math.min(w, h);
  const c = document.createElement("canvas");
  c.width = c.height = AVATAR_SIZE;
  const g = c.getContext("2d");
  g.fillStyle = color || "#8b6cff";
  g.fillRect(0, 0, AVATAR_SIZE, AVATAR_SIZE);
  g.imageSmoothingQuality = "high";
  g.drawImage(img, (w - side) / 2, (h - side) / 2, side, side, 0, 0, AVATAR_SIZE, AVATAR_SIZE);
  const blob = await new Promise((ok) => c.toBlob(ok, "image/jpeg", 0.9));
  const d = await (await fetch("/api/avatar/upload", { method: "POST", body: blob })).json();
  return Object.assign(d, { w, h });
}
async function imageResult(d) {
  if (d && d.ok) {
    try { d = await convertImage(d.url, pe.p ? pe.p.color : null); }
    catch (e) { d = { ok: false, error: "format" }; }
  }
  pe.picking = false;
  if (d && d.ok) { pe.img = { token: d.token, url: d.url, w: d.w, h: d.h }; return paintEdit(); }
  const err = d && d.error;
  if (err === "cancel") return;
  toast(t({ format: "imageBad", size: "imageBig", read: "imageRead", nodialog: "imageNoDialog" }[err] || "profileError"));
}
async function pickImage() {
  if (pe.picking) return;
  pe.picking = true;
  if (hostPick) {
    await fetch("/api/pad-keys", { method: "POST", body: JSON.stringify({ on: true }) }).catch(() => {});
    window.chrome.webview.postMessage("pick-image");
    return;
  }
  toast(t("imageOpening"));
  try { await imageResult(await (await fetch("/api/avatar/pick", { method: "POST", body: "{}" })).json()); }
  catch (e) { imageResult(null); }
}
async function hostPicked(path) {
  await fetch("/api/pad-keys", { method: "POST", body: JSON.stringify({ on: false }) }).catch(() => {});
  if (!path) return imageResult({ ok: false, error: "cancel" });
  try { await imageResult(await (await fetch("/api/avatar/path", { method: "POST", body: JSON.stringify({ path }) })).json()); }
  catch (e) { imageResult(null); }
}
function clearImage() {
  pe.img = null;
  pe.col = 0;
  paintEdit();
}
async function saveEdit() {
  const name = (pe.name || "").trim() || t("profileDefault");
  const avatar = pe.img === undefined ? undefined : pe.img ? pe.img.token : "";
  const body = pe.p
    ? { id: pe.p.id, name, parent: pe.parent, pin: pe.pin || undefined, avatar, auth: pf.auth }
    : { name, parent: pe.parent, pin: pe.pin || undefined, avatar, auth: pf.auth };
  // le premier compte parent créé devient le code de gestion
  const r = await fetch(`/api/profiles/${pe.p ? "update" : "create"}`, { method: "POST", body: JSON.stringify(body) });
  const d = await r.json();
  if (!d.ok) return toast(d.error === "full" ? t("profileFull") : t("profileError"));
  if (!pf.auth && pe.parent && pe.pin) pf.auth = pe.pin;
  Object.assign(pf, { list: d.profiles, parents: d.parents });
  closeEdit();
  renderProfiles();
  paintWho();
}
function deleteEdit() {
  const p = pe.p;
  openConfirm(t("confirmDeleteProfile", p.name), async () => {
    const r = await fetch("/api/profiles/delete", { method: "POST", body: JSON.stringify({ id: p.id, auth: pf.auth }) });
    const d = await r.json();
    if (!d.ok) return toast(t("profileError"));
    Object.assign(pf, { list: d.profiles, parents: d.parents, cur: d.current });
    if (!pf.parents) pf.auth = null;
    closeEdit();
    renderProfiles();
    paintWho();
  });
}
function editHandle(name) {
  const rows = editRows();
  const row = rows[pe.row];
  if (name === "up" || name === "down") {
    if (document.activeElement === $("#pe-name")) $("#pe-name").blur();
    pe.row = (pe.row + (name === "up" ? -1 : 1) + rows.length) % rows.length;
    pe.col = rows[pe.row] === "parent" ? (pe.parent ? 1 : 0) : 0;
  } else if (name === "left" || name === "right") {
    const n = row === "parent" ? 2 : row === "actions" ? editActions().length : row === "image" ? imageButtons().length : 1;
    pe.col = Math.max(0, Math.min(n - 1, pe.col + (name === "left" ? -1 : 1)));
  } else if (name === "a") {
    if (row === "name") { if (document.activeElement === $("#pe-name")) { $("#pe-name").blur(); pe.row = 1; } else return editName(); }
    else if (row === "image") return imageButtons()[pe.col].click();
    else if (row === "parent") return setParent(pe.col === 1);
    else if (row === "pin") return changePin();
    else return $(editActions()[pe.col]).click();
  } else if (name === "b" || name === "select" || name === "start") return closeEdit();
  paintEdit();
}
$("#pe-name").addEventListener("input", (e) => { pe.name = e.target.value; });
$("#pe-name").addEventListener("pointerdown", (e) => { if (e.pointerType === "touch" && PLATFORM !== "Windows") { e.preventDefault(); editName(); } });
document.querySelectorAll("#pe-parent .set-opt").forEach((b) => { b.onclick = () => { pe.row = editRows().indexOf("parent"); pe.col = +b.dataset.v; setParent(b.dataset.v === "1"); }; });
$("#pe-img-pick").onclick = pickImage;
$("#pe-img-clear").onclick = clearImage;
$("#pe-pin").onclick = changePin;
$("#pe-save").onclick = saveEdit;
$("#pe-delete").onclick = deleteEdit;
$("#pe-cancel").onclick = closeEdit;
buildPin();

// une surcouche ouverte (clavier, paramètres, profils) reçoit les commandes à la place de la bibliothèque
function overlayHandler() {
  if (splash.on) return splashHandle;
  if (confirmBox.open) return confirmHandle;
  if (osk.open) return oskHandle;
  if (pinBox.open) return pinHandle;
  if (who.open) return whoHandle;
  if (journal.open) return journalHandle;
  if (pe.open) return editHandle;
  if (pf.open) return profilesHandle;
  if (gm.open) return gmHandle;
  if (settings.open) return settingsHandle;
  return null;
}

// ------------------------------------------------------------ écran de lancement
// logo OnTrack Software ~1,4 s (entrées ignorées), puis « Qui joue ? » apparaît en fondu
const splash = { on: !!$("#splash"), ready: () => {} };
function splashHandle() { /* rien pendant le logo */ }
if (splash.on) {
  // le logo reste jusqu'à ce que l'écran suivant soit prêt (« Qui joue ? » rempli), pour ne jamais montrer
  // l'interface vide ou la bibliothèque entre les deux ; au plus 8 s si le serveur ne répond pas
  const minTime = new Promise((r) => setTimeout(r, 1350));
  const ready = new Promise((r) => { splash.ready = r; setTimeout(r, 8000); });
  Promise.all([minTime, ready]).then(() => {
    const el = $("#splash");
    const pfs = $("#profiles");
    if (!pfs.classList.contains("hidden")) { pfs.classList.remove("pf-enter"); void pfs.offsetWidth; pfs.classList.add("pf-enter"); }
    el.classList.add("out");
    splash.on = false;
    setTimeout(() => el.remove(), 400);
  });
}

// ------------------------------------------------------------ clavier
document.addEventListener("keydown", (e) => {
  const over = overlayHandler();
  if (over === confirmHandle && e.repeat) { e.preventDefault(); return; }
  if (over) {
    // nom du profil tapé au clavier (PC) : le champ garde les touches de saisie
    if (over === editHandle && document.activeElement === $("#pe-name") && !["Enter", "Escape", "ArrowUp", "ArrowDown", "Tab"].includes(e.key)) return;
    const map = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Enter: "a", Escape: osk.open && !confirmBox.open ? "x" : "b", Backspace: "b", Tab: "down" };
    if (over === pinHandle && /^[0-9]$/.test(e.key)) pinDigit(e.key);
    else if (over === pinHandle && e.key === "Escape") closePin(true);
    else if (map[e.key]) over(map[e.key]);
    else if (over === profilesHandle && e.key === "y") profilesHandle("y");
    else if (over === gmHandle && (e.key === "PageUp" || e.key === "PageDown")) gmHandle(e.key === "PageUp" ? "lb" : "rb");
    else if (over === gmHandle && (e.key === "Home" || e.key === "y")) gmHandle("y");
    else if (osk.open && e.key.length === 1) oskSet(oskGet() + (osk.target ? e.key : e.key.toLowerCase()));
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
  else if (k === "o") openSettings();
  else if (k === "g") openGames();
  else if (k === "p") openProfiles();
  else if (k === "/") { $("#search").focus(); }
  else if (k === "x") openOsk();
  else if (k === "-") zoomStep(-1);
  else if (k === "+" || k === "=") zoomStep(1);
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
  lt: [() => zoomStep(-1), true], rt: [() => zoomStep(1), true],
  start: [() => cycleSort()], select: [() => openSettings()],
  // clic d'un stick : « Qui joue ? » directement (Deck docké, sans tactile)
  l3: [() => openProfiles()], r3: [() => openProfiles()],
  // stick droit poussé : saut vers la section visée (angle envoyé avec l'appui)
  rs: [() => jumpSection(padAngle)],
};
let padAngle = 0;
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
    const over = overlayHandler();
    if (m.a !== undefined) padAngle = m.a;
    // le stick droit ne sert qu'à la bibliothèque : ignoré dans les surcouches
    const act = over ? (m.b === "rs" ? null : [() => over(m.b), OSK_REPEAT.has(m.b)]) : PAD_ACTIONS[m.b];
    if (!act) return;
    clearTimeout(repeats[m.b]);
    delete repeats[m.b];
    if (!m.v) padRelease(m.b);
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
function padLoop(ts) {
  const gp = serverPads ? null : [...(navigator.getGamepads ? navigator.getGamepads() : [])].find((g) => g && g.connected);
  if (gp && !state.running && document.hasFocus()) {
    const b = (i) => gp.buttons[i] && gp.buttons[i].pressed;
    const ax = (i) => gp.axes[i] || 0;
    const dirs = {
      up: b(12) || ax(1) < -0.5, down: b(13) || ax(1) > 0.5,
      left: b(14) || ax(0) < -0.5, right: b(15) || ax(0) > 0.5,
    };
    const act = { a: b(0), b: b(1), x: b(2), y: b(3), lb: b(4), rb: b(5), lt: b(6), rt: b(7), start: b(9), select: b(8), l3: b(10), r3: b(11) };
    const fire = (name, on, fn, repeat) => {
      if (!on) { if (pad.held[name]) padRelease(name); pad.held[name] = false; return; }
      if (!pad.held[name]) { pad.held[name] = true; pad.next[name] = ts + 380; fn(); }
      else if (repeat && ts >= pad.next[name]) { pad.next[name] = ts + 95; fn(); }
    };
    const run = (name) => () => { const over = overlayHandler(); return over ? over(name) : PAD_ACTIONS[name][0](); };
    for (const [name, on] of Object.entries(dirs)) fire(name, on, run(name), true);
    for (const [name, on] of Object.entries(act)) fire(name, on, run(name), !!PAD_ACTIONS[name][1] || (!!overlayHandler() && OSK_REPEAT.has(name)));
    // stick droit : saut de section (poussé au-delà de 60 %, relâché sous 35 %)
    const rx = ax(2), ry = -ax(3), rOn = Math.hypot(rx, ry) > (pad.held.rs ? 0.35 : 0.6);
    if (rOn && !pad.held.rs && !overlayHandler()) jumpSection(Math.atan2(ry, rx) * 180 / Math.PI);
    pad.held.rs = rOn;
  }
  requestAnimationFrame(padLoop);
}
requestAnimationFrame(padLoop);
window.addEventListener("gamepadconnected", () => toast(t("padFound")));

// ------------------------------------------------------------ divers
let lastPointer = "mouse";
document.addEventListener("pointerdown", (e) => { lastPointer = e.pointerType; }, true);

function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function ago(ts) {
  const d = (Date.now() / 1000 - ts) / 86400;
  if (d < 1) return t("today");
  if (d < 2) return t("yesterday");
  if (d < 30) return t("daysAgo", Math.floor(d));
  return new Date(ts * 1000).toLocaleDateString(t("locale"));
}
// ------------------------------------------------------------ synchro entre appareils
function fmtSize(b) {
  return b > 1e9 ? (b / 1e9).toFixed(1).replace(".", t("dec")) + " " + t("gb") : Math.max(1, Math.round(b / 1e6)) + " " + t("mb");
}
async function loadSync() {
  const el = $("#sync");
  try {
    const st = await (await fetch("/api/sync", { cache: "no-store" })).json();
    const peers = Object.values(st.peers || {});
    if (!st.state || !peers.length) { el.textContent = "🕘 " + t("journal"); el.classList.remove("hidden"); return; }
    let txt;
    if (st.state === "stopped") txt = t("syncStopped");
    else if (st.current) {
      const pct = st.current_size ? Math.floor((100 * st.current_done) / st.current_size) : 0;
      const n = peers.reduce((a, p) => a + (p.pending || 0), 0);
      txt = t("syncCopy", peers[0].name, n, pct);
    } else {
      const off = peers.find((p) => !p.online && p.pending);
      txt = off ? t("syncOff", off.name, off.pending, fmtSize(off.pending_bytes)) : t("syncOk");
    }
    el.textContent = txt;
    el.classList.remove("hidden");
  } catch (e) { el.textContent = "🕘 " + t("journal"); }
}

function tick() { $("#clock").textContent = new Date().toLocaleTimeString(t("locale"), { hour: "2-digit", minute: "2-digit" }); }

applyI18n();
tick();
setInterval(tick, 10000);
loadSync();
setInterval(loadSync, 5000);
load();
setInterval(load, 2000);

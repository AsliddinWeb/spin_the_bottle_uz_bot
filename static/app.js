"use strict";
// Layout units are set from JS so the page also works in old phone WebViews (no cqw / dvh / container queries).
function setUnits() {
  const r = document.documentElement.style, w = Math.min(document.documentElement.clientWidth || innerWidth, 480);
  r.setProperty("--u", w / 100 + "px"); r.setProperty("--vh", innerHeight / 100 + "px");
}
setUnits(); addEventListener("resize", setUnits); addEventListener("orientationchange", setUnits);
const tg = window.Telegram && Telegram.WebApp && Telegram.WebApp.initData !== undefined ? Telegram.WebApp : null;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

// seat centres in % of the felt (x, y) — 12 seats around the table
// Geometry measured from the original game (% of the felt). Centre of play is right of the HUD column.
// Phone (Telegram iOS/Android): HUD row on top of an almost square felt. Desktop: HUD column on the left.
// Force with ?layout=top or ?layout=side when testing in a normal browser.
const forced = new URLSearchParams(location.search).get("layout");
const MOBILE = forced ? forced === "top" : !!((tg && ["ios", "android", "android_x"].includes(tg.platform)) || (!tg && matchMedia("(pointer:coarse)").matches));
if (MOBILE) document.documentElement.classList.add("top");
if (tg && tg.platform === "ios") document.documentElement.classList.add("ios");
const CENTER = MOBILE ? [50.1, 56.4] : [56, 49.5];
const SEATS_RAW = MOBILE
  ? [[17.6, 26.3], [39.4, 21.8], [60.9, 21.8], [83.1, 26.7], [86.5, 46.2], [86.5, 65.4], [83.1, 85.3], [61.2, 89.5], [38.8, 89.5], [17.5, 85.3], [13.3, 65.4], [13.3, 46.2]]
  : [[27, 18], [46.5, 12.6], [65.5, 12.6], [85, 18], [89, 39.7], [88, 61], [85, 83], [65.5, 88], [46.5, 88], [27, 83], [23.5, 61], [23.5, 39.7]];
// seat element = avatar + name, centred as one box: shift down so the AVATAR centre sits on the measured point
const SEATS = SEATS_RAW.map(([x, y]) => [x, y + 1.4]);
const PAIR = [-1, 1].map(s => [CENTER[0] + s * (MOBILE ? 12.4 : 13), CENTER[1] + (MOBILE ? -1 : 3)]);   // the two players of a spin, side by side

let CFG, ME, ws, T = null, lang = "uz", initData = "", skew = 0, target = 0;
let lastSpinId = 0, lastKiss = 0, rot = 0, seatSig = [], joinedOnce = false, reconnectDelay = 800;

const svgI = (b, c = "#fff") => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${b}</svg>`;
const ICON = {
  gift: svgI('<rect x="3.5" y="9" width="17" height="11.5" rx="2"/><path d="M12 9v11.5M3.5 13h17M12 9C9 3.5 5.5 5.5 8 8M12 9c3-5.5 6.5-3.5 4-1"/>'),
  badge: svgI('<path d="M12 2.5l2.2 1.6 2.7-.2 1 2.5 2.3 1.5-.7 2.6.7 2.6-2.3 1.5-1 2.5-2.7-.2L12 21.5l-2.2-1.6-2.7.2-1-2.5L3.8 16l.7-2.6-.7-2.6 2.3-1.5 1-2.5 2.7.2z"/><path d="M8.6 12l2.5 2.5 4.4-4.8"/>'),
  mail: svgI('<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/>'),
  flag: svgI('<path d="M5 21V4M5 4.5h12l-2.5 4 2.5 4H5"/>'),
  kick: svgI('<path d="M4 14l3-8 5 1.5-1.5 4 6 1.5 1.5 3.5-3 2.5H6z"/><path d="M18 3l.8 2.2L21 6l-2.2.8L18 9l-.8-2.2L15 6l2.2-.8zM21 11l.5 1.3 1.3.5-1.3.5L21 14.6l-.5-1.3-1.3-.5 1.3-.5z"/>'),
  music: svgI('<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>'),
  user: svgI('<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20c.6-4 3.6-6 7.5-6s6.9 2 7.5 6"/>'),
};

// ------------------------------------------------------------ helpers
const t = (k, v = {}) => {
  let s = (I18N[lang] && I18N[lang][k]) ?? I18N.en[k] ?? k;
  for (const [a, b] of Object.entries(v)) s = s.replaceAll(`{${a}}`, b);
  return s;
};
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ls = {
  get: (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch { return d; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
};
const initials = n => (String(n || "?").trim().split(/\s+/).map(w => w[0]).join("").slice(0, 2) || "?").toUpperCase();
const avInner = (photo, name) => photo
  ? `<img src="${esc(photo)}" referrerpolicy="no-referrer" onerror="this.outerHTML='<div class=ini>${esc(initials(name))}</div>'">`
  : `<div class="ini">${esc(initials(name))}</div>`;
const miniAv = (photo, name) => photo
  ? `<div class="av-mini"><img src="${esc(photo)}" referrerpolicy="no-referrer" onerror="this.outerHTML='${esc(initials(name))}'"></div>`
  : `<div class="av-mini">${esc(initials(name))}</div>`;

async function api(path, method = "GET", body) {
  const r = await fetch(path, {
    method, headers: { "Content-Type": "application/json", "X-Init-Data": initData },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let d = ""; try { d = (await r.json()).detail; } catch {}
    if (d && typeof d === "object" && d.code === "banned") { showBanned(d); const e = new Error("banned"); e.code = "banned"; throw e; }
    const e = new Error(d || r.status); e.code = d; throw e;
  }
  return r.json();
}
function toast(msg, ms = 2600) {
  const d = document.createElement("div"); d.className = "toast"; d.textContent = msg;
  $("#toasts").appendChild(d); setTimeout(() => d.remove(), ms);
}
function openModal(html, { cls = "", closable = true, onclose } = {}) {
  const ov = document.createElement("div"); ov.className = "ov";
  ov.innerHTML = `<div class="modal ${cls}">${closable ? '<button class="x">✕</button>' : ""}<div class="mb"></div></div>`;
  const root = $("#modal-root"); root.querySelectorAll(".ov:not(.out)").forEach(o => o.classList.add("under"));  // older popups stay visible behind the new one
  root.appendChild(ov); sfx.open();
  const m = { el: $(".mb", ov), root: ov };
  m.close = () => {
    if (ov.classList.contains("out")) return;
    ov.classList.add("out"); setTimeout(() => ov.remove(), 170); sfx.close(); onclose && onclose();
    const rest = [...root.querySelectorAll(".ov:not(.out)")].filter(o => o !== ov), top = rest[rest.length - 1];
    if (top) top.classList.remove("under");
  };
  m.set = h => { m.el.innerHTML = h; };
  m.set(html);
  if (closable) { $(".x", ov).onclick = m.close; ov.addEventListener("click", e => { if (e.target === ov) m.close(); }); }
  return m;
}
const closeAllModals = () => $("#modal-root").innerHTML = "";
const openLink = u => (tg && tg.openLink ? tg.openLink(u) : window.open(u, "_blank"));
const openTg = u => (tg && tg.openTelegramLink ? tg.openTelegramLink(u) : window.open(u, "_blank"));

// ------------------------------------------------------------ sound (engine in sfx.js)
document.addEventListener("click", e => { if (e.target.closest("button")) sfx.click(); }, true);


// ------------------------------------------------------------ bottle art
const BOTTLES = {
  bottle_green: { c0: "#12420c", c1: "#2c861c", c2: "#6cc238", c3: "#dcffb4", label: "#f6e9c8", ink: "#b0482e" },
  bottle_red: { c0: "#3f0808", c1: "#a31d1d", c2: "#f0604d", c3: "#ffe0d8", label: "#fff2e0", ink: "#7a1a1a" },
  bottle_blue: { c0: "#08204b", c1: "#1b56b4", c2: "#5fa9ff", c3: "#e0f0ff", label: "#f3f7ff", ink: "#1b56b4" },
  bottle_gold: { c0: "#573a04", c1: "#b5811b", c2: "#ffd75e", c3: "#fff8d2", label: "#fffaf0", ink: "#9a6a10" },
  bottle_brown: { c0: "#2a1608", c1: "#6b3a14", c2: "#b3743a", c3: "#f1d2a8", label: "#f6e9c8", ink: "#6b3a14" },
  bottle_amber: { c0: "#4a2204", c1: "#b5651d", c2: "#f0a54a", c3: "#ffe2b0", label: "#fff2dc", ink: "#8a4a10" },
  bottle_clear: { c0: "#5a6b73", c1: "#a9c0c9", c2: "#e8f3f6", c3: "#ffffff", label: "#ffffff", ink: "#5a6b73" },
  bottle_milk: { c0: "#b4b4ab", c1: "#e6e6de", c2: "#ffffff", c3: "#ffffff", label: "#ffffff", ink: "#9a9a90" },
  bottle_wine: { c0: "#1c0a16", c1: "#4a1236", c2: "#8c2a63", c3: "#e9b3d3", label: "#f5e6ef", ink: "#4a1236" },
  bottle_champagne: { c0: "#0b2a14", c1: "#1c5a2c", c2: "#3f9a58", c3: "#c8f2d2", label: "#f3e7c0", ink: "#1c5a2c" },
  bottle_cola: { c0: "#3a0f08", c1: "#7a2412", c2: "#c4553a", c3: "#ffd3c6", label: "#fff", ink: "#7a2412" },
  bottle_rainbow: { c0: "#3b1670", c1: "#7b3fe4", c2: "#ff8ad6", c3: "#fff0fb", label: "#fffafd", ink: "#c0369b" },
};
let bsvg = 0;
function bottleSvg(id) {
  // a stout wine/beer bottle lying along the Y axis (cap at the top): ribbed lip, short shoulder, wide body, notched base
  const b = BOTTLES[id] || BOTTLES.bottle_green, k = "bt" + (++bsvg);
  const body = "M26 14H38C38.4 30 38.4 46 39.6 58C41 72 62 78 62 100V160C62 168 58 173 52 175Q44 168 32 168Q20 168 12 175C6 173 2 168 2 160V100C2 78 23 72 24.4 58C25.6 46 25.6 30 26 14Z";
  return `<svg viewBox="0 0 64 180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="${k}g" x1="0" x2="1"><stop offset="0" stop-color="${b.c0}"/><stop offset=".12" stop-color="${b.c1}"/><stop offset=".36" stop-color="${b.c2}"/><stop offset=".62" stop-color="${b.c1}"/><stop offset=".92" stop-color="${b.c0}"/><stop offset="1" stop-color="${b.c0}"/></linearGradient>
    <linearGradient id="${k}v" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".18"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".3"/></linearGradient>
    <clipPath id="${k}c"><path d="${body}"/></clipPath>
  </defs>
  <g filter="url(#gloss)">
    <path d="${body}" fill="url(#${k}g)" stroke="${b.c0}" stroke-width="1.6" stroke-linejoin="round"/>
    <g clip-path="url(#${k}c)">
      <rect x="0" y="60" width="64" height="120" fill="url(#${k}v)"/>
      <ellipse cx="32" cy="164" rx="26" ry="9" fill="#000" opacity=".26"/>
      <path d="M9 104V158" stroke="#fff" stroke-opacity=".6" stroke-width="5" stroke-linecap="round"/>
      <path d="M13 92C16 84 22 78 28 72" stroke="#fff" stroke-opacity=".55" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M54 108V156" stroke="#fff" stroke-opacity=".22" stroke-width="3" stroke-linecap="round"/>
      <path d="M30 20V54" stroke="#fff" stroke-opacity=".55" stroke-width="2.4" stroke-linecap="round"/>
      <ellipse cx="32" cy="128" rx="14" ry="26" fill="${b.c3}" opacity=".16"/>
    </g>
    <rect x="23.4" y="3" width="17.2" height="12" rx="3.6" fill="url(#${k}g)" stroke="${b.c0}" stroke-width="1.5"/>
    <path d="M24 7.6H40M24 11H40" stroke="${b.c0}" stroke-opacity=".5" stroke-width="1.2"/>
    <ellipse cx="32" cy="4.4" rx="6.8" ry="2.1" fill="${b.c0}" opacity=".85"/>
    <rect x="26" y="7" width="12" height="1.8" rx=".9" fill="#fff" opacity=".5"/>
  </g>
</svg>`;
}
const chatHue = n => { let h = 0; for (const c of String(n)) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };

// ------------------------------------------------------------ ban screen (full block, nothing else is usable)
function showBanned(info) {
  closeAllModals(); $("#boot").classList.remove("off");
  $("#boot").innerHTML = `<div class="banbox"><div style="font-size:64px">🚫</div><h2>${esc(t("banned_title"))}</h2>
    <p><b>${esc(t("banned_reason"))}:</b> ${esc(info.reason || "—")}</p>
    <p><b>${esc(t("banned_until"))}:</b> ${info.until ? new Date(info.until * 1000).toLocaleString() : "∞"}</p><small>${esc(t("banned_hint"))}</small></div>`;
  try { if (ws) ws.close(4004); } catch {}
}

// ------------------------------------------------------------ report dialog
function openReport(uid) {
  const m = openModal(`<h2>${t("report_title")}</h2>${["abuse", "spam", "nsfw", "fraud", "age"].map(k => `<button class="menu-i rp-i" data-r="${k}" style="font-size:18px">${esc(t("rs_" + k))}</button>`).join("")}`);
  $$("[data-r]", m.el).forEach(b => b.onclick = async () => {
    try { await api("/api/report", "POST", { to: uid, reason: b.dataset.r }); toast(t("report_sent2")); m.close(); }
    catch (e) { toast(e.code === "dup" ? t("report_dup") : t("err")); m.close(); }
  });
}

// ------------------------------------------------------------ boot
// The entry title is a ready picture per language (tools/make_titles.py): live SVG text was cut off in the Telegram web view.
(function bootTitle() {
  const T = { ru: "Целуй и Знакомься", uz: "O'p va Tanishing", en: "Kiss & Meet" };
  const l = (window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code || "").slice(0, 2), k = T[l] ? l : "ru";
  document.querySelector("#boot .btitle").innerHTML = `<img src="/static/title-${k}.webp?v=2" alt="${T[k]}" width="1072" height="528">`;
})();
// Entry sequence (as in the original): green screen with a progress bar -> title -> table.
const bootT0 = performance.now();
function bootProgress(p) { $("#boot").style.setProperty("--p", p + "%"); }
function bootDone() {
  const el = $("#boot"); bootProgress(100);
  setTimeout(() => {
    el.className = "tt";                                        // bar off, title on
    setTimeout(() => { el.classList.add("felt"); setTimeout(() => el.classList.add("off"), 280); }, 850);
  }, Math.max(0, 650 - (performance.now() - bootT0)) + 120);
}
async function boot() {
  bootProgress(14);
  if (tg) { tg.ready(); tg.expand(); if (tg.onEvent) tg.onEvent("viewportChanged", setUnits); try { tg.setHeaderColor("#000000"); if (tg.setBackgroundColor) tg.setBackgroundColor("#f4f4f5"); if (tg.setBottomBarColor) tg.setBottomBarColor("#ffffff"); tg.disableVerticalSwipes && tg.disableVerticalSwipes(); } catch {} }
  const q = new URLSearchParams(location.search);
  initData = (tg && tg.initData) || "";
  CFG = await fetch("/api/config").then(r => r.json());
  CFG.gifts.forEach(g => { GIFT_BY_EMOJI[g.emoji] = g.id; });
  bootProgress(42);
  if (!initData) {
    if (!CFG.dev) { $("#boot-msg").textContent = "Open this game from Telegram"; return; }
    let id = q.get("dev") || ls.get("devid", ""); if (!id) { id = String(100000 + Math.floor(Math.random() * 899999)); }
    ls.set("devid", id); initData = "dev:" + id;
  }
  try { ME = await api("/api/me"); } catch { const bm = $("#boot-msg"); if (bm) bm.textContent = "Auth failed"; return; }
  bootProgress(72); lang = ME.lang; applyStatic(); renderMe();
  bindUi(); setBottle(ME.bottle);
  bootDone();
  if (!ME.age) await profileModal(true);
  connect();
  loadCompliments();
  if (ME.daily.available) setTimeout(openDaily, 900);
}

function tableLabel() { $("#table-no").innerHTML = `${esc(t("table"))}<br>${T.id}`; }

// Celebration windows queue up. They are not shown while the player takes part in the current turn (they would cover the
// decision buttons and the kiss), and only one is open at a time.
const cheers = []; let cheer = null;
const myTurnNow = () => !!(T && ME && ["spin_wait", "spinning", "ask_spinner", "ask_target", "result"].includes(T.phase) && (T.turn === ME.id || T.target === ME.id));
function celebrate(make) { cheers.push(make); pumpCheers(); }
function pumpCheers() {
  if (cheer && (!cheer.m.root.isConnected || cheer.m.root.classList.contains("out"))) cheer = null;
  if (cheer) {
    if (myTurnNow()) { cheers.unshift(cheer.make); cheer.m.close(); cheer = null; }   // my turn began: put it aside for later
    return;
  }
  if (!cheers.length || myTurnNow() || $("#modal-root .ov:not(.out)")) return;
  const make = cheers.shift(); cheer = { make, m: make() };
}
function showAch(id) {
  const x = CFG.achievements.find(q => q.id === id); if (x) celebrate(() => achWindow(x, id));
}
function achWindow(x, id) {
  const tier = CFG.achievements.filter(q => q.stat === x.stat).sort((p, q) => p.need - q.need);
  const n = Math.max(1, Math.ceil((tier.findIndex(q => q.id === id) + 1) / tier.length * 3));
  const m = openModal(`<h2>${esc(t("ach_congrats"))}</h2><div class="sub">${esc(t("ach_unlocked"))}</div>
    <div class="stars">${"★".repeat(n)}<i>${"★".repeat(3 - n)}</i></div>
    <div class="rays"><div class="medal">${ACH_ICON[x.stat] || "🏅"}</div></div>
    <h3 class="center" style="margin:6px 0 2px">${esc(t("md_" + ({ kisses: "kisser", spins: "spinner", gifts_sent: "generous", gifts_received: "favorite", msgs: "talker", streak: "streak", tracks: "dj" }[x.stat] || "kisser")))}</h3>
    <div class="req">${esc(t("achs_" + x.stat, { n: x.need }))}</div>
    <button class="btn cta-ok" style="width:100%">${esc(t("ach_continue"))} +❤${x.reward}</button>`, { cls: "achm", closable: false });
  $(".cta-ok", m.el).onclick = m.close; sfx.ach();
  return m;
}
function applyStatic() {
  [["btn-wheel", "wheel_title"], ["btn-rating", "league_title"], ["btn-menu", "hud_menu"], ["btn-settings", "settings"], ["btn-table", "hud_table"]].forEach(([id, k]) => { const e = $("#" + id); if (e) e.title = t(k); });
  document.documentElement.lang = lang;
  $("#chat-input").placeholder = t("type_msg");
  $("#gp-label").textContent = t("send_gift");
  $("#newmsg span").textContent = t("new_msgs");
  if (T) tableLabel();
}

function renderMe() {
  $("#hearts").textContent = ME.hearts;
  $("#btn-daily").classList.toggle("hidden", !ME.daily.available);
  const ready = (ME.starter || []).filter(x => x.done && !x.claimed).length, dready = (ME.dtasks || []).filter(x => x.n >= x.goal && !x.claimed).length;
  $("#hearts-dot").classList.toggle("hidden", !(ready || dready));   // a reward is waiting in the hearts window
  if (ready > (renderMe.ready || 0)) { toast(t("st_ready"), 3500); sfx.ach(); }
  renderMe.ready = ready;
  if (dready > (renderMe.dready || 0)) { toast(t("dt_ready"), 3500); sfx.ach(); }
  renderMe.dready = dready;
  if (ME.rank > (renderMe.rank ?? ME.rank)) { toast(t("rk_up", { r: RANK_E[ME.rank] + " " + rankName(ME.rank) }), 4500); sfx.win(); }
  renderMe.rank = ME.rank;
  const ev = ME.event, ec = $("#btn-event");
  ec.classList.toggle("hidden", !ev); if (ev) ec.innerHTML = `${esc(ev.emoji)} <b>+❤${ev.bonus}</b>`;
  if (ev && renderMe.ev !== ev.id) { renderMe.ev = ev.id; toast(`${ev.emoji} ${ev.name} · ${t("ev_bonus", { n: ev.bonus })}`, 5000); sfx.ach(); }
}
function openEvent() {
  const ev = ME.event; if (!ev) return;
  const left = Math.max(0, ev.ends - Math.floor(Date.now() / 1000)), d = Math.floor(left / 86400), h = Math.floor(left % 86400 / 3600);
  const m = openModal(`<h2>${esc(ev.emoji)} ${esc(ev.name)}</h2><p class="center" style="font-size:18px">${esc(t("ev_bonus", { n: ev.bonus }))}</p><p class="sub center">${esc(t("ev_left", { d, h }))}</p>`);
}
function openDailyTasks() {
  const m = openModal("");
  const render = () => {
    const dt = ME.dtasks || [];
    m.set(`<h2>📅 ${esc(t("dt_title"))}</h2><p class="sub center">${esc(t("dt_sub"))}</p>
      ${dt.map(x => `<div class="card2 dt"><div class="dt-in"><b>${esc(t("dt_" + x.id))}</b><div class="dt-bar"><i style="width:${Math.round(x.n / x.goal * 100)}%"></i></div><small>${x.n}/${x.goal}</small></div>${x.claimed ? "✔" : `<button class="btn" data-c="${x.id}" ${x.n >= x.goal ? "" : "disabled"}>+❤${x.reward}</button>`}</div>`).join("")}`);
    $$("[data-c]", m.el).forEach(b => b.onclick = async () => {
      try { ME = await api("/api/dtask/claim", "POST", { id: b.dataset.c }); renderMe(); sfx.win(); render(); } catch { toast(t("not_yet")); }
    });
  };
  render();
}
const RANK_E = ["🌱", "💫", "🔥", "🌟", "💎"];
const rankName = i => t("rk_" + i);
function rankLine(kisses, rank) {   // title + progress to the next one
  const at = CFG.ranks || [0, 10, 50, 200, 1000], nx = at[rank + 1];
  return `<div class="rk"><span class="rk-e">${RANK_E[rank]}</span><div class="rk-in"><b>${esc(rankName(rank))}</b>${nx ? `<div class="dt-bar"><i style="width:${Math.min(100, Math.round((kisses - at[rank]) / (nx - at[rank]) * 100))}%"></i></div><small>${kisses}/${nx} 💋 → ${esc(rankName(rank + 1))}</small>` : `<small>${esc(t("rk_max"))}</small>`}</div></div>`;
}
function openStarter() {
  const names = { st_spin: "st_spin", st_kiss: "st_kiss", st_gift: "st_gift" }, m = openModal("");
  const render = () => {
    const st = ME.starter || [];
    if (!st.length) return m.close();
    m.set(`<h2>🎯 ${esc(t("st_title"))}</h2><p class="sub center">${esc(t("st_sub"))}</p>
      ${st.map(x => `<div class="card2"><b>${x.done ? "✅" : "⬜"} ${esc(t(names[x.id]))}</b>${x.claimed ? "✔" : `<button class="btn" data-c="${x.id}" ${x.done ? "" : "disabled"}>+❤${x.reward}</button>`}</div>`).join("")}`);
    $$("[data-c]", m.el).forEach(b => b.onclick = async () => {
      try { ME = await api("/api/starter/claim", "POST", { id: b.dataset.c }); renderMe(); sfx.win(); render(); } catch { toast(t("not_yet")); }
    });
  };
  render();
}

function fillFab() {   // the two floating buttons use the same art as the first two gift panel items
  const b = $$("#dj-fab button"); if (b[0]) b[0].innerHTML = giftIcon("music_now"); if (b[1]) b[1].innerHTML = giftIcon("music_queue");
}
function bindUi() {
  fillFab();
  const chat = $("#chat"), pill = $("#newmsg");
  chat.addEventListener("scroll", () => { if (chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80) pill.classList.add("hidden"); }, { passive: true });
  pill.onclick = () => { chat.scrollTop = chat.scrollHeight; pill.classList.add("hidden"); };
  $("#btn-hearts").onclick = openShop;
  $("#btn-wheel").onclick = openWheel;
  $("#btn-rating").onclick = openLeague;
  $("#btn-menu").onclick = openMenu;
  $("#btn-settings").onclick = openSettings;
  $("#btn-table").onclick = openTables;
  $("#btn-daily").onclick = openDaily;
  $("#btn-event").onclick = openEvent;
  $("#gp-plus").onclick = openShop;
  $("#gp-close").onclick = closeGifts;
  $("#chat-form").onsubmit = e => {
    e.preventDefault();
    const v = $("#chat-input").value.trim(); if (!v) return;
    send({ t: "chat", text: v }); $("#chat-input").value = "";
  };
  const EMOJIS = "😀😂🤣😍🥰😘😎🤩😉😏🙈😜🤗🥳😢😡👍👏🙏🔥💖💋🍾🌹🎉🤝👀💃🕺✨".match(/\p{Extended_Pictographic}\uFE0F?/gu);
  const row = $("#emoji-row");
  row.innerHTML = EMOJIS.map(e => `<button type="button">${e}</button>`).join("");
  row.onclick = e => { const b = e.target.closest("button"); if (b) { const i = $("#chat-input"); i.value += b.textContent; i.focus(); } };
  $("#emoji-btn").onclick = () => row.classList.toggle("hidden");
  const seats = $("#seats");
  SEATS.forEach(([x, y], i) => {
    const d = document.createElement("div"); d.className = "seat empty"; d.id = "seat" + i;
    d.style.left = x + "%"; d.style.top = y + "%";
    d.innerHTML = `<div class="av"></div>`;
    d.onclick = e => {
      const p = T && T.seats.find(s => s.seat === i); if (!p) return;
      if (p.uid === ME.id) return openGestures();
      if (e.target.closest(".pbtn") || target === p.uid) return openProfile(p.uid);  // selected: the 👤 opens the profile
      openGifts(p.uid);
    };
    seats.appendChild(d);
  });
  let lastWaitToast = 0;
  $("#bottle").onclick = () => {
    if (!T || T.phase !== "spin_wait") return;
    if (T.turn === ME.id) { $("#bottle").classList.remove("tap"); send({ t: "spin" }); return; }
    if (Date.now() - lastWaitToast > 2200) { lastWaitToast = Date.now(); toast(t("not_your_turn", { n: nameOf(T.turn) })); }   // "X is spinning right now, wait for your turn"
  };
  $("#dj-fab").onclick = e => { const b = e.target.closest("[data-k]"); if (b) b.dataset.k === "video" ? openMusicPicker("music_now", "video") : openMusicPicker(b.dataset.k); };
  const range = $("#pl-range"); range.value = ls.get("musicVol", "0"); applyVolume();
  range.oninput = () => { ls.set("musicVol", range.value); applyVolume(); };
  $("#pl-icon").onclick = () => { range.value = parseInt(range.value) ? 0 : 60; ls.set("musicVol", range.value); applyVolume(); };
  setInterval(tick, 250);
}

// ------------------------------------------------------------ websocket
function send(o) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); }

// leave the table right away when the page is closed so no ghost avatar stays seated
window.addEventListener("pagehide", () => { try { if (ws) ws.close(1000); } catch {} });

// A phone can lose the socket without any "close" event (app switched, network changed): the screen would stay frozen.
// So the client pings every few seconds and replaces a connection that has been silent for too long.
const PING_MS = 8000, STALE_MS = 20000, WAKE_GRACE_MS = 4000;
let lastRecv = 0, lastPing = 0, lastBeat = 0, beatTimer = 0;
function showReconnect(msg) { $("#boot").className = "re felt"; $("#boot-msg").textContent = msg; }
function connect() {
  const s = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws?init=${encodeURIComponent(initData)}`);
  ws = s; lastRecv = lastBeat = Date.now();
  s.onopen = () => { reconnectDelay = 800; lastRecv = Date.now(); };
  s.onmessage = ev => { lastRecv = Date.now(); handle(JSON.parse(ev.data)); };
  s.onclose = e => {
    showReconnect(e.code === 4001 ? "Opened in another window" : t("reconnecting"));
    if (e.code === 4001 || e.code === 4003 || e.code === 4004) return;
    setTimeout(() => { if (ws === s) connect(); }, reconnectDelay); reconnectDelay = Math.min(reconnectDelay * 1.6, 8000);
  };
  if (!beatTimer) { beatTimer = setInterval(heartbeat, 2000); document.addEventListener("visibilitychange", heartbeat); }
}
function heartbeat() {
  if (!ws || ws.readyState > 1 || document.hidden) return;   // closed sockets are handled by onclose
  const now = Date.now();
  if (now - lastBeat > 10000) { lastRecv = Math.max(lastRecv, now - STALE_MS + WAKE_GRACE_MS); lastPing = 0; }   // just woke up: ask, and wait a moment
  lastBeat = now;
  if (now - lastRecv > STALE_MS) {
    ws.onopen = ws.onmessage = ws.onclose = null; try { ws.close(); } catch {}
    showReconnect(t("reconnecting")); return connect();
  }
  if (now - lastPing >= PING_MS) { lastPing = now; send({ t: "ping" }); }
}

function handle(m) {
  switch (m.t) {
    case "hello":
      ME = m.me; renderMe(); if ($("#boot").classList.contains("re")) $("#boot").classList.add("off");   // only the reconnect overlay closes here; the entry sequence closes itself
      send({ t: "join", table: parseInt(sessionStorage.getItem("tbl")) || "random" });
      break;
    case "me": ME = m.me; renderMe(); if (!$("#gest-panel").classList.contains("hidden")) renderGestures(); break;
    case "joined":
      sessionStorage.setItem("tbl", m.table); $("#chat").innerHTML = ""; $("#newmsg").classList.add("hidden"); lastSpinId = 0; seatSig = [];
      T = { id: m.table, seats: [], phase: "waiting" }; tableLabel();
      m.history.forEach(addChat); { const c = $("#chat"); c.scrollTop = c.scrollHeight; $("#newmsg").classList.add("hidden"); } joinedOnce = true; break;
    case "state": onState(m); break;
    case "chat": addChat(m); break;
    case "toast": toast(t(m.key)); if (m.key === "no_hearts") openShop(); break;
    case "banned": showBanned(m); break;
    case "court": openCourtPop(m); break;
    case "compliment": showCompliment(m); sfx.gift(); break;
    case "ach": showAch(m.id); break;
    case "medals": showMedals(m.list); break;
    case "ref_paid": toast(t("ref_paid", { n: m.name, h: m.hearts }), 6000); sfx.win(); break;
    case "weekly": toast(t("weekly_won", { p: m.place, h: m.hearts }), 5000); sfx.ach(); break;
    case "left":
      T = null; closeGifts();
      if (m.reason === "afk") toast(t("left_afk"), 4000);
      if (m.reason === "kicked") toast(t("kicked"), 4000);
      sessionStorage.removeItem("tbl"); openTables(); break;
  }
}

// ------------------------------------------------------------ table rendering
function serverNow() { return Date.now() + skew; }

let myTurnKey = "";
function onState(s) {
  const prev = T; T = s; skew = s.now - Date.now(); kickAt = performance.now();
  const mine = (s.phase === "spin_wait" && s.turn === ME.id) || (s.phase === "ask_spinner" && s.turn === ME.id) || (s.phase === "ask_target" && s.target === ME.id);
  const key = mine ? s.phase + ":" + (s.spin ? s.spin.id : 0) + ":" + s.turn : "";
  if (key && key !== myTurnKey) sfx.turn();
  myTurnKey = key;
  if (s.phase === "ask_spinner" && (!prev || prev.phase !== "ask_spinner")) setTimeout(sfx.pair, 900);
  if (prev && prev.seats.length < s.seats.length) sfx.join(); else if (prev && prev.seats.length > s.seats.length) sfx.leave();
  renderSeats(); renderCenter(); renderActions(); handleSpin(); handleMusic(); renderKickBar(); pumpCheers();
  if (target && !s.seats.find(p => p.uid === target)) closeGifts();
  if (!$("#gift-panel").classList.contains("hidden")) updateGiftHead();
}

function seatOf(uid) { const p = T && T.seats.find(s => s.uid === uid); return p ? p.seat : -1; }
const inPair = () => T && (["ask_spinner", "ask_target"].includes(T.phase) || (T.phase === "result" && T.result === "kiss"));

function renderSeats() {
  const pair = inPair();
  SEATS.forEach(([x, y], i) => {
    const el = $("#seat" + i), p = T.seats.find(s => s.seat === i);
    let sig = p ? JSON.stringify(p) : "";
    if (sig !== seatSig[i]) {
      seatSig[i] = sig;
      if (!p) { el.className = "seat empty"; el.innerHTML = `<div class="av"></div>`; }
      else {
        const fr = p.frame ? "fr-" + p.frame.replace("frame_", "") : "";
        el.innerHTML = `<div class="frame ${fr}"><div class="av">${avInner(p.photo, p.name)}</div>${frameArt(p.frame)}</div>${p.gesture ? `<span class="gestE">${p.gesture}</span>` : ""}` +
          (p.kisses ? `<span class="kb"><i>💋</i><b>${p.kisses}</b></span>` : "") +
          (p.gifts && p.gifts.hand ? `<span class="gf">${giftIcon(p.gifts.hand)}</span>` : "") +
          (p.gifts && p.gifts.head ? `<span class="gh">${giftIcon(p.gifts.head)}</span>` : "") +
          (p.gifts && p.gifts.side ? `<span class="gx">${giftIcon(p.gifts.side)}</span>` : "") +
          (p.vip ? `<span class="vipmark">👑</span>` : "") +
          (p.uid !== ME.id ? `<button class="gbtn">${ICON.gift}</button><button class="pbtn">${ICON.user}</button>` : "") +
          `<div class="nm">${frameEmblem(p.frame)}<span>${esc(p.name)}${p.age ? ", " + p.age : ""}</span>${frameEmblem(p.frame)}</div>`;
      }
    }
    if (!p) { el.className = "seat empty"; el.style.left = x + "%"; el.style.top = y + "%"; return; }
    const isTurn = p.uid === T.turn, isTarget = p.uid === T.target && T.target;
    const inP = pair && (isTurn || isTarget);
    el.className = "seat" + (p.frame ? " framed" : "") + (p.uid === ME.id ? " me" : "") + (isTurn && T.phase !== "waiting" ? " turn" : "") +
      (isTarget ? " target" : "") + (inP ? " pair" : "") + (target === p.uid ? " sel" : "") + ((gwaitUntil[p.uid] || 0) > performance.now() ? " gwait" : "");
    const pos = inP ? PAIR[isTurn ? 0 : 1] : [x, y];
    el.style.left = pos[0] + "%"; el.style.top = pos[1] + "%";
  });
}

function nameOf(uid) { const p = T && T.seats.find(s => s.uid === uid); return p ? p.name : "?"; }

function renderHint() {
  const h = $("#hint"), mine = T.phase === "spin_wait" && T.turn === ME.id;
  $("#bottle").classList.toggle("tap", mine);
  h.classList.toggle("mine", mine);
  if (mine) {  // "Крути бутылочку!" with a hand-drawn arrow pointing at the bottle
    h.style.left = CENTER[0] + 22 + "%"; h.style.top = CENTER[1] - 3 + "%";
    // original: the arrow sits between the bottle and a two-line text, pointing at the bottle
    h.innerHTML = `<svg viewBox="0 0 44 40" width="44"><path d="M40 6C26 4 14 12 6 28" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/><path d="M5 29l10-3M5 29l1.500-10.500" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg><span>${esc(t("spin_hint"))}</span>`;
    return h.classList.remove("hidden");
  }
  const i = T.phase === "spin_wait" ? seatOf(T.turn) : -1;
  if (i < 0) return h.classList.add("hidden");
  const [sx, sy] = SEATS[i], hx = sx + (CENTER[0] - sx) * .5, hy = sy + (CENTER[1] - sy) * .5;
  const felt = $("#felt").getBoundingClientRect();
  const deg = Math.atan2((sy - hy) * felt.height, (sx - hx) * felt.width) * 180 / Math.PI;
  h.style.left = hx + "%"; h.style.top = hy + "%";
  h.innerHTML = `<span>${esc(t("turn_short"))}</span><span class="ha"><svg viewBox="0 0 32 20" style="transform:rotate(${deg}deg)"><path d="M3 10H28M20 3L28.500 10L20 17" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></span>`;
  h.classList.remove("hidden");
  keepHintClear(h, sx, sy, felt);
}
function keepHintClear(h, sx, sy, felt) {   // slide the hint from the seat toward the bottle until it covers no player
  const w = h.offsetWidth, ht = h.offsetHeight;
  const boxes = T.seats.map(p => { const el = $("#seat" + p.seat), [x, y] = SEATS[p.seat]; return [x / 100 * felt.width, y / 100 * felt.height, el.offsetWidth / 2, el.offsetHeight / 2 + 2]; });
  for (let f = .5; f <= .8001; f += .05) {
    const x = sx + (CENTER[0] - sx) * f, y = sy + (CENTER[1] - sy) * f, px = x / 100 * felt.width, py = y / 100 * felt.height;
    h.style.left = x + "%"; h.style.top = y + "%";
    if (boxes.every(([bx, by, bw, bh]) => Math.abs(px - bx) >= w / 2 + bw || Math.abs(py - by) >= ht / 2 + bh)) return;
  }
}

function renderCenter() {
  renderHint();
  const kissed = T.phase === "result" && T.result === "kiss";
  $("#arc-top").classList.toggle("hidden", !(T.phase === "ask_target" || kissed));  // spinner said yes
  $("#arc-bot").classList.toggle("hidden", !kissed);                                // target said yes too
  const box = $("#center-msg"); let msg = "";
  switch (T.phase) {
    case "waiting": msg = T.need === "f" ? t("wait_girls") : T.need === "m" ? t("wait_boys") : t("waiting"); break;
    case "between": msg = t("next_turn"); break;
    case "spin_wait": msg = ""; break;
    case "ask_spinner": msg = T.turn === ME.id ? t("your_choice") : t("ask_kiss"); break;
    case "ask_target": msg = T.target === ME.id ? t("your_choice") : t("ask_back"); break;
    case "result": msg = T.result === "kiss" ? t("kissed", { a: nameOf(T.turn), b: nameOf(T.target) }) : t("nokiss"); break;
  }
  box.textContent = msg;
  const middle = T.phase === "waiting" || T.phase === "between" || (T.phase === "result" && T.result !== "kiss");
  box.style.top = (middle ? CENTER[1] : CENTER[1] - (MOBILE ? 19.5 : 22.5)) + "%";
  if (T.phase === "result" && T.result === "kiss" && lastKiss !== T.spin.id) {
    lastKiss = T.spin.id; kissFx();
  } else if (T.phase === "result" && T.result !== "kiss" && lastKiss !== -T.spin.id) {
    lastKiss = -T.spin.id; sfx.no();
  }
}

// Kiss effect: pink glow + light rays, a glossy lips stamp that pops in, a burst of hearts and sparkles, "+❤N" over both players.
const LIPS_SVG = `<svg class="kl" viewBox="0 0 64 44" xmlns="http://www.w3.org/2000/svg"><g filter="url(#gloss)"><path d="M5 24C13 8 25 8 32 15C39 8 51 8 59 24C51 38 42 41 32 41C22 41 13 38 5 24Z" fill="url(#gRed)" stroke="#7a0f1e" stroke-opacity=".5" stroke-width="1.4" stroke-linejoin="round"/><path d="M7 24C18 29 46 29 57 24" fill="none" stroke="#6a0a18" stroke-width="2.2" stroke-linecap="round"/><path d="M15 17C20 13 25 13 29 16C24 16 19 17 15 17Z" fill="#fff" fill-opacity=".6"/></g></svg>`;
const heartMini = c => `<svg viewBox="-12 -11 24 22"><path d="M0 9C-12 0-9-9-4.5-9C-2-9 0-7 0-5C0-7 2-9 4.5-9C9-9 12 0 0 9Z" fill="${c}" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/><path d="M-6-6C-4-7-2-6-1.5-4" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="1.6" stroke-linecap="round"/></svg>`;
const sparkMini = `<svg viewBox="-10 -10 20 20"><path d="M0-9L2.4-2.4L9 0L2.4 2.4L0 9L-2.4 2.4L-9 0L-2.4-2.4Z" fill="#fff6c8" stroke="#ffd34d" stroke-width="1"/></svg>`;
const LIP_COLS = ["#e5231f", "#d4141c", "#c4147f", "#e0267a", "#ff3d8a"];
const lipSvg = c => `<svg viewBox="0 0 64 44"><path d="M5 24C13 8 25 8 32 15C39 8 51 8 59 24C51 38 42 41 32 41C22 41 13 38 5 24Z" fill="${c}"/><path d="M6 24C20 30 44 30 58 24" fill="none" stroke="rgba(60,0,20,.55)" stroke-width="2" stroke-linecap="round"/><path d="M16 19c5-5 10-4 14-1" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="2.4" stroke-linecap="round"/></svg>`;
function lipPrints(seatEl) {   // lipstick marks stamped on a player's photo one after another, each with its own smack; they stay for a while
  const fr = seatEl.querySelector(".frame"); if (!fr) return;
  fr.querySelectorAll(".lipst").forEach(e => e.remove());
  const layer = document.createElement("div"); layer.className = "lipst"; fr.appendChild(layer);
  const n = 8 + Math.floor(Math.random() * 5);
  for (let i = 0; i < n; i++) {
    const l = document.createElement("i"), s = 22 + Math.random() * 30;
    l.innerHTML = lipSvg(LIP_COLS[Math.floor(Math.random() * LIP_COLS.length)]);
    l.style.cssText = `width:${s}%;left:${Math.random() * 78 - 6}%;top:${Math.random() * 78 - 8}%;--r:${Math.round(Math.random() * 90 - 45)}deg;animation-delay:${i * 70}ms`;
    layer.appendChild(l); setTimeout(() => sfx.smack(), i * 70);
  }
  setTimeout(() => { layer.classList.add("fade"); setTimeout(() => layer.remove(), 1500); }, 11000);
}
function kissFx() {
  const felt = $("#felt"); if (!felt) return;
  felt.querySelectorAll(".kfx").forEach(e => e.remove());
  const u = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--u")) || 4, rnd = (a, b) => a + Math.random() * (b - a);
  const root = document.createElement("div"); root.className = "kfx";
  root.innerHTML = `<div class="kg"></div><div class="kr"></div>${LIPS_SVG}`;
  felt.appendChild(root); sfx.kiss();
  const cols = ["#ff4d6d", "#ff2e63", "#ff7fa8", "#ffb3c8", "#e5374a"];
  for (let i = 0; i < 18; i++) {
    const s = rnd(2.4, 5.4) * u, h = document.createElement("div"); h.className = "kh";
    h.style.cssText = `width:${s}px;height:${s}px;left:${-s / 2}px;top:${-s / 2}px`; h.innerHTML = heartMini(cols[i % cols.length]); root.appendChild(h);
    const ang = -Math.PI / 2 + rnd(-1.15, 1.15), dist = rnd(9, 26) * u, dx = Math.cos(ang) * dist, dy = Math.sin(ang) * dist - rnd(3, 9) * u;
    h.animate([{ transform: "translate(0,0) scale(.2) rotate(0deg)", opacity: 0 },
      { offset: .18, opacity: 1, transform: `translate(${dx * .3}px,${dy * .3}px) scale(1) rotate(${rnd(-25, 25)}deg)` },
      { transform: `translate(${dx}px,${dy}px) scale(.85) rotate(${rnd(-55, 55)}deg)`, opacity: 0 }],
      { duration: rnd(1300, 2200), delay: rnd(60, 420), easing: "cubic-bezier(.2,.7,.3,1)", fill: "both" });
  }
  for (let i = 0; i < 9; i++) {
    const s = rnd(1.6, 3.2) * u, e = document.createElement("div"); e.className = "kh"; e.style.cssText = `width:${s}px;height:${s}px;left:${rnd(-14, 14) * u - s / 2}px;top:${rnd(-9, 9) * u - s / 2}px`;
    e.innerHTML = sparkMini; root.appendChild(e);
    e.animate([{ transform: "scale(0) rotate(0deg)", opacity: 0 }, { offset: .4, transform: "scale(1.2) rotate(45deg)", opacity: 1 }, { transform: "scale(0) rotate(90deg)", opacity: 0 }], { duration: rnd(700, 1100), delay: rnd(100, 900), fill: "both" });
  }
  const K = (CFG.kiss || { reward: 1, vip_bonus: 1 }), fr = felt.getBoundingClientRect(), c0 = root.getBoundingClientRect();
  [T && T.turn, T && T.target].forEach(uid => {
    const i = uid ? seatOf(uid) : -1; if (i < 0) return;
    const el = $("#seat" + i), p = T.seats.find(s => s.uid === uid), r = el.getBoundingClientRect();
    el.classList.add("kissing"); setTimeout(() => el.classList.remove("kissing"), 1200); lipPrints(el);
    const f = document.createElement("div"); f.className = "kf"; f.textContent = "+❤" + (K.reward + (p && p.vip ? K.vip_bonus : 0));
    f.style.left = (r.left + r.width / 2 - c0.left) + "px"; f.style.top = (r.top - c0.top) + "px"; root.appendChild(f);
  });
  setTimeout(() => root.remove(), 2800);
}

const BOOST_E = { kiss_fire: "🔥", slap: "🖐️" };
let boostUntil = 0, boostSpin = -1, boostUsed = -1;
function decide(v) {   // answering also opens a short window in which a choice booster can be thrown
  send({ t: "decide", v }); boostUntil = Date.now() + 7000; boostSpin = T && T.spin ? T.spin.id : -1; setTimeout(updateBoostbar, 7100);
}
function updateBoostbar() {
  const felt = $("#felt"); if (!felt || !T) return;
  let bar = $("#boostbar"); if (!bar) { bar = document.createElement("div"); bar.id = "boostbar"; felt.appendChild(bar); }
  const kinds = ["kiss_fire", "slap"].filter(k => ((ME.inv || {})[k] || { qty: 0 }).qty > 0);
  const ok = (T.turn === ME.id || T.target === ME.id) && Date.now() < boostUntil && T.spin && T.spin.id === boostSpin && boostUsed !== boostSpin && ["ask_spinner", "ask_target", "result"].includes(T.phase) && kinds.length;
  bar.innerHTML = ok ? kinds.map(k => `<button data-bk="${k}"><span>${BOOST_E[k]}</span><b>${ME.inv[k].qty}</b></button>`).join("") : "";
  $$("[data-bk]", bar).forEach(b => b.onclick = () => { send({ t: "boost", kind: b.dataset.bk }); boostUsed = boostSpin; bar.innerHTML = ""; });
}
function boostFx(kind) {
  const felt = $("#felt"); if (!felt) return;
  const e = document.createElement("div"); e.className = "bfx " + (kind === "slap" ? "slap" : "fire");
  e.innerHTML = kind === "slap" ? `<span class="hand">🖐️</span><i>💥</i>` : `<span class="fl">🔥</span>${LIPS_SVG}`;
  felt.appendChild(e); setTimeout(() => e.remove(), 2300);
  if (kind === "slap") { sfx.giftPlay("slipper"); setTimeout(() => sfx.smack(), 220); } else sfx.kiss();
}
function renderActions() {
  const a = $("#actions"); a.innerHTML = "";
  const btn = (txt, cls, fn) => { const b = document.createElement("button"); b.className = "cta " + cls; b.textContent = txt; b.onclick = () => { a.innerHTML = ""; fn(); }; a.appendChild(b); };
  if (T.phase === "ask_spinner" && T.turn === ME.id) { btn(t("kiss_btn"), "", () => decide(true)); btn(t("skip_btn"), "alt", () => decide(false)); }
  else if (T.phase === "ask_target" && T.target === ME.id) { btn(t("yes_btn"), "", () => decide(true)); btn(t("no_btn"), "alt", () => decide(false)); }
  updateBoostbar();
}

function tick() {
  pumpCheers();
  if (T && T.kicks && T.kicks.length) renderKickBar();
  const sec = T && T.deadline ? Math.ceil((T.deadline - serverNow()) / 1000) : 0, cnt = sec > 0 && T && ["spin_wait", "ask_spinner", "ask_target"].includes(T.phase);
  $("#tbl-n").classList.toggle("hidden", !cnt); $("#btn-table").classList.toggle("cnt", !!cnt); if (cnt) $("#tbl-n").textContent = sec;
  if (!T || !T.deadline) { $("#timer").textContent = ""; return; }
  const left = Math.ceil((T.deadline - serverNow()) / 1000);
  if (myTurnKey && left > 0 && left <= 3) sfx.tick();
  $("#timer").textContent = ["ask_spinner", "ask_target"].includes(T.phase) && left > 0 ? left : "";
}

// ------------------------------------------------------------ bottle
function angleToSeat(i) {
  const felt = $("#felt").getBoundingClientRect();
  const dx = (SEATS[i][0] - CENTER[0]) * felt.width / 100, dy = (SEATS[i][1] - CENTER[1]) * felt.height / 100;
  return Math.atan2(dx, -dy) * 180 / Math.PI;
}
let curBottle = "";
function setBottle(id) {
  if (id === curBottle) return;
  curBottle = id; const b = $("#bottle");
  b.innerHTML = bottleSvg(id); b.className = id === "bottle_rainbow" ? "rainbow" : "";
}
function handleSpin() {
  const b = $("#bottle"), s = T.spin;
  if (s.id === lastSpinId) return;
  lastSpinId = s.id;
  if (!s.id) return;
  setBottle(s.bottle);
  const ti = seatOf(T.target); if (ti < 0) return;
  const want = angleToSeat(ti);
  if (T.phase === "spinning") {
    const delta = (((want - rot) % 360) + 360) % 360;
    rot += 360 * 6 + delta;
    b.style.transition = `transform ${s.dur}s cubic-bezier(.15,.55,.1,1)`;
    b.style.transform = `rotate(${rot}deg)`; sfx.spin(s.dur, 360 * 6 + delta);
  } else {
    rot = Math.round(want / 360) * 360 + want; b.style.transition = "none"; b.style.transform = `rotate(${rot}deg)`;
  }
}

// ------------------------------------------------------------ chat
function addPm(m) {
  const box = $("#chat"), d = document.createElement("div"); d.className = "msg";
  d.innerHTML = `${miniAv(m.photo, m.name)}<div class="bubble pm"><span class="who" style="color:hsl(${chatHue(m.name)} 62% 42%)">🔒 ${esc(m.name)}:</span> ${esc(m.text)}</div>`;
  $(".bubble", d).onclick = () => openPm({ id: m.uid, name: m.name });
  box.appendChild(d); box.scrollTop = box.scrollHeight; sfx.pm();
}
function seatPhoto(uid) { const p = T && T.seats.find(s => s.uid === uid); return p ? p.photo : ""; }
// A sent gift flies in an arc from the sender's seat to the receiver's hand slot, then lands with a bounce.
const DRINK = { coffee: "#4a2a12", tea: "#c8842e", cola: "#3b1d0c", milk: "#ffffff", wine: "#8a1a3a", whisky: "#d98c2b", cocktail: "#ff8a1f", martini: "#cfeff0", champagne: "#f4dc7a", smoothie: "#ff7fb2" };
const SPLAT = { tomato: ["#e5371e", "#9a1408"], egg: ["#ffd23d", "#c8920a"], pie: ["#fff6e0", "#d9b98a"], bucket: ["#6dbcff", "#2a73d6"], bomb: ["#2b2b2b", "#000"] };
const splatSvg = (c, d) => `<svg viewBox="0 0 100 100"><g fill="${c}" stroke="${d}" stroke-width="1.6" stroke-linejoin="round"><path d="M50 14C60 10 70 20 74 28C84 26 92 36 86 46C94 54 90 66 80 68C82 78 72 86 62 82C56 92 42 90 38 82C28 86 16 78 20 68C10 64 8 52 16 46C10 36 18 26 28 28C32 18 42 10 50 14Z"/><circle cx="12" cy="20" r="4"/><circle cx="90" cy="14" r="3"/><circle cx="8" cy="80" r="3.5"/><circle cx="94" cy="84" r="4"/><path d="M42 80c-1 10 2 16 6 16s6-6 4-16zM64 76c0 8 2 12 5 12s4-5 3-12z"/></g><ellipse cx="38" cy="34" rx="9" ry="5" fill="#fff" opacity=".45" transform="rotate(-20 38 34)"/></svg>`;
function landFx(seatEl, emoji) {   // what happens when a gift lands: drinks are poured into the glass, tomatoes and eggs burst, the frog hops
  const id = GIFT_BY_EMOJI[emoji]; if (!id) return;
  const gf = seatEl.querySelector(DRINK[id] ? ".gf" : ".gx");
  if (DRINK[id] && gf) { gf.style.setProperty("--liq", DRINK[id]); gf.classList.add("pour"); setTimeout(() => gf.classList.remove("pour"), 1700); }
  if (id === "frog" && gf) { gf.classList.add("hop"); setTimeout(() => gf.classList.remove("hop"), 1300); }
  if (id === "bomb" || id === "slipper") {   // explosion flash / slap: the whole seat shakes
    seatEl.classList.add("shake"); setTimeout(() => seatEl.classList.remove("shake"), 700);
    const av0 = seatEl.querySelector(".av");
    if (av0) { const f = document.createElement("div"); f.className = id === "bomb" ? "boomfx" : "slapfx"; av0.appendChild(f); setTimeout(() => f.remove(), 1100); }
  }
  const sp = SPLAT[id], av = seatEl.querySelector(".av");
  if (sp && av) {
    const s = document.createElement("div"); s.className = "splat"; s.innerHTML = splatSvg(sp[0], sp[1]); av.appendChild(s); setTimeout(() => s.remove(), 7500);
    const r = av.getBoundingClientRect();
    for (let i = 0; i < 9; i++) {   // droplets fly off the impact point
      const d = document.createElement("i"); d.className = "drop"; d.style.background = sp[0]; const sz = 3 + Math.random() * 5; d.style.cssText += `;width:${sz}px;height:${sz}px;background:${sp[0]}`; av.appendChild(d);
      const a = Math.random() * Math.PI * 2, dist = r.width * (.35 + Math.random() * .5);
      d.animate([{ transform: "translate(0,0) scale(1)", opacity: 1 }, { transform: `translate(${Math.cos(a) * dist}px,${Math.sin(a) * dist + 8}px) scale(.4)`, opacity: 0 }], { duration: 500 + Math.random() * 350, easing: "cubic-bezier(.2,.7,.4,1)" }).onfinish = () => d.remove();
    }
  }
}
const FLY_MS = 1700, gwaitUntil = {};  // gwaitUntil: receiver keeps its new gift hidden until the flying one lands
function giftSound(m) {
  if (m.blocked) return sfx.no();
  sfx.giftSend(m.gift);
  setTimeout(() => (m.to_uid === ME.id ? sfx.giftGot(m.gift) : sfx.giftHit(m.gift)), FLY_MS - 120);
  flyGift(m);
}
function flyGift(m) {
  if (!T || document.hidden) return;
  const ia = seatOf(m.uid), ib = seatOf(m.to_uid); if (ia < 0 || ib < 0 || ia === ib) return;
  const felt = $("#felt").getBoundingClientRect(), A = $("#seat" + ia).getBoundingClientRect(), eb = $("#seat" + ib), B = eb.getBoundingClientRect();
  const sx = A.left - felt.left + A.width / 2, sy = A.top - felt.top + A.height / 2;
  const gid = GIFT_BY_EMOJI[m.gift], head = (CFG.head_gifts || []).includes(gid);   // crowns: top-left, drinks: bottom-right, the rest: bottom-left
  const ex = B.left - felt.left + B.width * (head ? .1 : DRINK[gid] ? .86 : .14), ey = B.top - felt.top + B.height * (head ? .04 : .72);
  const mx = (sx + ex) / 2, my = Math.min(sy, ey) - Math.abs(ex - sx) * .16 - 16;
  const el = document.createElement("div"); el.className = "gfly"; el.innerHTML = giftIcon(m.gift); el.style.fontSize = A.width * .55 + "px";
  $("#felt").appendChild(el); eb.classList.add("gwait"); gwaitUntil[m.to_uid] = performance.now() + FLY_MS;
  const at = (x, y, s, r) => `translate(${x}px,${y}px) translate(-50%,-50%) scale(${s}) rotate(${r}deg)`;
  const an = el.animate([
    { transform: at(sx, sy, .4, -25), opacity: 0 },
    { transform: at(sx + (mx - sx) * .25, sy + (my - sy) * .35, .9, -12), opacity: 1, offset: .14 },
    { transform: at(mx, my, 1.55, 12), offset: .52 },
    { transform: at(ex, ey, 1, 0), opacity: 1 },
  ], { duration: FLY_MS, easing: "cubic-bezier(.32,.1,.25,1)", fill: "forwards" });
  an.onfinish = an.oncancel = () => {
    el.remove(); delete gwaitUntil[m.to_uid]; eb.classList.remove("gwait"); eb.classList.add("gland"); landFx(eb, m.gift); setTimeout(() => eb.classList.remove("gland"), 560);
  };
}
// pictures used in chat lines
const CHEV_SVG = `<svg viewBox="0 0 20 18"><path d="M3 3l6 6-6 6M11 3l6 6-6 6" fill="none" stroke="#8cc47a" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const NOTE_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="#f0a24a" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l11-2v12.500"/><ellipse cx="6" cy="18" rx="3" ry="2.600"/><ellipse cx="17" cy="15.500" rx="3" ry="2.600"/></svg>`;
const nameColor = m => m.g === "f" ? "#f2789f" : m.g === "m" ? "#58a6e4" : `hsl(${chatHue(m.name)} 62% 42%)`;
// "Show translation" appears only under messages written in another alphabet than the reader's language
const foreign = text => { const cyr = /[\u0400-\u04ff]/.test(text), lat = /[a-z]/i.test(text); return lang === "ru" ? lat && !cyr : cyr; };
const onlyEmoji = text => { try { const s = text.replace(/\s/g, ""); return s.length > 0 && s.length <= 20 && /^(?:\p{Extended_Pictographic}|\p{Emoji_Modifier}|\u200d|\ufe0f)+$/u.test(s); } catch { return false; } };
function addChat(m) {
  const box = $("#chat"), near = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
  const d = document.createElement("div");
  if (m.k === "msg") {
    if (m.uid !== ME.id) sfx.chat();
    const big = onlyEmoji(m.text);   // a message of smileys alone is shown large, without a bubble
    d.className = big ? "msg big" : "msg";
    d.innerHTML = `${miniAv(m.photo, m.name)}` + (big ? `<span class="bigemo">${esc(m.text)}</span>`
      : `<div class="bubble"><span class="who" style="color:${nameColor(m)}">${frameEmblem(m.fr)}${esc(m.name)}${m.vip ? " 👑" : ""}:</span> ${esc(m.text)}${foreign(m.text) ? `<span class="tr">${t("translate")}</span>` : ""}</div>`);
    const reply = () => { const i = $("#chat-input"); i.value = m.name + ", "; i.focus(); };
    if (!big) $(".who", d).onclick = reply;
    $(".av-mini", d).onclick = reply;
    const tr = $(".tr", d);
    if (tr) tr.onclick = () => openLink(`https://translate.google.com/?sl=auto&tl=${lang}&text=${encodeURIComponent(m.text)}&op=translate`);
  } else if (m.k === "gift") {
    // consecutive identical gifts from one sender collapse into one row: same receiver -> "x2", other receivers -> more avatars
    const key = `${m.uid}|${m.gift}`, last = box.lastElementChild;
    if (last && last.dataset.gk === key && !m.blocked) {
      const tos = (last.dataset.to || "").split(",");
      if (tos.includes(String(m.to_uid))) {
        const n = (parseInt(last.dataset.n) || 1) + 1; last.dataset.n = n;
        let x = $(".xn", last); if (!x) { x = document.createElement("span"); x.className = "xn"; $(".g", last).after(x); }
        x.textContent = "x" + n;
      } else {
        last.dataset.to = [...tos, m.to_uid].join(",");
        $(".giftline", last).insertAdjacentHTML("beforeend", miniAv(m.to_photo || seatPhoto(m.to_uid), m.to_name));
      }
      giftSound(m); if (near) box.scrollTop = box.scrollHeight; return;
    }
    d.className = "msg"; d.dataset.gk = key; d.dataset.to = String(m.to_uid);
    d.innerHTML = `${miniAv(m.photo || seatPhoto(m.uid), m.name)}<div class="bubble giftline"><span class="g">${giftIcon(m.gift)}</span><span class="ar">${CHEV_SVG}</span>${miniAv(m.to_photo || seatPhoto(m.to_uid), m.to_name)}${m.blocked ? `<small>🛡️ ${t("ev_gift_blocked")}</small>` : ""}</div>`;
    giftSound(m);
  } else if (m.k === "kiss") {
    d.className = "msg ev"; d.innerHTML = `${miniAv(m.photo || seatPhoto(m.uid), m.name)}<span class="kmark"><i>💋</i> <b>x${m.n || 1}</b></span><span class="ar">${CHEV_SVG}</span>${miniAv(m.to_photo || seatPhoto(m.to_uid), m.to_name)}`;
  } else if (m.k === "court") {
    d.className = "msg ev";
    d.innerHTML = `${miniAv(m.photo, m.name)}<span class="ico">💝</span><div>${esc(t("court_ev", { n: m.price }))}</div>${miniAv(m.to_photo || seatPhoto(m.to_uid), m.to_name)}`;
  } else if (m.k === "kick") {
    d.className = "msg ev"; d.innerHTML = `<span class="ico">👢</span><div>${esc(t("ev_kick", { a: m.name, b: m.to_name }))}</div>`;
    m.to_uid === ME.id ? sfx.error() : sfx.no();
  } else if (m.k === "rescue") {
    d.className = "msg ev"; d.innerHTML = `<span class="ico">🛟</span><div>${esc(t("ev_rescue", { a: m.name, b: m.to_name }))}</div>`; sfx.win();
  } else if (m.k === "kickout") {
    d.className = "msg ev"; d.innerHTML = `<span class="ico">🚪</span><div>${esc(t("ev_kickout", { n: m.name }))}</div>`;
  } else if (m.k === "dj") {
    d.className = "msg ev";
    d.innerHTML = `${miniAv(m.photo, m.name)}<span class="ico">🏅</span><div><b style="color:#f0a24a">DJ</b> ${esc(t("dj_level", { n: m.level }))}</div>`;
    sfx.win();
  } else if (m.k === "medal") {
    d.className = "msg ev";
    d.innerHTML = `${miniAv(m.photo || seatPhoto(m.uid), m.name)}<span class="ico mck"><svg viewBox="0 0 32 32"><path d="M16 2l4 2.500 4.700-.3 1.900 4.300 3.900 2.700-1 4.600 1 4.600-3.900 2.700-1.900 4.300-4.700-.3L16 30l-4-2.500-4.700.3-1.900-4.300L1.500 20.800l1-4.600-1-4.600 3.900-2.700 1.900-4.300L12 4.500z" fill="none" stroke="#f0a24a" stroke-width="2.200" stroke-linejoin="round"/><path d="M10 16.500l4 4 8-9" fill="none" stroke="#f0a24a" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></span><div><b style="color:#f0a24a">${esc(t("md_" + m.medal))}</b> ${esc(t("medal_level", { n: m.tier }))}</div>`;
  } else if (m.k === "boost") {
    boostFx(m.boost);
    d.className = "msg ev"; d.innerHTML = `${miniAv(m.photo || seatPhoto(m.uid), m.name)}<span class="ico">${BOOST_E[m.boost] || "✨"}</span><div>${esc(t("ev_" + m.boost, { n: m.name }))}</div>`;
  } else if (m.k === "music") {
    d.className = "msg ev mus"; d.innerHTML = `${miniAv(m.photo || seatPhoto(m.uid), m.name)}<span class="note">${NOTE_SVG}</span><div title="${esc(m.name)}">${esc(m.title)}</div>`;
  } else return;
  box.appendChild(d);
  while (box.children.length > 80) box.firstChild.remove();
  if (near || m.uid === ME.id) box.scrollTop = box.scrollHeight;
  else $("#newmsg").classList.remove("hidden");
}

// ------------------------------------------------------------ music (YouTube)
let yt, ytReady = false, curTid = "";
const yth = $("#yt-holder");
function placeVideo() {   // a video sits inside the player card in the boombox's place, small, like the original
  const on = !!(T && T.music && T.music.mode === "video" && !T.music.fid), box = $("#player"), slot = $("#player .pl-vslot");
  box.classList.toggle("isvideo", on); yth.classList.toggle("video", on);
  if (!on || !slot || box.classList.contains("hidden")) { yth.style.left = yth.style.top = yth.style.width = yth.style.height = ""; return; }
  const r = slot.getBoundingClientRect(); if (!r.width) return;
  Object.assign(yth.style, { left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px" });
}
window.addEventListener("resize", placeVideo);
new ResizeObserver(placeVideo).observe($("#player"));
$("#player").onclick = e => { if (e.target.closest("#pl-icon,#pl-range")) return; openMusicPicker("music_now", T && T.music && T.music.mode === "video" ? "video" : "audio"); };
const tga = new Audio(); tga.preload = "auto";
tga.onended = () => send({ t: "music_ended", tid: curTid });
function applyVolume() {
  const v = parseInt($("#pl-range").value);
  $("#pl-icon").innerHTML = `<svg viewBox="0 0 28 22" fill="#7d8894"><path d="M2 7.500h4.500L13 2v18l-6.500-5.500H2z"/>${v
    ? '<path d="M16.500 7c2 2.200 2 5.800 0 8M20 4c4 4 4 10 0 14" fill="none" stroke="#7d8894" stroke-width="2.200" stroke-linecap="round"/>'
    : '<path d="M17 8l7 6M24 8l-7 6" fill="none" stroke="#7d8894" stroke-width="2.400" stroke-linecap="round"/>'}</svg>`;
  tga.volume = v / 100; tga.muted = !v;
  if (tga.src && v && tga.paused && T && T.music && T.music.fid) tga.play().catch(() => { });
  if (!yt || !ytReady) return;
  if (v) { yt.unMute(); yt.setVolume(v); yt.playVideo(); } else yt.mute();
}
function loadYT(cb) {
  if (window.YT && YT.Player) return cb();
  window.onYouTubeIframeAPIReady = cb;
  const s = document.createElement("script"); s.src = "https://www.youtube.com/iframe_api"; document.head.appendChild(s);
}
function handleMusic() {
  const m = T.music, box = $("#player");
  $("#dj-fab").classList.toggle("covered", !!m);   // as in the original: the player card takes the place of the two buttons
  if (!m) { box.classList.add("hidden"); if (yt && ytReady && curTid) { try { yt.stopVideo(); } catch {} } tga.pause(); curTid = ""; placeVideo(); return; }
  box.classList.remove("hidden"); placeVideo();
  $("#pl-title").textContent = m.title; $("#pl-by").textContent = m.by + (T.queue ? ` · +${T.queue}` : "");
  const who = T.seats.find(p => p.name === m.by);
  $("#pl-cover").innerHTML = who && who.photo ? `<img src="${esc(who.photo)}">` : `<span>${esc(initials(m.by))}</span>`;
  if (m.tid === curTid) return;
  curTid = m.tid; placeVideo(); requestAnimationFrame(placeVideo); setTimeout(placeVideo, 400);
  if (m.fid) {   // Telegram profile track: plain audio element, no YouTube
    if (yt && ytReady) { try { yt.stopVideo(); } catch { } }
    tga.src = `/api/tgaudio/${encodeURIComponent(m.fid)}?init=${encodeURIComponent(initData)}`; applyVolume();
    return;
  }
  tga.pause();
  loadYT(() => {
    if (yt) { yt.loadVideoById(m.vid); applyVolume(); return; }
    yt = new YT.Player("yt", {
      width: 200, height: 200, videoId: m.vid, playerVars: { autoplay: 1, controls: 0, playsinline: 1 },
      events: {
        onReady: () => { ytReady = true; yt.mute(); yt.playVideo(); applyVolume(); },
        onStateChange: e => { if (e.data === 0) send({ t: "music_ended", tid: curTid }); },
      },
    });
  });
}

// ------------------------------------------------------------ gifts panel
function openGifts(uid) {
  if (!T || !T.seats.find(p => p.uid === uid)) return toast(t("not_here"));
  target = uid; updateGiftHead(); renderSeats();
  $("#gift-panel").classList.remove("hidden");
  const g = $("#gift-grid"); g.innerHTML = "";
  CFG.gifts.forEach(x => {
    const locked = x.vip && !ME.vip;
    const b = document.createElement("button"); b.className = "gi" + (locked ? " lock" : "");
    b.innerHTML = `<span class="e">${giftIcon(x.id)}</span><span class="p">${locked ? "🔒" : "❤️" + x.price}</span>`;
    b.onclick = () => giveGift(x);
    g.appendChild(b);
  });
}
function updateGiftHead() {
  const p = T && T.seats.find(s => s.uid === target);
  $("#gp-name").textContent = p ? p.name : t("pick_player");
  $("#gp-av").innerHTML = p ? (p.photo ? `<img src="${esc(p.photo)}">` : esc(initials(p.name))) : "";
}
function closeGifts() { target = 0; $("#gift-panel").classList.add("hidden"); if (T && T.seats) renderSeats(); }

function giveGift(g) {
  if (!target && !g.kind.startsWith("music")) return toast(t("pick_player"));
  if (g.vip && !ME.vip) { toast(t("need_vip")); return openVip(); }
  if (ME.hearts < g.price) { toast(t("no_hearts")); return openShop(); }
  if (g.kind.startsWith("music")) return openMusicPicker(g.id, g.id === "music_now" ? "video" : "audio");   // original panel: first item = video (❤9), second = music (❤5)
  send({ t: "gift", to: target, gift: g.id });
}

// ------------------------------------------------------------ gestures (own avatar tap)
function openGestures() {
  closeGifts(); $("#bottle-panel").classList.add("hidden");
  $("#gs-label").textContent = t("gesture_title"); $("#gest-panel").classList.remove("hidden"); renderGestures();
}
function renderGestures() {
  $("#gs-n").textContent = ME.smiles;
  const g = $("#gest-grid"); g.innerHTML = "";
  CFG.gestures.forEach(x => {
    const locked = (x.vip && !ME.vip) || (x.stat && (ME[x.stat] || 0) < x.need);
    const b = document.createElement("button"); b.className = "gs" + (locked ? " lock" : "") + (x.vip ? " vip" : "");
    b.innerHTML = `<span class="e">${x.emoji}</span>${locked ? '<span style="font-size:20px;opacity:.6">🔒</span>' : `<b>😊 ${x.price}</b>`}`;
    b.onclick = () => {
      if (locked) return toast(t(x.vip && !ME.vip ? "need_vip" : "gesture_locked"));
      if (ME.smiles < x.price) return toast(t("no_smiles"));
      send({ t: "gesture", id: x.id }); $("#gest-panel").classList.add("hidden");
    };
    g.appendChild(b);
  });
}
$("#gs-close").onclick = () => $("#gest-panel").classList.add("hidden");
$("#gs-smiles").onclick = () => openVip();

// ------------------------------------------------------------ music picker
const favKey = mode => mode === "video" ? "favVideos" : "favTracks";
const favTracks = mode => { try { return JSON.parse(ls.get(favKey(mode), "[]")); } catch { return []; } };
const fmtDur = s => s ? Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0") : "";
// Music and video are two separate screens: each opens only its own list (music has the Telegram-profile tab, video does not).
function openMusicPicker(kind, mode = "audio") {
  const gOf = () => CFG.gifts.find(x => x.id === kind); let g = gOf(); if (!g) return;
  if (ME.hearts < Math.min(...["music_now", "music_queue"].map(k => CFG.gifts.find(x => x.id === k).price))) { toast(t("no_hearts")); return openShop(); }
  const video = mode === "video", m = openModal("", { cls: "mpick" });
  const ytId = v => (v.match(/(?:youtu\.be\/|v=|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})/) || [])[1];
  const TI = {   // tab pictures (our own)
    pop: `<svg viewBox="0 0 32 32"><path d="M17 2c1 6 9 9 9 18a10 10 0 0 1-20 0c0-5 3-8 5-10 0 3 1 5 3 6 0-6 1-10 3-14z" fill="currentColor"/><path d="M16 18c2 3 5 4 5 7a5 5 0 0 1-10 0c0-3 3-4 5-7z" fill="#fff" opacity=".45"/></svg>`,
    fav: `<svg viewBox="0 0 32 32"><path d="M16 3l4 8.500 9 1.200-6.500 6.300 1.700 9L16 23.700 7.800 28l1.700-9L3 12.700l9-1.200z" fill="currentColor"/></svg>`,
    hist: `<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" fill="currentColor"/><path d="M16 8.500V16l5.500 3.500" fill="none" stroke="#fff" stroke-width="2.800" stroke-linecap="round"/></svg>`,
    find: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="3.600" stroke-linecap="round"><circle cx="13.500" cy="13.500" r="9"/><path d="M20.500 20.500L28 28"/></svg>`,
    tg: `<svg viewBox="0 0 32 32" fill="currentColor"><circle cx="16" cy="10.500" r="6.500"/><path d="M4 28c1-7.500 6-10.500 12-10.500S27 20.500 28 28z"/></svg>`,
  };
  const STAR = `<svg viewBox="0 0 32 32"><path d="M16 4l3.700 7.600 8.300 1.200-6 5.800 1.400 8.300L16 23l-7.400 3.900L10 18.600l-6-5.800 8.300-1.200z"/></svg>`;
  let tab = "pop", list = [], findQ = "";
  const thumb = v => `https://i.ytimg.com/vi/${v}/mqdefault.jpg`;
  const pick = (vid, tgFid) => {
    g = gOf(); if (ME.hearts < g.price) { toast(t("no_hearts")); return openShop(); }
    send({ t: "gift", to: 0, gift: kind, url: tgFid ? "tg:" + tgFid : "https://youtu.be/" + vid, mode }); m.close();
  };
  const load = async () => {
    list = tab === "fav" ? favTracks(mode) : tab === "find" ? []
      : tab === "tg" ? await api("/api/music/tg").catch(() => [])
      : await api((tab === "hist" ? "/api/music/history" : "/api/music/popular") + "?mode=" + mode).catch(() => []);
    render();
  };
  const render = () => {
    g = gOf(); const playing = !!(T && T.music), favs = new Set(favTracks(mode).map(x => x.vid));
    const tabs = video ? ["pop", "fav", "hist", "find"] : ["pop", "fav", "tg", "hist", "find"];
    const titles = { pop: t(video ? "video_popular" : "music_popular"), fav: t("music_saved"), hist: t("music_history"), find: t("music_find"), tg: t("music_tg") };
    const price = k => CFG.gifts.find(x => x.id === k).price;
    const grid = list.length ? (tab === "tg"
      ? `<div class="mp-rows">${list.map(x => `<div class="mp-row" data-f="${esc(x.fid)}"><div><b>${esc(x.title)}</b><small>${esc(x.artist)}</small></div><span>${fmtDur(x.dur)}</span></div>`).join("")}</div>`
      : `<div class="mp-grid">${list.map(x => `<div class="mp-card" data-v="${x.vid}"><div class="mp-th"><img loading="lazy" src="${thumb(x.vid)}"><button class="mp-star ${favs.has(x.vid) ? "on" : ""}" data-star="${x.vid}" aria-label="★">${STAR}</button></div><div class="mp-tt">${esc(x.title)}</div></div>`).join("")}</div>`)
      : `<p class="mp-empty">${esc(tab === "tg" ? t("music_tg_empty") : tab === "find" ? t("mp_find_hint") : t("no_tracks"))}</p>`;
    m.set(`<div class="mp-tabs">${tabs.map(k => `<button data-tab="${k}" class="tab-${k} ${k === tab ? "on" : ""}">${TI[k]}</button>`).join("")}</div>
      ${playing ? `<div class="mp-seg sm" id="mp-kind"><button data-k="music_now" class="${kind === "music_now" ? "on" : ""}">${esc(t("mp_replace"))} · ❤${price("music_now")}</button><button data-k="music_queue" class="${kind === "music_queue" ? "on" : ""}">${esc(t("mp_queue"))} · ❤${price("music_queue")}</button></div>` : ""}
      <p class="mp-title">${esc(titles[tab])}<span>❤${price(kind)}</span></p>
      ${tab === "find" ? `<form class="mp-find" id="mp-form"><input id="mp-q" placeholder="${esc(t("mp_find_link"))}" value="${esc(findQ)}" autocomplete="off"><button class="btn">${TI.find}</button></form>` : ""}
      <div class="mp-scroll">${grid}</div>`);
    $$("#mp-kind [data-k]", m.el).forEach(b => b.onclick = () => { kind = b.dataset.k; render(); });
    $$("[data-tab]", m.el).forEach(b => b.onclick = () => { tab = b.dataset.tab; load(); });
    $$("[data-star]", m.el).forEach(b => b.onclick = e => {
      e.stopPropagation(); const v = b.dataset.star, cur = favTracks(mode), item = list.find(x => x.vid === v);
      ls.set(favKey(mode), JSON.stringify(cur.some(x => x.vid === v) ? cur.filter(x => x.vid !== v) : [...cur, { vid: v, title: item ? item.title : v }]));
      if (tab === "fav") list = favTracks(mode); render();
    });
    $$("[data-v]", m.el).forEach(c => c.onclick = () => pick(c.dataset.v));
    $$("[data-f]", m.el).forEach(c => c.onclick = () => pick("", c.dataset.f));
    const fm = $("#mp-form", m.el);
    if (fm) fm.onsubmit = async e => {
      e.preventDefault(); findQ = $("#mp-q", m.el).value.trim();
      const link = ytId(findQ); if (link) return pick(link);   // a pasted YouTube link plays straight away
      if (findQ.length < 2) return;
      list = await api("/api/music/search?q=" + encodeURIComponent(findQ + (video ? " video" : ""))).catch(() => []); render(); $("#mp-q", m.el).focus();
    };
  };
  load();
}

// ------------------------------------------------------------ modals
function trophyChips(tr) {   // weekly-top medals earned (1st/2nd/3rd place counts)
  const med = { 1: "🥇", 2: "🥈", 3: "🥉" }, items = [1, 2, 3].filter(p => tr && tr[p]).map(p => `<span>${med[p]}${tr[p] > 1 ? " ×" + tr[p] : ""}</span>`);
  return items.length ? `<div class="tro">${items.join("")}<small>${esc(t("weekly_top"))}</small></div>` : "";
}
async function openProfile(uid) {
  let c; try { c = await api("/api/user/" + uid); } catch { return toast(t("err")); }
  const me = uid === ME.id, m = openModal("", { cls: "prof" });
  let more = false;
  const render = () => {
    const fr = c.frame ? "fr-" + c.frame.replace("frame_", "") : "";
    const sp = c.suitor;
    m.set(`<div class="ph ${fr}">${c.top ? `<span class="vrib top">TOP</span>` : c.vip ? `<span class="vrib">VIP</span>` : ""}${c.photo ? `<img src="${esc(c.photo)}" referrerpolicy="no-referrer" onerror="this.remove()">` : ""}<span class="big">${esc(initials(c.name))}</span>
        <div class="pn">${esc(c.name)}${c.age ? ", " + c.age : ""}${c.top ? " 🏆" : c.vip ? " 👑" : ""}</div>${me ? "" : `<button class="rep" id="pf-rep">!</button>`}</div>
      <div class="pb">
        ${rankLine(c.kisses, c.rank || 0)}
        ${trophyChips(c.trophies)}
        ${(more ? RATINGS : ["kisses", "dj", "emotion"]).map(k => `<div class="pst ${k}">${RT_ICON[k]}<b>${num(c.stats[k])}</b>${c.ranks[k] ? `<small>${esc(t("rt_place", { n: num(c.ranks[k]) }))}</small>` : ""}</div>`).join("")}
        <div class="chev"><button id="pf-more">${more ? "︿" : "﹀"}</button></div>
        ${more && c.gifts.length ? `<div class="gbox">${c.gifts.slice(0, 40).map(g => `<span class="gchip">${giftIcon(g.emoji)}<b>${g.n}</b></span>`).join("")}</div>` : ""}
        <div class="suit">
          <div class="sa">${sp ? (sp.photo ? `<img src="${esc(sp.photo)}" referrerpolicy="no-referrer">` : esc(initials(sp.name))) : "♡"}</div>
          <div class="si">${sp ? `<div class="l">${esc(t("courting"))} <b>${esc(sp.name)}</b></div>` : `<div class="l">${t("court_none")}</div>`}
            <div class="h">${RT_ICON.dear}<b>${num(c.court_next)}</b>${c.ranks.dear ? `<small>${esc(t("rt_place", { n: num(c.ranks.dear) }))}</small>` : ""}</div>
            ${me ? (sp ? `<button class="btn out" id="pf-decl">${t("court_decline")}</button>` : "") : sp && sp.id === ME.id ? `<button class="btn" disabled>${t("court_mine")}</button>` : `<button class="btn" id="pf-court">${t("court_btn")}</button>`}</div>
        </div>
        <div class="acts">
          ${me ? `<button class="a4" id="pf-edit" style="width:100%;border-radius:36px">${t("profile_settings")}</button>` :
            `<button class="a1" id="pf-pc">${ICON.kick}</button><button class="a2" id="pf-gift">${ICON.music}</button><button class="a3" id="pf-ach">${ICON.badge}</button><button class="a4" id="pf-mail">${ICON.mail}</button>`}
        </div></div>`);
    const on = (id, fn) => { const e = $(id, m.el); if (e) e.onclick = fn; };
    on("#pf-more", () => { more = !more; render(); });
    on("#pf-rep", () => openReport(uid));
    on("#pf-pc", () => openKick({ ...c, id: uid }));
    on("#pf-gift", () => { m.close(); openGifts(uid); });
    on("#pf-ach", () => showAchievementsOf(c));
    on("#pf-mail", () => { m.close(); openPm(c); });
    on("#pf-edit", () => { m.close(); profileModal(false); });
    on("#pf-decl", async () => {
      try { const r = await api("/api/court/decline", "POST"); ME = r.me; renderMe(); c = await api("/api/user/" + uid); render(); }
      catch (e) { if (e.code === "no_hearts") { toast(t("no_hearts")); m.close(); openShop(); } else toast(t("err")); }
    });
    on("#pf-court", async () => {
      try { const r = await api("/api/court", "POST", { to: uid }); ME = r.me; renderMe(); c = await api("/api/user/" + uid); sfx.gift(); render(); }
      catch (e) { if (e.code === "no_hearts") { toast(t("no_hearts")); m.close(); openShop(); } else if (e.code === "already") toast(t("courting") + " ✓"); else toast(t("err")); }
    });
  };
  render();
}

// ------------------------------------------------------------ kick & rescue
function kickFreeIn() {   // seconds until the next free kick (0 = ready)
  const elapsed = Math.max(0, serverNow() / 1000 - (ME.server_time || 0));
  return Math.max(0, Math.ceil((ME.kick_free_in || 0) - elapsed));
}
function openKick(c) {
  const K = CFG.kick;
  if (!T || !T.seats.find(s => s.uid === c.id)) return toast(t("not_here"));
  if (T.kicks && T.kicks.find(k => k.uid === c.id)) return toast(t("kick_pending"));
  const free = kickFreeIn() === 0, left = kickFreeIn(), pct = free ? 100 : Math.max(4, Math.round((1 - left / K.free_every) * 100));
  const mm = Math.floor(left / 60), ss = String(left % 60).padStart(2, "0");
  const m = openModal(`<button class="qhelp dark" id="kk-help">?</button><h2>${esc(t("kick_title"))}</h2>
    <div class="kk-body"><div class="kk-av">${c.photo ? `<img src="${esc(c.photo)}" referrerpolicy="no-referrer" onerror="this.remove()">` : esc(initials(c.name))}<i>${ICON.kick}</i></div>
      <p>${t("kick_q", { n: `<b>${esc(c.name)}</b>`, s: `<b>${K.delay}</b>`, m: `<b>${K.ban_min}</b>` })}</p></div>
    <p class="kk-warn">${esc(t("kick_warn"))}</p>
    <div class="kk-bar"><span class="kk-ic">${ICON.kick}</span><div class="kk-track"><i style="width:${pct}%"></i></div><b class="kk-ok ${free ? "on" : ""}">${free ? "✓" : "⏳"}</b></div>
    <p class="kk-note">${free ? esc(t("kick_free")) : `${esc(t("kick_wait", { t: mm + ":" + ss }))} · ${esc(t("kick_cost", { p: K.price }))}`}</p>
    <div class="kk-btns"><button class="btn out" id="kk-no">${esc(t("kick_cancel"))}</button><button class="btn" id="kk-go">${esc(t("kick_go"))}${free ? "" : " ❤" + K.price}</button></div>`, { cls: "kick", closable: false });
  $("#kk-help", m.el).onclick = () => toast(t("kick_help", { s: K.delay, m: K.ban_min, r: K.rescue, f: Math.round(K.free_every / 60) }), 6000);
  $("#kk-no", m.el).onclick = m.close;
  $("#kk-go", m.el).onclick = () => { send({ t: "kick", to: c.id }); closeAllModals(); };
}
let kickAt = 0;
function renderKickBar() {
  let el = $("#kickbar");
  if (!T || !T.kicks || !T.kicks.length) { if (el) el.remove(); return; }
  if (!el) { el = document.createElement("div"); el.id = "kickbar"; el.className = "in"; $("#felt").appendChild(el); }
  const K = CFG.kick, passed = (performance.now() - kickAt) / 1000;
  el.innerHTML = T.kicks.map(k => {
    const s = Math.max(0, Math.ceil(k.left - passed)), mine = k.uid === ME.id, name = nameOf(k.uid);
    return `<div class="kb-row ${mine ? "me" : ""}"><span>${esc(mine ? t("kick_banner_me", { s }) : t("kick_banner", { n: name, s }))}</span>${mine || k.by === ME.id ? "" : `<button class="btn" data-r="${k.uid}">${esc(t("rescue_btn", { p: K.rescue }))}</button>`}</div>`;
  }).join("");
  el.onclick = e => { const b = e.target.closest("[data-r]"); if (b) send({ t: "rescue", to: +b.dataset.r }); };
}

function showAchievementsOf(c) {
  const rows = CFG.achievements.map(a => `<div class="card2"><span style="font-size:26px">${c.ach.includes(a.id) ? "✅" : "🔒"}</span><b>${t("achs_" + a.stat, { n: a.need })}</b></div>`).join("");
  openModal(`<h2>${esc(c.name)}</h2>${rows}`);
}

function openPm(c) {
  const m = openModal(`<h2>💌 ${t("compl_title")} · ${esc(c.name)}</h2><textarea class="pmtxt" id="pm-text" maxlength="200"></textarea><p class="sub">${t("compl_hint")}</p><button class="btn wide" id="pm-go">${t("compl_send")}</button>`);
  $("#pm-go", m.el).onclick = async () => {
    const v = $("#pm-text", m.el).value.trim(); if (!v) return;
    try { const r = await api("/api/compliment", "POST", { to: c.id, text: v }); ME = r.me; renderMe(); toast(t("compl_sent")); m.close(); }
    catch (e) { if (e.code === "no_hearts") { toast(t("no_hearts")); m.close(); openShop(); } else toast(e.code === "too_fast" ? t("too_fast") : e.code === "limit" ? t("limit_c") : e.code === "muted" ? t("muted") : String(e.code).startsWith("filtered_") ? t(e.code) : t("err")); }
  };
  setTimeout(() => $("#pm-text", m.el).focus(), 50);
}

let complQueue = [], complOpen = false;
function showCompliment(c) { complQueue.push(c); nextCompliment(); }
function nextCompliment() {
  if (complOpen || !complQueue.length) return;
  const c = complQueue.shift(); complOpen = true;
  const m = openModal(`<div class="center" style="font-size:54px">💌</div><h2 style="color:#e8873a">${esc(t("compl_from", { name: c.name }))}</h2>
    <div class="card2" style="align-items:flex-start">${miniAv(c.photo, c.name)}<b style="font-weight:600;font-size:17px;line-height:1.3">${esc(c.text)}</b></div>
    <button class="btn wide" id="cm-ok">${t("compl_claim")}</button>`, { onclose: () => { complOpen = false; setTimeout(nextCompliment, 250); } });
  $("#cm-ok", m.el).onclick = async () => {
    try { ME = await api(`/api/compliments/${c.id}/read`, "POST"); renderMe(); sfx.win(); } catch {}
    m.close();
  };
}
async function loadCompliments() {
  try { (await api("/api/compliments/unread")).forEach(c => complQueue.push(c)); nextCompliment(); } catch {}
}

function openCourtPop(m) {
  const pop = openModal(`<h2>${t("court_title")}</h2><div class="court-pop"><div class="ca"><div class="bx">${miniAv(m.photo, m.name)}<div style="margin-top:4px">${esc(m.name)}</div></div>
    <p>${esc(t("court_notice", { name: m.name, n: m.price }))}</p></div><button class="btn" id="cp-ok">${t("got_it")}</button></div>`);
  $("#cp-ok", pop.el).onclick = pop.close; sfx.gift();
}

function profileModal(first = false) {
  return new Promise(res => {
    let gender = ME.gender || "", photo = ME.photo || "";
    const tgName = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.first_name : "";
    const initial = { name: ME.name || tgName, birth: ME.birth || "", gender };
    const maxBirth = new Date(Date.now() - 14 * 365.25 * 864e5).toISOString().slice(0, 10);
    const m = openModal(`<h2>${t("profile_settings")}</h2><div class="pfx">
      <div class="pfx-l"><div class="pfx-ph" id="pf-ph"></div><button class="pfx-plus" id="pf-pick">+</button><div class="pfx-cap">${t("choose_photo")}</div>
        <input type="file" id="pf-file" accept="image/*" hidden></div>
      <div class="pfx-r">
        <label class="field"><span>${t("name")}:</span><input id="pf-name" maxlength="24" value="${esc(initial.name)}"></label>
        <label class="field"><span>${t("birth")}:</span><input id="pf-birth" type="date" min="1940-01-01" max="${maxBirth}" value="${esc(initial.birth)}"></label>
        <div class="field"><span>${t("gender")}:</span><div class="gtile"><button data-g="m" aria-label="m">👦</button><button data-g="f" aria-label="f">👧</button></div></div>
      </div></div>
      <div class="pfx-btns">${first ? "" : `<button class="btn ghost" id="pf-cancel">${t("cancel_btn")}</button>`}<button class="btn" id="pf-save">${t("save")}</button></div>`, { closable: !first, onclose: () => res() });
    const paintPh = () => { $("#pf-ph", m.el).innerHTML = photo ? `<img src="${esc(photo)}" referrerpolicy="no-referrer">` : `<div class="ini">${esc(initials($("#pf-name", m.el).value || ME.name))}</div>`; };
    const dirty = () => first || $("#pf-name", m.el).value.trim() !== initial.name || $("#pf-birth", m.el).value !== initial.birth || gender !== initial.gender;
    const refresh = () => {
      $$("[data-g]", m.el).forEach(b => b.classList.toggle("on", b.dataset.g === gender));
      $("#pf-save", m.el).disabled = !dirty();
    };
    paintPh(); refresh();
    $$("[data-g]", m.el).forEach(b => b.onclick = () => { gender = b.dataset.g; refresh(); });
    $("#pf-name", m.el).oninput = () => { refresh(); if (!photo) paintPh(); };
    $("#pf-birth", m.el).oninput = refresh;
    const cancel = $("#pf-cancel", m.el); if (cancel) cancel.onclick = m.close;
    $("#pf-pick", m.el).onclick = () => $("#pf-file", m.el).click();
    $("#pf-file", m.el).onchange = async e => {   // square-crop + shrink in the browser, the server re-encodes again
      const f = e.target.files[0]; if (!f) return;
      try {
        const bmp = await createImageBitmap(f), side = Math.min(bmp.width, bmp.height), c = document.createElement("canvas");
        c.width = c.height = Math.min(640, side); c.getContext("2d").drawImage(bmp, (bmp.width - side) / 2, (bmp.height - side) / 2, side, side, 0, 0, c.width, c.height);
        const blob = await new Promise(r => c.toBlob(r, "image/jpeg", .86));
        const r = await fetch("/api/photo", { method: "POST", headers: { "Content-Type": "image/jpeg", "X-Init-Data": initData }, body: blob });
        if (!r.ok) throw new Error(r.status);
        ME = await r.json(); photo = ME.photo; paintPh(); renderMe(); toast("✓");
      } catch { toast(t("err")); }
    };
    $("#pf-save", m.el).onclick = async () => {
      const birth = $("#pf-birth", m.el).value, name = $("#pf-name", m.el).value.trim();
      if (!birth) return toast(t("age_err"));
      if (!name || !gender) return toast(t("err"));
      try {
        ME = await api("/api/profile", "POST", { name, birth, gender, lang });
        applyStatic(); renderMe(); m.close();
      } catch (e) { toast(e.code === "invalid" ? t("age_err") : e.code === "bad_name" ? t("bad_name") : t("err")); }
    };
  });
}

const heartNum = n => `<span class="hb"><svg viewBox="0 0 40 36"><path d="M20 35C6 25 1 16 1 10 1 4 6 1 11 1c4 0 7 2 9 6 2-4 5-6 9-6 5 0 10 3 10 9 0 6-5 15-19 25z" fill="url(#hg)" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg><b>${n}</b></span>`;
function openDaily() {
  if (!ME.daily.available) return;
  const day = ME.daily.day, mult = ME.vip ? 2 : 1;
  const rows = CFG.daily.map((h, i) => `<div class="drow ${i <= day ? "now" : ""}"><span class="dot">${i < day ? "✔" : ""}</span><span class="dl">${t("day", { n: i + 1 })}</span>${heartNum(h * mult)}</div>`).join("");
  // like the original: no close button, the dialog goes away only after claiming
  const m = openModal(`<h2>${t("daily_title")}</h2><p class="dtxt pre">${t("daily_desc")}</p>${rows}
    <div class="center dfoot"><button class="btn dbtn" id="dl-ok">${t("claim")}</button></div>`, { cls: "green daily", closable: false });
  $("#dl-ok", m.el).onclick = async () => {
    try { const r = await api("/api/daily/claim", "POST"); ME = r.me; renderMe(); toast(t("daily_ok", { n: r.reward })); sfx.win(); m.close(); }
    catch { m.close(); }
  };
}

function shopTasks() {   // starter and daily tasks: free hearts, so they live in the hearts window
  const row = (go, icon, title, list, done, ready) => list.length ? `<button class="stask ${list.some(ready) ? "ready" : ""}" data-go="${go}"><i>${icon}</i><span>${esc(t(title))}</span><b>${list.filter(done).length}/${list.length}</b></button>` : "";
  const html = row("starter", "🎯", "st_title", ME.starter || [], x => x.claimed, x => x.done && !x.claimed) + row("dtask", "📅", "dt_title", ME.dtasks || [], x => x.claimed, x => x.n >= x.goal && !x.claimed);
  return html && `<div class="shop-tasks">${html}</div>`;
}
const SHOP_ART = {
  p5000: `<svg viewBox="0 0 64 64"><path transform="translate(22 24) scale(0.9)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/><path transform="translate(42 22) scale(1.0)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ff6a4d" stroke="#fff" stroke-width="1.200"/><path transform="translate(32 17) scale(0.95)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#d9362a" stroke="#fff" stroke-width="1.200"/><rect x="8" y="26" width="48" height="26" rx="4" fill="#8e44ad"/><rect x="8" y="26" width="48" height="8" fill="#f4b52c"/><rect x="14" y="26" width="6" height="26" fill="#f4b52c"/><rect x="44" y="26" width="6" height="26" fill="#f4b52c"/><rect x="27" y="31" width="10" height="11" rx="2" fill="#ffd86b" stroke="#8a5a00" stroke-width="1.500"/><path transform="translate(52 48) scale(0.8)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/></svg>`,
  p2500: `<svg viewBox="0 0 64 64"><path transform="translate(22 24) scale(0.9)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/><path transform="translate(42 22) scale(1.0)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ff6a4d" stroke="#fff" stroke-width="1.200"/><path transform="translate(32 17) scale(0.95)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#d9362a" stroke="#fff" stroke-width="1.200"/><path d="M14 26h36c5 8 5 20 0 28H14c-5-8-5-20 0-28z" fill="#a8652d"/><path d="M12.500 32h39M12.500 48h39" stroke="#f4b52c" stroke-width="4"/><path d="M24 27v26M40 27v26" stroke="#7d4718" stroke-width="2"/><path transform="translate(32 40) scale(0.75)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#f4b52c" stroke="#fff" stroke-width="1.200"/><path transform="translate(52 49) scale(0.8)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/></svg>`,
  p1000: `<svg viewBox="0 0 64 64"><path transform="translate(22 24) scale(0.9)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/><path transform="translate(42 22) scale(1.0)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ff6a4d" stroke="#fff" stroke-width="1.200"/><path transform="translate(32 17) scale(0.95)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#d9362a" stroke="#fff" stroke-width="1.200"/><path d="M16 28h32c8 5 9 22-4 26H20C7 50 8 33 16 28z" fill="#5b4fc4"/><rect x="13" y="25" width="38" height="7" rx="3.500" fill="#7a6ee0"/><circle cx="12" cy="38" r="4" fill="none" stroke="#7a6ee0" stroke-width="3"/><circle cx="52" cy="38" r="4" fill="none" stroke="#7a6ee0" stroke-width="3"/><path transform="translate(32 42) scale(0.7)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#f4c52c" stroke="#fff" stroke-width="1.200"/><path transform="translate(52 50) scale(0.8)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/></svg>`,
  p500: `<svg viewBox="0 0 64 64"><path transform="translate(32 18) scale(1.0)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/><path d="M24 26h16c10 6 16 14 14 22-2 8-42 8-44 0-2-8 4-16 14-22z" fill="#d3304a"/><path d="M22 26q10 5 20 0" stroke="#f4b52c" stroke-width="4" fill="none" stroke-linecap="round"/><path transform="translate(46 47) scale(0.8)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ff6a4d" stroke="#fff" stroke-width="1.200"/></svg>`,
  p250: `<svg viewBox="0 0 64 64"><path transform="translate(22 24) scale(0.9)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/><path transform="translate(42 22) scale(1.0)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ff6a4d" stroke="#fff" stroke-width="1.200"/><path transform="translate(32 17) scale(0.95)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#d9362a" stroke="#fff" stroke-width="1.200"/><path d="M12 30h40v22H12z" fill="#f4b52c"/><path d="M12 30l-6 7 13 4 7-11zM52 30l6 7-13 4-7-11z" fill="#ffd25c"/><path d="M12 42h40" stroke="#d98f10" stroke-width="2"/><path transform="translate(50 48) scale(0.8)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/></svg>`,
  p50: `<svg viewBox="0 0 64 64"><path transform="translate(20 40) scale(1.15)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ff6a4d" stroke="#fff" stroke-width="1.200"/><path transform="translate(44 40) scale(1.15)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/><path transform="translate(32 30) scale(1.35)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#e0392c" stroke="#fff" stroke-width="1.200"/></svg>`,
  vip: `<svg viewBox="0 0 64 64"><path d="M32 4l22 12v20c0 12-10 20-22 24-12-4-22-12-22-24V16z" fill="#b9bdf0"/><path d="M32 10l16 9v16c0 9-7 15-16 18-9-3-16-9-16-18V19z" fill="#d9dcfb"/><text x="32" y="39" text-anchor="middle" font-size="15" font-weight="900" fill="#6a6fb8" font-family="Arial,sans-serif">VIP</text><circle cx="32" cy="12" r="7" fill="#8fc63f" stroke="#fff" stroke-width="2"/><path d="M32 9v6M29 12h6" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>`,
  friend: `<svg viewBox="0 0 64 64"><rect x="6" y="16" width="26" height="34" rx="4" fill="#cfd8ee" transform="rotate(-9 19 33)"/><rect x="32" y="16" width="26" height="34" rx="4" fill="#cfd8ee" transform="rotate(9 45 33)"/><rect x="18" y="14" width="28" height="38" rx="4" fill="#fff" stroke="#9fb0d8" stroke-width="2"/><circle cx="32" cy="28" r="7" fill="#e9b184"/><path d="M21 49c1-9 5-12 11-12s10 3 11 12z" fill="#5f7fd0"/><circle cx="14" cy="18" r="8" fill="#8fc63f" stroke="#fff" stroke-width="2"/><path d="M14 14.500v7M10.500 18h7" stroke="#fff" stroke-width="2.200" stroke-linecap="round"/></svg>`,
  mail: `<svg viewBox="0 0 64 64"><path d="M14 12h36v26H14z" fill="#fff" stroke="#e3c9a0" stroke-width="1.500"/><path transform="translate(25 24) scale(0.65)" d="M0 9C-12 0-9-9-4.500-9C-2-9 0-7 0-5C0-7 2-9 4.500-9C9-9 12 0 0 9Z" fill="#ee4b3a" stroke="#fff" stroke-width="1.200"/><path d="M35 21h10M35 27h10" stroke="#c9c9c9" stroke-width="2.500"/><path d="M6 24l26 19 26-19v30H6z" fill="#f6dcae"/><path d="M6 54l21-17M58 54L37 37" stroke="#d9b678" stroke-width="2" fill="none"/><path d="M6 54h52" stroke="#e5534a" stroke-width="3" stroke-dasharray="6 5"/></svg>`,
};   // our own drawings for the heart shop
function openShop() {
  const packs = [...CFG.packs].sort((a, b) => b.stars - a.stars);
  const m = openModal(`<h2>${t("buy_hearts")}</h2>
    <div class="grid3" style="margin-bottom:10px">
      <div class="pack"><div class="txt" style="color:#e8873a;font-weight:800">${t("vip_status")}</div><div class="em">${SHOP_ART.vip}</div><button class="btn blue" data-go="vip">${t("learn")}</button>${ME.vip ? "" : `<span class="vbadge">!</span>`}</div>
      <div class="pack"><div class="txt">${t("get_friend", { n: 20 })}</div><div class="em">${SHOP_ART.friend}</div><button class="btn blue" data-go="promo">${t("learn")}</button></div>
      <div class="pack"><div class="txt">${t("get_comp", { n: 10 })}</div><div class="em">${SHOP_ART.mail}</div><button class="btn blue" data-go="compl">${t("learn")}</button></div>
    </div>
    ${shopTasks()}
    <div class="grid3">${packs.map(p => `<div class="pack">
      ${p.stars === 5000 ? `<span class="tag">${t("best")}</span>` : p.stars === 1000 ? `<span class="tag hit">${t("hit")}</span>` : ""}
      <div class="big">❤️${p.hearts}</div><div class="bn">${p.bonus ? t("bonus_pct", { n: p.bonus }) : ""}</div>
      <div class="em">${SHOP_ART[p.id]}</div><button class="btn" data-pack="${p.id}">${buyLabel(p.price, "★" + p.stars)}</button></div>`).join("")}</div>
    ${CFG.payments === "manual" ? `<div class="center" style="margin-top:12px"><button class="btn blue" id="my-orders">🧾 ${t("my_orders")}</button></div>` : ""}`, { cls: "pink" });
  const mo = $("#my-orders", m.el); if (mo) mo.onclick = () => { m.close(); openMyOrders(); };
  $$("[data-go]", m.el).forEach(b => b.onclick = () => { m.close(); ({ vip: openVip, free: openFree, promo: openPromo, compl: openComplTask, starter: openStarter, dtask: openDailyTasks })[b.dataset.go](); });
  $$("[data-pack]", m.el).forEach(b => b.onclick = () => buy("pack", b.dataset.pack, m));
}

// manual payments: the button shows the price when one is configured, otherwise just "Order"
const buyLabel = (price, stars) => CFG.payments === "manual" ? (price || t("order_btn")) : stars;

const orderWhat = o => o.kind === "vip" ? t("order_vip", { d: CFG.vip.days }) : `❤️${o.hearts}`;

async function placeOrder(kind, id) {
  try {
    const r = await api("/api/orders", "POST", { kind, id }), o = r.order;
    const m = openModal(`<h2>${t("order_title", { n: o.id })}</h2>
      <div class="center" style="font-size:26px;font-weight:800;margin:4px 0">${esc(orderWhat(o))}</div>
      <p class="center" style="font-weight:700;margin:4px 0 12px">${esc(o.price ? t("order_price", { p: o.price }) : t("order_ask_price"))}</p>
      <div class="ord-steps"><p>${t("order_s1")}</p><p>${t("order_s2")}${r.pay_info ? `<br><b>${esc(r.pay_info)}</b>` : ""}</p><p>${t("order_s3")}</p></div>
      <div class="ord-btns">${r.support ? `<button class="btn" id="ord-chat">${t("order_contact")}</button>` : ""}<button class="btn ghost" id="ord-cancel">${t("order_cancel")}</button></div>`);
    const chat = $("#ord-chat", m.el);
    if (chat) chat.onclick = () => openTg(`https://t.me/${r.support.replace("@", "")}?text=${encodeURIComponent(`#${o.id} · ${orderWhat(o)} · ID ${ME.id}`)}`);
    $("#ord-cancel", m.el).onclick = async () => { try { await api(`/api/orders/${o.id}/cancel`, "POST"); toast(t("order_cancelled")); } catch {} m.close(); };
  } catch (e) { toast(e.code === "already" ? t("order_dup") : e.code === "too_many" ? t("order_many") : t("err")); }
}

async function openMyOrders() {
  let list = []; try { list = await api("/api/orders"); } catch {}
  openModal(`<h2>${t("my_orders")}</h2>${list.length ? list.map(o => `<div class="card2"><b>#${o.id} · ${esc(orderWhat(o))}${o.price ? " · " + esc(o.price) : ""}</b><span class="ord-st ${o.status}">${t("order_st_" + o.status)}</span></div>`).join("") : `<p class="sub">${t("order_none")}</p>`}`);
}

async function buy(kind, id, modal) {
  if (CFG.payments === "manual" && !CFG.dev) return placeOrder(kind, id);
  try {
    const r = await api("/api/shop/invoice", "POST", { kind, id });
    if (r.dev) { ME = r.me; renderMe(); toast(t("paid_ok")); sfx.win(); return; }
    if (!tg || !tg.openInvoice) return toast(t("err"));
    tg.openInvoice(r.link, async status => {
      if (status !== "paid") return;
      toast(t("paid_ok")); sfx.win();
      for (let i = 0; i < 4; i++) { await new Promise(r => setTimeout(r, 1200)); ME = await api("/api/me"); renderMe(); }
    });
  } catch { toast(t("err")); }
}

function openVip() {
  const until = ME.vip ? new Date(ME.vip_until * 1000).toLocaleDateString() : "";
  const slides = [["🎁🍸🏆", "vip_slide1"], ["🪪", "vip_slide6"], ["📆", "vip_slide2"], ["💋➕", "vip_slide3"], ["👑", "vip_slide4"], ["🎡", "vip_slide5"]];
  const m = openModal(`<h2 class="vipt">${t("vip_title")}</h2><p class="center" style="font-weight:600;margin:0 6px 6px">${esc(t("vip_desc").split("\n")[0].replace("• ", ""))}</p>
    <div class="vcar" id="vcar">${slides.map(([e, k]) => `<div class="vs"><div class="vse">${e}</div><b>${esc(t(k))}</b></div>`).join("")}</div>
    <div class="vdots" id="vdots">${slides.map((_, i) => `<i class="${i ? "" : "on"}"></i>`).join("")}</div>
    ${ME.vip ? `<p class="sub">${t("vip_until", { date: until })}</p>` : ""}
    ${ME.vip ? `<div class="vcol"><span>😊 <b>${CFG.vip_smiles}</b> ${esc(t("vip_collect"))}</span><button class="btn" id="vip-collect">${t("collect")}</button></div>` : ""}
    ${ME.vip ? "" : `<button class="btn wide" id="vip-buy">${CFG.payments === "manual" ? (CFG.vip.price ? CFG.vip.price + " · " : "") + t("order_btn") : t("vip_buy", { n: CFG.vip.stars })} · ${t("days", { n: CFG.vip.days })}</button>`}`, { cls: "green" });
  const car = $("#vcar", m.el), dots = $$("#vdots i", m.el);
  car.onscroll = () => { const i = Math.round(car.scrollLeft / car.clientWidth); dots.forEach((d, k) => d.classList.toggle("on", k === i)); };
  const vb = $("#vip-buy", m.el); if (vb) vb.onclick = () => buy("vip", "", m);
  const col = $("#vip-collect", m.el);
  if (col) col.onclick = async () => { try { ME = await api("/api/vip/collect", "POST"); renderMe(); sfx.win(); col.disabled = true; } catch { toast(t("not_yet")); } };
}

async function openFree() {
  let tk; try { tk = await api("/api/tasks"); } catch { return toast(t("err")); }
  const m = openModal("", { cls: "freeh" });
  const st = { invite: tk.invited > 0, sub: tk.subscribe_done };
  const render = () => {
    const ready = st.invite && st.sub && !tk.subscribe_done;
    m.set(`<h2>${t("free_title")}</h2>
      <div class="card2"><b>${t("invite_friends")}</b>${st.invite ? "✅" : `<button class="btn" data-a="invite">${t("go")}</button>`}</div>
      <div class="card2"><b>${t("subscribe")}</b>${st.sub ? "✅" : `<button class="btn" data-a="sub">${t("go")}</button>`}</div>
      ${tg && tg.addToHomeScreen && tg.isVersionAtLeast && tg.isVersionAtLeast("8.0") ? `<div class="card2"><b>${t("add_home")}</b><button class="btn" data-a="home">${t("add_btn")}</button></div>` : ""}
      <div class="center" style="margin-top:14px"><button class="btn" id="fr-claim" style="min-width:60%;font-size:18px" ${ready ? "" : "disabled"}>${tk.subscribe_done ? "✅" : t("free_get")}</button></div>`);
    $$("[data-a]", m.el).forEach(b => b.onclick = () => {
      if (b.dataset.a === "home") { try { tg.addToHomeScreen(); } catch { toast(t("err")); } return; }
      if (b.dataset.a === "invite") openTg(`https://t.me/share/url?url=${encodeURIComponent(tk.link || location.origin)}&text=${encodeURIComponent("🍾 Spin the Bottle")}`), st.invite = true;
      else { if (CFG.channel) openTg("https://t.me/" + CFG.channel.replace("@", "")); st.sub = true; }
      render();
    });
    $("#fr-claim", m.el).onclick = async () => {
      try { ME = await api("/api/tasks/claim", "POST", { id: "subscribe" }); renderMe(); sfx.win(); tk.subscribe_done = true; render(); }
      catch (e) { toast(e.code === "not_subscribed" ? t("not_subscribed") : t("not_yet")); st.sub = false; render(); }
    };
  };
  render();
}

// "Акция!": invite-a-friend promo (opened from the shop's friend card)
function openPromo() {
  const m = openModal(`<h2>${t("promo_title")}</h2>
    <div class="promo-av"><div><span class="pa a1">🧑</span><b>+❤20</b></div><div><span class="pa a2">👩<i>★</i></span><b>+❤50</b></div></div>
    <p class="center" style="font-size:17px;line-height:1.3;margin:10px 4px">${esc(t("promo_text"))}</p>
    <p class="center sub" id="pr-stat"></p>
    <div class="center" style="margin-top:14px"><button class="btn" id="pr-inv">${t("promo_invite")}</button></div>`, { cls: "promo" });
  api("/api/tasks").then(tk => { const e = $("#pr-stat", m.el); if (e) e.textContent = t("ref_stats", { n: tk.invited, p: tk.ref_paid, k: tk.ref_need }); }).catch(() => { });
  $("#pr-inv", m.el).onclick = async () => {
    let tk = {}; try { tk = await api("/api/tasks"); } catch {}
    openTg(`https://t.me/share/url?url=${encodeURIComponent(tk.link || location.origin)}&text=${encodeURIComponent("🍾 Spin the Bottle")}`);
  };
}

// "Комплименты": rate players with a tag, 10 ratings pay hearts
async function openComplTask() {
  let task; try { task = await api("/api/tagtask"); } catch { return toast(t("err")); }
  const m = openModal("", { cls: "ctask" });
  const colors = { argues: "#f4a3a3", hair: "#9fdcc0", flatterer: "#a9c6f5", fun: "#c9b6f2", drinks: "#f7dc8c", greedy: "#f4a3a3" };
  const render = () => {
    const p = task.next, left = Math.max(0, task.need - task.done);
    m.set(`<h2>${t("ctask_title")}</h2>
      <div class="ct-banner">${task.paid ? esc(t("ctask_done", { r: task.reward })) : esc(t("ctask_left", { n: left, r: task.reward }))}</div>
      ${p && !task.paid ? `<div class="ct-card"><div class="ct-ph">${p.photo ? `<img src="${esc(p.photo)}" referrerpolicy="no-referrer">` : `<div class="ini">${esc(initials(p.name))}</div>`}<small>${esc(p.name)}</small></div><div class="ct-q">${esc(t("ctask_q"))}</div></div>
        <div class="ct-tags">${CFG.tags.map(k => `<button data-tag="${k}" style="background:${colors[k]}">${esc(t("tag_" + k))}</button>`).join("")}</div>`
        : `<p class="sub">${esc(task.paid ? "✓" : t("ctask_none"))}</p>`}`);
    $$("[data-tag]", m.el).forEach(b => b.onclick = async () => {
      try {
        const r = await api("/api/tagtask/vote", "POST", { to: p.id, tag: b.dataset.tag });
        task = r.task; ME = r.me; renderMe(); sfx.gift();
        if (r.result === "reward") { toast(t("ctask_done", { r: task.reward }), 3500); sfx.win(); }
        render();
      } catch { toast(t("err")); }
    });
  };
  render();
}

function openMenu() {
  const r = $("#btn-menu").getBoundingClientRect(), ov = document.createElement("div"); ov.className = "pop-ov";
  const rows = [["ach", "🏅", "achievements"], ["rate", "📊", "ratings"], ["bot", "🍾", "bottle"], ["dec", "🖼️", "decorations"], ["boo", "⚡", "boosters"]];
  ov.innerHTML = `<div class="pop">${rows.map(([k, i, n]) => `<button data-m="${k}"><span class="ic">${i}</span>${t(n)}</button>`).join("")}</div>`;
  $("#modal-root").appendChild(ov);
  const pop = $(".pop", ov);
  const gap = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--u")) * 2.9;
  const left = MOBILE ? r.left + r.width / 2 - pop.offsetWidth / 2 : r.right + 10, top = MOBILE ? r.bottom + gap : r.top + r.height / 2 - pop.offsetHeight / 2;
  pop.style.left = Math.max(8, Math.min(left, innerWidth - pop.offsetWidth - 8)) + "px";
  pop.style.top = Math.max(8, Math.min(top, innerHeight - pop.offsetHeight - 8)) + "px";
  const map = { ach: openAchievements, rate: openRatings, bot: () => openStore("bottle"), dec: () => openStore("frame"), boo: () => openStore("booster") };
  ov.addEventListener("click", e => { const b = e.target.closest("[data-m]"); ov.remove(); if (b) map[b.dataset.m](); });
}

function bottlePreview(id) { return `<div class="pv-b">${bottleSvg(id)}</div>`; }

// ---- "Сменить бутылочку": panel at the bottom, like the gift panel
function openBottlePanel() {
  $("#bp-label").textContent = t("change_bottle");
  $("#bottle-panel").classList.remove("hidden");
  const render = () => {
    const g = $("#bottle-grid"); g.innerHTML = "";
    CFG.items.filter(i => i.kind === "bottle").forEach(it => {
      const have = ME.inv[it.id] && ME.inv[it.id].qty > 0, eq = ME.bottle === it.id;
      const b = document.createElement("button"); b.className = "bi" + (eq ? " eq" : "");
      b.innerHTML = `<span class="bv">${bottleSvg(it.id)}</span><span class="bp">${eq ? "✓" : have ? "" : "❤️" + it.price}</span>`;
      b.onclick = async () => {
        try {
          if (!have) ME = await api("/api/store/buy", "POST", { item: it.id });
          ME = await api("/api/store/equip", "POST", { item: it.id });
          renderMe(); setBottle(ME.bottle); sfx.gift(); render();
        } catch (e) { if (e.code === "no_hearts") { toast(t("no_hearts")); openShop(); } else toast(t("err")); }
      };
      g.appendChild(b);
    });
  };
  render();
}
$("#bp-close").onclick = () => $("#bottle-panel").classList.add("hidden");

// ---- decorations: preview + apply
function openStore(kind) {
  if (kind === "bottle") return openBottlePanel();
  if (kind === "booster") return openBoosters();
  const m = openModal("", { cls: "decor" }); let sel = ME.frame;
  const frames = CFG.items.filter(i => i.kind === "frame");
  const owned = id => !!(ME.inv[id] && ME.inv[id].qty > 0);
  m.el.innerHTML = `<h2></h2><div class="dc-top"></div><div class="dc-scroll"><div class="dc-grid">` +
    `<button class="dc-t" data-f=""><span class="dc-ic"><span class="dc-none">✕</span></span><b></b></button>` +
    frames.map(f => `<button class="dc-t" data-f="${f.id}" aria-label="${esc(t(f.id))}"><span class="dc-ic">${frameArt(f.id)}${frameEmblem(f.id)}</span><b></b></button>`).join("") + `</div></div>`;
  const render = () => {   // only the preview and the marks change, so the list keeps its scroll position
    const cur = frames.find(f => f.id === sel), have = !sel || owned(sel), eq = sel === ME.frame;
    $("h2", m.el).textContent = sel ? t(sel) : t("no_decor");
    $(".dc-top", m.el).innerHTML = `<div class="dc-pv"><div class="frame"><div class="av">${avInner(ME.photo, ME.name)}</div>${frameArt(sel)}</div><small>${frameEmblem(sel)}<span>${esc(ME.name)}${ME.age ? ", " + ME.age : ""}</span>${frameEmblem(sel)}</small></div>
      <div class="dc-info"><p>${sel ? esc(t("decor_desc")) : esc(t("keep_plain"))}</p><button class="btn ${eq ? "gray" : ""}" id="dc-apply" ${eq ? "disabled" : ""}>${have ? t("apply") : heartMini("#f2572f") + cur.price}</button></div>`;
    $$("[data-f]", m.el).forEach(b => {
      const id = b.dataset.f;
      b.classList.toggle("on", id === sel);
      $("b", b).outerHTML = ME.frame === id ? `<b class="dc-ok">✓</b>` : id && !owned(id) ? `<b class="dc-price">${heartMini("#f2572f")}${frames.find(f => f.id === id).price}</b>` : "<b></b>";
    });
    $("#dc-apply", m.el).onclick = async () => {
      try {
        if (sel && !have) ME = await api("/api/store/buy", "POST", { item: sel });
        ME = await api("/api/store/equip", "POST", { item: sel }); renderMe(); sfx.gift(); render();
      } catch (e) { if (e.code === "no_hearts") { toast(t("no_hearts")); m.close(); openShop(); } else toast(t("err")); }
    };
  };
  $$("[data-f]", m.el).forEach(b => b.onclick = () => { sel = b.dataset.f; render(); });
  render();
}

// ---- boosters: round icons with counts, tap for details
async function openLeague() {
  let d; try { d = await api("/api/league"); } catch { return toast(t("err")); }
  const m = openModal("", { cls: "league" }), inv = id => (ME.inv[id] || { qty: 0 }).qty, it = id => CFG.items.find(i => i.id === id);
  const render = () => {
    const left = Math.max(0, d.ends - Math.floor(Date.now() / 1000)), dd = Math.floor(left / 86400), hh = Math.floor(left % 86400 / 3600), me = d.me;
    m.set(`<button class="qhelp" id="lg-help">?</button><h2>🏆 ${esc(t("league_title"))}</h2>
      <p class="sub center">${esc(t("league_end", { d: dd, h: hh }))}</p>
      <div class="lg-me"><div><b>${me.rank ? "#" + me.rank : "—"}</b><small>${esc(t("league_rank"))}</small></div><div><b>${me.pts}/${me.limit}</b><small>${esc(t("league_pts"))}</small></div>${me.x2_left ? `<div class="x2"><b>×2</b><small>${esc(t("league_x2_left", { m: Math.ceil(me.x2_left / 60) }))}</small></div>` : ""}</div>
      <div class="dt-bar"><i style="width:${Math.min(100, Math.round(me.pts / me.limit * 100))}%"></i></div>
      <div class="lg-bs">${["league_x2", "league_limit", "league_plus5"].map(id => `<button class="lg-b" data-use="${id}" ${inv(id) ? "" : "disabled"} title="${esc(t(id + "_n"))}"><span>${it(id).emoji}</span><i>${inv(id)}</i></button>`).join("")}<button class="lg-b shop" id="lg-shop">＋</button></div>
      <div class="lg-list">${d.top.map((r, i) => `<div class="lg-r ${r.uid === ME.id ? "me" : ""}"><b>${i + 1}</b>${miniAv(r.photo, r.name)}<span>${esc(r.name)}</span><em>${r.pts}</em></div>`).join("") || `<p class="sub center">${esc(t("league_empty"))}</p>`}</div>`);
    $("#lg-help", m.el).onclick = () => toast(t("league_help", { n: d.me.limit }), 12000);
    $("#lg-shop", m.el).onclick = () => { m.close(); openBoosters(); };
    $$("[data-use]", m.el).forEach(b => b.onclick = async () => {
      try { ME = await api("/api/league/use", "POST", { item: b.dataset.use }); renderMe(); sfx.win(); d = await api("/api/league"); render(); } catch { toast(t("not_yet")); }
    });
  };
  render();
}
function openBoosters() {
  const m = openModal("", { cls: "boost" }); let sel = "";
  const groups = [["b_choice", ["kiss_fire", "slap"]], ["b_league", ["league_x2", "league_limit", "league_plus5"]], ["b_other", ["magnet", "double", "shield"]]];
  const render = () => {
    const it = id => CFG.items.find(i => i.id === id), inv = id => ME.inv[id] || { qty: 0, armed: 0 };
    m.set(`<button class="qhelp" id="bs-help">?</button><h2>${t("boosters_title")}</h2><p class="center" style="margin:2px 0 6px;font-weight:600">${t("boosters_desc")}</p>
      ${groups.map(([title, ids]) => `<div class="bs-h"><span>${t(title)}</span></div><div class="bs-row">${ids.map(id => `<button class="bs-i ${sel === id ? "on" : ""}" data-b="${id}"><span>${it(id).emoji}</span><i>${inv(id).qty + inv(id).armed}</i></button>`).join("")}</div>`).join("")}
      ${sel ? `<div class="bs-d"><b>${t(sel + "_n")}</b><small>${t(sel + "_d")}</small>
        <div class="bs-a"><button class="btn" data-buy="${sel}">❤️ ${it(sel).price}</button>${inv(sel).qty ? (it(sel).kind === "league" ? `<button class="btn blue" data-lg="${sel}">${t("use")} (${inv(sel).qty})</button>` : it(sel).kind === "choice" ? `<small class="bs-own">× ${inv(sel).qty} · ${t("choice_hint")}</small>` : `<button class="btn blue" data-arm="${sel}">${t("use")} (${inv(sel).qty})</button>`) : ""}</div>
        ${inv(sel).armed ? `<small style="color:#4a9">${t("armed", { n: inv(sel).armed })}</small>` : ""}</div>` : ""}`);
    $$("[data-b]", m.el).forEach(b => b.onclick = () => { sel = b.dataset.b; render(); });
    $("#bs-help", m.el).onclick = () => toast(t("boosters_help"), 12000);
    const act = async (path, body) => { try { ME = await api(path, "POST", body); renderMe(); render(); } catch (e) { if (e.code === "no_hearts") { toast(t("no_hearts")); m.close(); openShop(); } else toast(t("err")); } };
    $$("[data-buy]", m.el).forEach(b => b.onclick = () => act("/api/store/buy", { item: b.dataset.buy }));
    $$("[data-arm]", m.el).forEach(b => b.onclick = () => act("/api/store/arm", { item: b.dataset.arm }));
    $$("[data-lg]", m.el).forEach(b => b.onclick = () => act("/api/league/use", { item: b.dataset.lg }));
  };
  render();
}

const ACH_ICON = { kisses: "💋", spins: "🍾", gifts_sent: "🎁", gifts_received: "🌟", msgs: "💬", streak: "🔥", tracks: "🎵" };
const medalArt = md => md.art ? giftIcon(md.art) : md.emoji;
const medalBadge = (md, tier) => `<div class="mdl t${tier}"><span class="mdl-stars">${[1, 2, 3].map(i => `<i class="${i <= tier ? "on" : ""}">★</i>`).join("")}</span><div class="mdl-c"><span>${medalArt(md)}</span></div></div>`;
const medalState = md => { const p = (ME.medals || {})[md.id] || [0, 0]; return { v: p[0], tier: p[1], next: md.tiers[Math.min(p[1], 2)] }; };
function openMedal(md) {   // like the original: "Выполни условие, чтобы получить:" + medal + name + condition
  const s = medalState(md);
  openModal(`<h2>${esc(t("ach_title"))}</h2><p class="center sub">${esc(t("ach_cond"))}</p><div class="center">${medalBadge(md, s.tier)}</div>
    <h3 class="center" style="margin:6px 0">${esc(t("md_" + md.id))}</h3>
    <div class="card2"><b>${esc(t("mdd_" + md.id, { n: s.next }))}</b><span>${Math.min(s.v, s.next)}/${s.next}</span></div>
    <div class="dt-bar"><i style="width:${Math.min(100, Math.round(s.v / s.next * 100))}%"></i></div>
    <small class="sub center" style="display:block">${md.tiers.map((n, i) => `${i < s.tier ? "★" : "☆"} ${n} (+❤${md.rewards[i]})`).join(" · ")}</small>`);
}
function showMedals(list) {
  if (!list || !list.length) return;
  const x = list[list.length - 1], md = CFG.medals.find(q => q.id === x.id); if (md) celebrate(() => medalWindow(list, x, md));
}
function medalWindow(list, x, md) {
  const total = list.reduce((a, q) => a + q.reward, 0);
  const m = openModal(`<h2>${esc(t("ach_congrats"))}</h2><div class="sub">${esc(t("ach_medal_got"))}</div>
    <div class="center" style="margin:6px 0">${medalBadge(md, x.tier)}</div>
    <h3 class="center" style="margin:4px 0">${esc(t("md_" + md.id))}</h3>
    <div class="req">${esc(t("mdd_" + md.id, { n: md.tiers[x.tier - 1] }))}</div>
    ${list.length > 1 ? `<p class="center sub">+${list.length - 1}</p>` : ""}
    <button class="btn cta-ok" style="width:100%">${esc(t("ach_continue"))} +❤${total}</button>`, { cls: "achm", closable: false });
  $(".cta-ok", m.el).onclick = m.close; sfx.ach();
  return m;
}
function openAchievements() {
  const m = openModal("", { cls: "ach" }); let doneFirst = true;
  const render = () => {
    const list = CFG.medals.map(md => ({ md, ...medalState(md) }));
    list.sort((a, b) => (doneFirst ? b.tier - a.tier : a.tier - b.tier));
    const stars = list.reduce((a, q) => a + q.tier, 0), tier = {}, old = CFG.achievements.map(a => { tier[a.stat] = (tier[a.stat] || 0) + 1; return { ...a, tier: tier[a.stat], max: CFG.achievements.filter(x => x.stat === a.stat).length, got: ME.ach.includes(a.id) }; });
    m.set(`<h2>${t("my_ach")} <span class="ach-n">★ ${stars}/${list.length * 3}</span></h2>
      <div class="ach-f"><span>${t("first")}</span><div class="segp"><button data-df="1" class="${doneFirst ? "on" : ""}">${t("done_f")}</button><button data-df="0" class="${doneFirst ? "" : "on"}">${t("undone_f")}</button></div></div>
      <div class="md-g">${list.map(q => `<button class="md-i" data-md="${q.md.id}">${medalBadge(q.md, q.tier)}<small>${esc(t("md_" + q.md.id))}</small><em>${Math.min(q.v, q.next)}/${q.next}</em></button>`).join("")}</div>
      <h3 class="ach-sub">${esc(t("ach_basic"))} · ★ ${ME.ach.length}/${old.length}</h3>
      <div class="ach-g">${old.map(a => `<div class="ach-c ${a.got ? "got" : ""}"><div class="ach-st">${"★".repeat(Math.min(5, 1 + Math.ceil(a.tier * 5 / a.max)))}</div><div class="ach-m">${ACH_ICON[a.stat] || "🏅"}</div>
        <small>${esc(t("achs_" + a.stat, { n: a.need }))}</small><em>${Math.min(ME[a.stat] || 0, a.need)}/${a.need}</em></div>`).join("")}</div>`);
    $$("[data-df]", m.el).forEach(b => b.onclick = () => { doneFirst = b.dataset.df === "1"; render(); });
    $$("[data-md]", m.el).forEach(b => b.onclick = () => openMedal(CFG.medals.find(q => q.id === b.dataset.md)));
  };
  render();
}

// rating icons: our own drawings in the places of the original's five
const RT_ICON = {
  kisses: `<svg viewBox="0 0 64 44"><path d="M4 22C13 5 25 6 32 13C39 6 51 5 60 22C51 37 42 41 32 41C22 41 13 37 4 22Z" fill="#e8382d"/><path d="M6 22C20 28 44 28 58 22" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="2.6" stroke-linecap="round"/></svg>`,
  dj: `<svg viewBox="0 0 48 48" fill="#c8479f"><path d="M18 8l24-5v28.500a7.500 6.500 0 1 1-4-5.700V13l-16 3.500v21a7.500 6.500 0 1 1-4-5.700z"/></svg>`,
  dear: `<svg viewBox="0 0 48 44"><path d="M24 42C8 31 2 23 2 14C2 7 7 2 13.500 2C18 2 22 5 24 9C26 5 30 2 34.500 2C41 2 46 7 46 14C46 23 40 31 24 42Z" fill="#ea5a2c"/></svg>`,
  influence: `<svg viewBox="0 0 64 46"><path d="M42 41C30 32 25 26 25 19C25 13 29 9 34 9C38 9 41 11 42 14C43 11 46 9 50 9C56 9 61 13 61 19C61 26 54 32 42 41Z" fill="#c9431f"/><path d="M22 38C10 29 3 22 3 14C3 8 7 4 13 4C17 4 20 6 22 10C24 6 27 4 31 4C37 4 41 8 41 14C41 22 34 29 22 38Z" fill="#ea6a2c" stroke="#fff" stroke-width="2.4"/></svg>`,
  emotion: `<svg viewBox="0 0 48 48"><circle cx="24" cy="24" r="22" fill="#ffc12e"/><path d="M12 18q4-6 8 0M28 18q4-6 8 0" fill="none" stroke="#7a3d06" stroke-width="3.400" stroke-linecap="round"/><path d="M10 27h28c-2 10-8 15-14 15S12 37 10 27z" fill="#7a3d06"/><path d="M14 29h20c-1 3-3 4-10 4s-9-1-10-4z" fill="#fff"/></svg>`,
};
function retryImg(img) {   // one more try, then leave the plain placeholder
  if (img.dataset.again) return img.remove();
  img.dataset.again = "1"; setTimeout(() => { img.src = img.getAttribute("src"); }, 1500);
}
const RATINGS = ["kisses", "dj", "dear", "influence", "emotion"], RT_PERIODS = ["kisses", "dj", "emotion"];
const num = v => (v || 0).toLocaleString("ru");
async function openRatings() {
  const m = openModal("", { cls: "rate" }); let kind = "kisses", period = "all";
  const photo = p => `<div class="rt2-ph">${p ? `<img src="${esc(p)}" referrerpolicy="no-referrer" onerror="retryImg(this)">` : ""}</div>`;
  const load = async () => {
    const pOK = RT_PERIODS.includes(kind); if (!pOK) period = "all";
    let r; try { r = await api(`/api/ratings/${kind}?period=${period}`); } catch { return; }
    const val = v => `<span class="rt-v ${kind}">${RT_ICON[kind]}<i>${num(v)}</i></span>`;
    m.set(`<div class="rt-top"><button class="rt-q" id="rt-q">?</button><div class="rt-ic">${RATINGS.map(k => `<button data-k="${k}" class="${k === kind ? "on" : ""}">${RT_ICON[k]}</button>`).join("")}</div></div>
      <div class="rt-sub"><b>${t("rt_" + kind)}</b>${pOK ? `<select class="rt-per" id="rt-per">${[["day", "period_day"], ["week", "period_week"], ["month", "period_month"], ["all", "all_time"]].map(([k, key]) => `<option value="${k}" ${k === period ? "selected" : ""}>${esc(t(key))}</option>`).join("")}</select>` : ""}</div>
      <div class="rt-list">${r.rows.map((x, i) => `<div class="rt2-row" data-u="${x.id}">${photo(x.photo)}<b><em>${i + 1}.</em> ${esc(x.name)}</b>${val(x.v)}</div>`).join("") || `<p class="rt-empty">${t("rt_empty")}</p>`}</div>
      <div class="rt2-row me">${photo(ME.photo)}<b>${r.rank ? `<em>${r.rank}.</em> ` : ""}${esc(ME.name)}</b>${val(r.mine)}</div>`);
    $$("[data-k]", m.el).forEach(b => b.onclick = () => { kind = b.dataset.k; load(); });
    $$("[data-u]", m.el).forEach(row => row.onclick = () => openProfile(+row.dataset.u));
    const ps = $("#rt-per", m.el); if (ps) ps.onchange = () => { period = ps.value; load(); };
    $("#rt-q", m.el).onclick = () => openRatingRule(kind);
  };
  load();
}
function openRatingRule(kind) {   // the "?" window: how points are earned
  const extra = kind === "kisses" && CFG.weekly ? " " + t("weekly_hint", { a: CFG.weekly.rewards[0], b: CFG.weekly.rewards[1], c: CFG.weekly.rewards[2], n: CFG.weekly.min }) : "";
  const m = openModal(`<h2>${t("rt_" + kind)}</h2><p class="rt-rule">${esc(t("rtr_" + kind) + extra)}</p><p class="rt-rule">${esc(t("rt_top_rule"))}</p>
    <div class="center"><button class="btn" id="rt-ok">${t("got_it")}</button></div>`, { cls: "rule" });
  $("#rt-ok", m.el).onclick = m.close;
}

const SET_ICON = {   // our own drawings
  snd: `<svg viewBox="0 0 32 32"><path d="M3 11.500h5.500L17 5v22l-8.500-6.500H3z" fill="#8fc63f"/><path d="M21 11c2.500 2.800 2.500 7.200 0 10M25 7.500c5 5 5 12 0 17" fill="none" stroke="#b9bcc2" stroke-width="2.600" stroke-linecap="round"/></svg>`,
  mus: `<svg viewBox="0 0 32 32" fill="#c8479f"><path d="M12 6l16-3.500v19a5 4.300 0 1 1-2.700-3.800V9.500L14.700 11.800V25a5 4.300 0 1 1-2.700-3.800z"/></svg>`,
  ntf: `<svg viewBox="0 0 32 32"><path d="M16 3c-6 0-8.500 5-8.500 10v6l-3 5h23l-3-5v-6C24.500 8 22 3 16 3z" fill="#ffc12e"/><path d="M12.500 26a3.500 3.500 0 0 0 7 0z" fill="#d98a10"/></svg>`,
  lng: `<svg viewBox="0 0 32 32" fill="none" stroke="#4fa3e0" stroke-width="2.400"><circle cx="16" cy="16" r="12.500"/><path d="M3.500 16h25M16 3.500c-8 7-8 18 0 25 8-7 8-18 0-25z"/></svg>`,
  inv: `<svg viewBox="0 0 32 32"><circle cx="18" cy="11" r="6.500" fill="#e9b184"/><path d="M7 29c1-8 5.500-10.500 11-10.500S28 21 29 29z" fill="#7a86c8"/><circle cx="7.500" cy="8" r="6" fill="#8fc63f"/><path d="M7.500 5v6M4.500 8h6" stroke="#fff" stroke-width="1.900" stroke-linecap="round"/></svg>`,
  prof: `<svg viewBox="0 0 32 32"><rect x="2" y="5" width="28" height="22" rx="3" fill="#4fa3e0"/><rect x="2" y="5" width="28" height="6" rx="3" fill="#2f7fc4"/><circle cx="10" cy="18" r="4" fill="#fff"/><path d="M17 16h9M17 21h7" stroke="#fff" stroke-width="2.200" stroke-linecap="round"/></svg>`,
  help: `<svg viewBox="0 0 32 32"><path d="M3 5h19v13H11l-5 4v-4H3z" fill="#9cc7ee"/><path d="M12 12h17v13h-3v4l-5-4h-9z" fill="#4fa3e0"/></svg>`,
};
function openSettings() {
  const sw = (id, on) => `<span class="tgl"><input id="${id}" type="checkbox" ${on ? "checked" : ""}><i></i></span>`;
  const m = openModal(`<h2>${t("settings")}</h2>
    <label class="st-row"><i>${SET_ICON.snd}</i><b>${t("sounds")}</b>${sw("st-snd", parseFloat(ls.get("sfx", "0.7")) > 0)}</label>
    <label class="st-row"><i>${SET_ICON.mus}</i><b>${t("music")}</b>${sw("st-mus", parseInt(ls.get("musicVol", "0")) > 0)}</label>
    <label class="st-row"><i>${SET_ICON.ntf}</i><b>${t("notify_label")}</b>${sw("st-notify", ME.notify)}</label>
    <label class="st-row"><i>${SET_ICON.lng}</i><b>${t("language")}</b><select id="st-lang"><option value="uz">O'zbekcha</option><option value="ru">Русский</option><option value="en">English</option></select></label>
    <button class="st-row" data-s="inv"><i>${SET_ICON.inv}</i><b>${t("invite")}</b></button>
    <button class="st-row" data-s="prof"><i>${SET_ICON.prof}</i><b>${t("profile_settings")}</b></button>
    <button class="st-row" data-s="help"><i>${SET_ICON.help}</i><b>${t("contact")}</b></button>
    <p class="st-id">ID ${ME.id}</p>`, { cls: "settings" });
  $("#st-notify", m.el).onchange = async e => { try { ME = await api("/api/notify", "POST", { on: e.target.checked }); } catch {} };
  $("#st-lang", m.el).value = lang;
  $("#st-lang", m.el).onchange = async e => {
    try { ME = await api("/api/profile", "POST", { name: ME.name, birth: ME.birth || "", age: ME.age, gender: ME.gender, lang: e.target.value }); lang = ME.lang; applyStatic(); m.close(); toast("✓"); } catch { toast(t("err")); }
  };
  $("#st-snd", m.el).onchange = e => { ls.set("sfx", e.target.checked ? "0.7" : "0"); if (e.target.checked) sfx.bell(); };
  $("#st-mus", m.el).onchange = e => { const v = e.target.checked ? "60" : "0"; ls.set("musicVol", v); $("#pl-range").value = v; applyVolume(); };
  $$("[data-s]", m.el).forEach(b => b.onclick = () => {
    m.close();
    if (b.dataset.s === "inv") openFree();
    else if (b.dataset.s === "prof") profileModal(false);
    else CFG.support ? openTg("https://t.me/" + CFG.support.replace("@", "")) : toast("—");
  });
}

async function openTables() {
  const m = openModal(""); let d = { recent: [], popular: [] };
  try { d = await api("/api/tables/recent"); } catch {}
  const row = r => `<button class="tb-row" data-t="${r.id}"><span class="tb-ic">${bottleSvg("bottle_green")}</span><span class="tb-no">#${r.id}</span>
    <span class="tb-cnt"><span><em>👦</em>${r.m}</span><span><em>👧</em>${r.f}</span></span></button>`;
  m.set(`<h2>${t("change_table")}</h2><button class="tb-rand" id="tb-rand">${t("random_table")}</button>
    ${d.recent.length ? `<p class="tb-sec">${t("last_tables")}</p>${d.recent.map(row).join("")}` : ""}
    ${d.popular.length ? `<p class="tb-sec">${t("popular_tables")}</p>${d.popular.map(row).join("")}` : ""}`);
  $("#tb-rand", m.el).onclick = () => { send({ t: "join", table: "random" }); m.close(); };
  $$("[data-t]", m.el).forEach(b => b.onclick = () => { send({ t: "join", table: parseInt(b.dataset.t) }); m.close(); });
}

// ------------------------------------------------------------ wheel
let wheelRot = 0;
const GOLD = "url(#gGold)";
const heartPath = (x, y, s, f = "url(#gRed)") => `<path transform="translate(${x} ${y}) scale(${s / 10})" d="M0 9C-12 0-9-9-4.5-9C-2-9 0-7 0-5C0-7 2-9 4.5-9C9-9 12 0 0 9Z" fill="${f}" stroke="#7a0f1e" stroke-opacity=".5" stroke-width="1" stroke-linejoin="round"/>`;
const smileSvg = (x, y, r) => `<circle cx="${x}" cy="${y}" r="${r}" fill="url(#gYellow)" stroke="#a86a00" stroke-opacity=".6" stroke-width="1.4"/><circle cx="${x - r * .35}" cy="${y - r * .2}" r="${r * .11}" fill="#6b3a00"/><circle cx="${x + r * .35}" cy="${y - r * .2}" r="${r * .11}" fill="#6b3a00"/><path d="M${x - r * .45} ${y + r * .15}Q${x} ${y + r * .7} ${x + r * .45} ${y + r * .15}" fill="none" stroke="#6b3a00" stroke-width="${r * .12}" stroke-linecap="round"/>`;
const diceSvg = (x, y, s) => `<rect x="${x - s}" y="${y - s}" width="${s * 2}" height="${s * 2}" rx="${s * .35}" fill="#17a37c" stroke="#0b5e49" stroke-width="1.5"/>${[[-.5, -.5], [.5, -.5], [0, 0], [-.5, .5], [.5, .5]].map(([dx, dy]) => `<circle cx="${x + dx * s}" cy="${y + dy * s}" r="${s * .17}" fill="#eafff6"/>`).join("")}`;
function wheelSvg() {
  const n = CFG.wheel.length, step = 360 / n, cx = 160, cy = 160;
  const pt = (a, r) => [cx + r * Math.sin(a * Math.PI / 180), cy - r * Math.cos(a * Math.PI / 180)];
  let out = `<svg id="wheel" viewBox="0 0 320 320"><circle cx="160" cy="160" r="159" fill="${GOLD}"/><circle cx="160" cy="160" r="150" fill="#b97a10"/><circle cx="160" cy="160" r="147" fill="${GOLD}"/><circle cx="160" cy="160" r="141" fill="#0b6a54"/>`;
  CFG.wheel.forEach((w, i) => {
    const a0 = i * step - step / 2, a1 = i * step + step / 2, [x0, y0] = pt(a0, 139), [x1, y1] = pt(a1, 139);
    out += `<path d="M160 160L${x0} ${y0}A139 139 0 0 1 ${x1} ${y1}Z" fill="${i % 2 ? "#16a47c" : "#0f8f6c"}" stroke="#0b6a54" stroke-width=".8"/>`;
    const [ix, iy] = pt(i * step, 114), [nx, ny] = pt(i * step, 78);
    const icon = w.kind === "hearts" ? heartPath(ix, iy, 15) : w.kind === "smiles" ? smileSvg(ix, iy, 12) : diceSvg(ix, iy, 10);
    out += icon + `<g transform="translate(${nx} ${ny}) rotate(${i * step - 90})"><text x="0" y="0" text-anchor="middle" dominant-baseline="middle" font-size="${w.amount >= 100 ? 17 : 19}" font-weight="900" fill="#ffe9a0" stroke="#7a4a00" stroke-opacity=".45" stroke-width=".8">${w.amount}</text></g>`;
  });
  return out + `<circle cx="160" cy="160" r="36" fill="#9a6408"/><circle cx="160" cy="160" r="33" fill="${GOLD}"/>${heartPath(160, 162, 21, "#fff")}</svg>`;
}
// fixed "selector": lime wedge from the pointer toward the centre, and the golden arrow badge on the left rim
const WHEEL_SEL = (() => {
  const step = 360 / 16, pt = (a, r) => [160 + r * Math.sin(a * Math.PI / 180), 160 - r * Math.cos(a * Math.PI / 180)];
  const [x0, y0] = pt(270 - step / 2, 139), [x1, y1] = pt(270 + step / 2, 139);
  return `<svg class="wsel" viewBox="0 0 320 320"><defs><radialGradient id="wselg" cx="0" cy="0.5" r="1"><stop offset="0" stop-color="#d8ff7a" stop-opacity=".95"/><stop offset="1" stop-color="#7fe04a" stop-opacity=".05"/></radialGradient></defs><path d="M160 160L${x0} ${y0}A139 139 0 0 1 ${x1} ${y1}Z" fill="url(#wselg)"/></svg>
  <svg class="wpt" viewBox="0 0 80 80"><path d="M6 40L30 10H66Q72 10 72 16V64Q72 70 66 70H30Z" fill="${GOLD}" stroke="#7a4a00" stroke-width="2.4" stroke-linejoin="round"/><path d="M20 40h30M40 28l14 12-14 12" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 40h30M40 28l14 12-14 12" fill="none" stroke="#a86a00" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" opacity=".6"/></svg>`;
})();
// bundles of green dice for the chance shop (own art)
const diceStack = k => { const pos = [[0, 6], [-13, 14], [13, 14], [-6, -4], [7, -6], [0, -16], [-18, 2], [18, 2], [0, 26]].slice(0, k); return `<svg viewBox="-34 -30 68 66" class="dstack">${pos.map(([x, y]) => diceSvg(x, y, 9)).join("")}</svg>`; };
const PACK_ART = { 1: 1, 5: 3, 15: 5, 50: 7, 300: 9 };

function openChanceShop(onBought) {
  const m = openModal("", { cls: "green chshop" });
  m.set(`<h2>${t("chance_shop")}</h2><div class="cs-grid">${CFG.chance_packs.map(p => `<button class="cs-i" data-n="${p.n}"><b class="cs-n">${p.n}</b>${diceStack(PACK_ART[p.n] || 3)}<span class="cs-p">❤️ ${p.price}</span></button>`).join("")}</div>`);
  m.el.onclick = async e => {
    const b = e.target.closest(".cs-i"); if (!b) return;
    try { ME = await api("/api/wheel/buy", "POST", { n: +b.dataset.n }); renderMe(); sfx.coin(); toast(t("chance_bought", { n: b.dataset.n })); m.close(); onBought && onBought(); }
    catch (er) { toast(t("no_hearts")); m.close(); openShop(); }
  };
}

async function openWheel() {
  let info = { winner: null }; try { info = await api("/api/wheel"); } catch {}
  let busy = false;
  const m = openModal("", { cls: "dark" });
  const render = () => {
    m.root.style.background = "rgba(0,0,0,.38)";
    m.set(`<div class="wh-top"><button class="qhelp" id="wh-help">?</button><h2>${t("wheel_title")}</h2><p class="center" style="margin:4px 0 8px">${t("wheel_desc")}</p>
      <div class="center wh-line">${t("chances")}: <span class="chance-pill"><svg viewBox="-12 -12 24 24" width="22" height="22">${diceSvg(0, 0, 10)}</svg> <b>${ME.chances}</b> <button class="pl" id="wh-buy">+</button></span></div></div>
      <div class="wheel-box">${wheelSvg()}${WHEEL_SEL}</div>
      <div class="center price-row">${t("price")}: <svg viewBox="-12 -12 24 24" width="22" height="22">${diceSvg(0, 0, 10)}</svg> <b>1</b></div>
      <div class="center"><button class="btn" id="wh-spin" style="min-width:60%;font-size:19px;padding:12px">${t("spin_btn")}</button></div>
      <div class="winner-bar">${info.winner
        ? `${miniAv(info.winner.photo, info.winner.name)}<div><span class="wn-t">${t("winner_title")}</span><br><b>${esc(info.winner.name)}</b> ${t(info.winner.amount >= 100 ? "winner_tail" : "winner_small_tail")} <b>❤️${info.winner.amount}</b></div>`
        : `<span style="font-size:34px">🎰</span><div>${t("winner_none")}</div>`}</div>`);
    $("#wheel", m.el).style.transform = `rotate(${wheelRot}deg)`;
    $("#wheel", m.el).style.transition = "none";
    $("#wh-help", m.el).onclick = () => toast(t("wheel_desc"), 3500);
    $("#wh-buy", m.el).onclick = () => { if (!busy) openChanceShop(() => document.body.contains(m.root) && render()); };
    $("#wh-spin", m.el).onclick = async () => {
      if (busy) return;
      if (ME.chances < 1) return openChanceShop(() => document.body.contains(m.root) && render());
      busy = true;
      try {
        const r = await api("/api/wheel/spin", "POST");
        const step = 360 / CFG.wheel.length, delta = (((270 - r.index * step - wheelRot) % 360) + 360) % 360;
        wheelRot += 360 * 5 + delta; sfx.wheel(5, 360 * 5 + delta);
        const w = $("#wheel", m.el); void w.getBoundingClientRect(); w.style.transition = ""; w.style.transform = `rotate(${wheelRot}deg)`;
        setTimeout(() => {
          ME = r.me; renderMe(); busy = false; sfx.wheelStop(true);
          toast(t("you_won", { text: r.kind === "hearts" ? `❤️ ${r.amount}` : r.kind === "smiles" ? `😊 ${r.amount}` : `🎲 ${r.amount}` }), 3500);
          if (document.body.contains(m.root)) { wheelRot %= 360; render(); }
        }, 5200);
      } catch { busy = false; toast(t("no_chances")); }
    };
  };
  render();
}

boot().catch(e => { $("#boot-msg").textContent = "Error: " + e.message; console.error(e); });

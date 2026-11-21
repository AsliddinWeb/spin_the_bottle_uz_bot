"use strict";
const $ = (s, r = document) => r.querySelector(s);
const tg = window.Telegram && Telegram.WebApp;
if (tg) { tg.ready(); tg.expand(); }
const dev = new URLSearchParams(location.search).get("dev");           // ?dev=<id> works only when the server runs in DEV_MODE
const initData = dev ? "dev:" + dev : (tg ? tg.initData : "");
const RANK = { "": 0, mod: 1, admin: 2, owner: 3 };
let ME = null, tab = "dash";

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = ts => ts ? new Date(ts * 1000).toLocaleString("uz", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
const until = ts => ts ? fmt(ts) : "∞";
const ERR = {
  self: "o'zingizga qo'llab bo'lmaydi", rank: "bu odam sizdan yuqori yoki teng darajada", need_admin: "admin huquqi kerak", need_mod: "moderator huquqi kerak",
  need_owner: "faqat owner", no_user: "foydalanuvchi topilmadi", bad_role: "noto'g'ri rol", bad_what: "noto'g'ri maydon", is_owner: "owner rolini o'zgartirib bo'lmaydi",
  handled: "allaqachon ko'rib chiqilgan", no_order: "buyurtma topilmadi", bad_text: "matn noto'g'ri", no_bot: "bot ulanmagan", busy: "xabar yuborish davom etmoqda",
  bad_word: "so'z noto'g'ri (2-30 belgi, bo'sh joysiz)", need_role: "ruxsat yo'q", empty: "bo'sh", bad_duration: "muddat noto'g'ri", bad_act: "noma'lum amal", forbidden: "ruxsat yo'q",
};
const ROLE_TXT = { owner: "owner", admin: "admin", mod: "moderator", "": "o'yinchi" };
const REASON = { abuse: "haqorat", spam: "spam", nsfw: "18+", fraud: "aldash", age: "yosh" };

function toast(t, bad) { const e = $("#toast"); e.textContent = t; e.className = "on" + (bad ? " err" : ""); clearTimeout(toast.t); toast.t = setTimeout(() => e.className = "", 2200); }

async function api(path, method = "GET", body) {
  const r = await fetch("/api/admin" + path, { method, headers: { "Content-Type": "application/json", "X-Init-Data": initData }, body: body === undefined ? undefined : JSON.stringify(body) });
  let j = {}; try { j = await r.json(); } catch { }
  if (!r.ok) { const code = typeof j.detail === "string" ? j.detail : "error"; const e = new Error(ERR[code] || code); e.code = code; e.status = r.status; throw e; }
  return j;
}
async function run(fn, okMsg) { try { const r = await fn(); if (okMsg) toast(okMsg); return r; } catch (e) { toast(e.message, true); return null; } }

const av = u => `<div class="av" style="${u.photo ? `background-image:url('${esc(u.photo)}')` : ""}">${u.photo ? "" : esc((u.name || "?")[0])}</div>`;
const rank = () => RANK[ME.role] || 0;

// ---------------------------------------------------------------- shell
const TABS = [["dash", "📊 Bosh", 1], ["users", "👥 O'yinchilar", 1], ["reports", "🚩 Shikoyat", 1], ["orders", "🛒 Buyurtma", 2], ["tables", "🎮 Stollar", 1],
["photos", "🖼 Rasmlar", 1], ["filter", "🧹 Filtr", 1], ["audit", "📜 Audit", 1], ["broadcast", "📣 Xabar", 2], ["backup", "💾 Zaxira", 3]];
let badges = {};

function drawTabs() {
  $("#tabs").innerHTML = TABS.filter(t => rank() >= t[2]).map(t => `<button data-t="${t[0]}" class="${tab === t[0] ? "on" : ""}">${t[1]}${badges[t[0]] ? `<i>${badges[t[0]]}</i>` : ""}</button>`).join("");
}
$("#tabs").onclick = e => { const b = e.target.closest("button"); if (b) { tab = b.dataset.t; drawTabs(); render(); } };
$("#reload").onclick = () => render();
$("#sheet-x").onclick = closeSheet;
$("#sheet").onclick = e => { if (e.target.id === "sheet") closeSheet(); };
function openSheet(html) { $("#sheet-body").innerHTML = html; $("#sheet").hidden = false; }
function closeSheet() { $("#sheet").hidden = true; $("#sheet-body").innerHTML = ""; }

async function render() {
  const v = $("#view"); v.innerHTML = `<p class="muted">Yuklanmoqda…</p>`;
  const fn = { dash, users, reports, orders, tables, photos, filter, audit, broadcast, backup }[tab];
  try { await fn(v); } catch (e) { v.innerHTML = `<p class="muted">Xato: ${esc(e.message)}</p>`; }
  refreshBadges();
}
async function refreshBadges() {
  try { const s = await api("/stats"); badges = { reports: s.reports_new, orders: s.orders_pending }; drawTabs(); } catch { }
}

// ---------------------------------------------------------------- dashboard
const bars = (series, key, cls) => { const m = Math.max(1, ...series.map(s => s[key])); return `<div class="bars ${cls}">${series.map(s => `<div title="${s.d}: ${s[key]}" style="height:${Math.max(3, s[key] / m * 100)}%"></div>`).join("")}</div><div class="lbl"><span>${series[0].d}</span><span>${series[series.length - 1].d}</span></div>`; };
async function dash(v) {
  const s = await api("/stats");
  const st = (n, l) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`;
  v.innerHTML = `<div class="grid">${st(s.users, "jami o'yinchi")}${st(s.online, "hozir tarmoqda")}${st(s.seated, "stollarda (" + s.tables_live + " stol)")}${st(s.active24, "24 soatda faol")}${st(s.new24, "yangi (24 soat)")}
    ${st(s.reports_new, "yangi shikoyat")}${st(s.bans, "faol ban")}${st(s.mutes, "faol mute")}${rank() >= 2 ? st(s.orders_pending, "kutilayotgan buyurtma") + st(s.revenue_total + " " + esc(s.cur), "jami tushum") : ""}</div>
    <h3>Yangi o'yinchilar (14 kun)</h3>${bars(s.series, "new", "")}
    ${rank() >= 2 ? `<h3>Tushum (14 kun)</h3>${bars(s.series, "rev", "rev")}` : ""}`;
}

// ---------------------------------------------------------------- users
let uq = { q: "", flt: "", off: 0 };
async function users(v) {
  v.innerHTML = `<div class="row"><input type="search" id="uq" placeholder="id / @username / ism" value="${esc(uq.q)}"><select id="uf">
    ${[["", "hammasi"], ["online", "tarmoqda"], ["reported", "shikoyatli"], ["muted", "mute"], ["banned", "ban"], ["vip", "VIP"], ["staff", "staff"]].map(o => `<option value="${o[0]}" ${uq.flt === o[0] ? "selected" : ""}>${o[1]}</option>`).join("")}</select></div><div id="ul"></div>`;
  let t; $("#uq").oninput = e => { clearTimeout(t); t = setTimeout(() => { uq.q = e.target.value; uq.off = 0; loadUsers(); }, 250); };
  $("#uf").onchange = e => { uq.flt = e.target.value; uq.off = 0; loadUsers(); };
  await loadUsers();
}
async function loadUsers() {
  const r = await api(`/users?q=${encodeURIComponent(uq.q)}&flt=${uq.flt}&limit=30&offset=${uq.off}`);
  $("#ul").innerHTML = `<p class="muted">Topildi: ${r.total}</p><div class="list">${r.users.map(u => `<div class="item click" data-u="${u.id}">${av(u)}<div class="grow"><b>${esc(u.name)}</b> ${u.username ? `<span class="muted">@${esc(u.username)}</span>` : ""}
    <div class="muted">${u.id} · ${u.age || "?"} · ❤${u.hearts} · ${u.online ? "🟢 onlayn" : fmt(u.last_seen)}</div></div>
    ${u.role ? `<span class="pill blue">${ROLE_TXT[u.role]}</span>` : ""}${u.vip_until ? `<span class="pill yellow">VIP</span>` : ""}</div>`).join("")}</div>
    <div class="row">${uq.off > 0 ? `<button class="ghost" id="up">← Oldingi</button>` : ""}${uq.off + 30 < r.total ? `<button class="ghost" id="un">Keyingi →</button>` : ""}</div>`;
  $("#ul").onclick = e => { const i = e.target.closest("[data-u]"); if (i) userSheet(+i.dataset.u); };
  if ($("#up")) $("#up").onclick = () => { uq.off -= 30; loadUsers(); };
  if ($("#un")) $("#un").onclick = () => { uq.off += 30; loadUsers(); };
}

const DUR = [["1h", 3600], ["1d", 86400], ["7d", 7 * 86400], ["30d", 30 * 86400], ["∞", 0]];
async function userSheet(uid, d) {
  d = d || await run(() => api("/users/" + uid)); if (!d) return;
  const canMod = d.can_act, admin = rank() >= 2;
  const dur = id => `<select id="${id}">${DUR.map(o => `<option value="${o[1]}">${o[0]}</option>`).join("")}</select>`;
  const sanc = (s, name) => s ? `<span class="pill red">${name} → ${until(s.until)} · ${esc(s.reason)}</span>` : "";
  openSheet(`<div class="item" style="border:0;background:none;padding-left:0">${av(d)}<div class="grow"><b style="font-size:16px">${esc(d.name)}</b> ${d.username ? `<span class="muted">@${esc(d.username)}</span>` : ""}
    <div class="muted">ID ${d.id} · ${ROLE_TXT[d.role]} · ${d.lang} · ${d.online ? "🟢 onlayn" : "oxirgi: " + fmt(d.last_seen)}${d.table ? " · stol " + d.table : ""}</div></div></div>
    <div>${sanc(d.ban, "BAN")} ${sanc(d.mute, "MUTE")}</div>
    <div class="kv" style="margin-top:8px"><span>Balans</span><span>❤ ${d.hearts} · 😊 ${d.smiles} · 🎲 ${d.chances} · VIP: ${d.vip_until ? fmt(d.vip_until) : "—"}</span>
    <span>Faollik</span><span>💋 ${d.kisses} · 🎁 ${d.gifts_sent}/${d.gifts_received} · 💬 ${d.msgs} · 🎵 ${d.tracks}</span>
    <span>Intizom</span><span>⚠️ ${d.warns} ogohlantirish · 🚩 ${d.reports} shikoyat (${d.reporters} kishi)</span>
    <span>Ro'yxatdan</span><span>${fmt(d.created)} · bot: ${d.bot_started ? "ha" : "yo'q"}</span></div>
    ${!canMod ? `<p class="muted">Bu odamga amal qo'llab bo'lmaydi (o'zingiz yoki unvoni yuqori/teng).</p>` : `
    <h3>Jazo</h3>
    <div class="row"><input id="a-reason" placeholder="sabab / ogohlantirish matni" style="flex:1"><button class="warn" data-a="warn">⚠️ Warn</button></div>
    <div class="row">${dur("a-mdur")}<button class="warn" data-a="mute">🔇 Mute</button><button class="ghost" data-a="unmute">🔊 Unmute</button><button class="ghost" data-a="kick">👢 Kick</button></div>
    ${admin ? `<div class="row">${dur("a-bdur")}<button class="bad" data-a="ban">🚫 Ban</button><button class="ghost" data-a="unban">✅ Unban</button></div>` : ""}
    <h3>Profil</h3>
    <div class="row"><input id="a-name" placeholder="yangi ism" maxlength="24"><button data-a="rename">Ismni o'zgartirish</button><button class="ghost" data-a="unphoto" ${d.photo ? "" : "disabled"}>🖼 Rasmni olib tashlash</button></div>
    ${admin ? `<h3>Balans (limitsiz)</h3><div class="row"><select id="g-what"><option value="hearts">❤ yurak</option><option value="smiles">😊 smaylik</option><option value="chances">🎲 imkoniyat</option><option value="vip">VIP (kun)</option></select>
    <input id="g-n" type="number" placeholder="son (−/+)" style="width:110px"><button class="ok" data-a="give">Berish / olish</button></div>` : ""}
    ${rank() >= 3 ? `<h3>Rol</h3><div class="row"><select id="a-role">${["", "mod", "admin"].map(r => `<option value="${r}" ${d.role === r ? "selected" : ""}>${ROLE_TXT[r]}</option>`).join("")}</select><button data-a="role">Rolni saqlash</button></div>` : ""}`}
    <h3>Jazolar tarixi</h3>${d.history.map(h => `<div class="muted">${fmt(h.ts)} · ${h.kind} → ${until(h.until)} · ${esc(h.reason)} · #${h.by}${h.active ? " · <b>faol</b>" : ""}</div>`).join("") || `<div class="muted">—</div>`}
    <h3>Buyurtmalar</h3>${d.orders.map(o => `<div class="muted">#${o.id} ${fmt(o.ts)} · ${esc(o.kind)} ${esc(o.item)} · ${esc(o.price)} · ${o.status}</div>`).join("") || `<div class="muted">—</div>`}
    <h3>Oxirgi sovg'alar</h3>${d.gifts.map(g => `<div class="muted">${fmt(g.ts)} · ${g.emoji} #${g.sender} → #${g.target}</div>`).join("") || `<div class="muted">—</div>`}
    <h3>Audit</h3>${d.audit.map(a => `<div class="muted">${fmt(a.ts)} · #${a.actor} ${esc(a.action)} → #${a.target} ${esc(a.detail)}</div>`).join("") || `<div class="muted">—</div>`}`);
  $("#sheet-body").onclick = async e => {
    const b = e.target.closest("[data-a]"); if (!b) return;
    const g = id => $("#" + id)?.value;
    const act = b.dataset.a, body = { act, reason: g("a-reason") || "" };
    if (act === "warn") body.text = g("a-reason") || "qoidalarni buzmang";
    if (act === "mute") body.seconds = +g("a-mdur");
    if (act === "ban") body.seconds = +g("a-bdur");
    if (act === "rename") body.text = g("a-name") || "";
    if (act === "give") { body.what = g("g-what"); body.n = parseInt(g("g-n"), 10) || 0; if (!body.n) return toast("sonni kiriting", true); }
    if (act === "role") body.role = g("a-role");
    if (["ban", "kick", "unphoto"].includes(act) && !confirm("Tasdiqlaysizmi?")) return;
    const r = await run(() => api(`/users/${uid}/act`, "POST", body), "Bajarildi");
    if (r) { if (r.note === "not_seated") toast("hozir stolda emas"); userSheet(uid, r.user); if (tab === "users") loadUsers(); }
  };
}

// ---------------------------------------------------------------- reports
async function reports(v) {
  const list = await api("/reports?status=new");
  if (!list.length) { v.innerHTML = `<p class="muted">✅ Yangi shikoyat yo'q</p>`; return; }
  v.innerHTML = `<div class="list">${list.map(r => `<div class="item" style="flex-direction:column;align-items:stretch" data-r="${r.id}">
    <div class="row" style="margin:0"><b>#${r.id}</b><span class="pill red">${REASON[r.reason] || esc(r.reason)}</span><span class="muted">${fmt(r.ts)}</span><span class="grow"></span><span class="pill">jami: ${r.total}</span></div>
    <div><a href="#" data-u="${r.target.id}"><b>${esc(r.target.name)}</b></a> <span class="muted">(${r.target.id}) ← ${esc(r.reporter.name)}</span></div>
    ${r.chat.map(c => `<div class="chat">${esc(c)}</div>`).join("")}
    <div class="row"><button class="warn" data-o="warn">⚠️ Warn</button><button class="warn" data-o="m1d">🔇 Mute 1d</button><button class="ghost" data-o="kick">👢 Kick</button>
    ${rank() >= 2 ? `<button class="bad" data-o="ban7">🚫 Ban 7d</button>` : ""}<button class="ghost" data-o="dismiss">🗑 Rad etish</button></div></div>`).join("")}</div>`;
  v.onclick = async e => {
    const u = e.target.closest("[data-u]"); if (u) { e.preventDefault(); return userSheet(+u.dataset.u); }
    const b = e.target.closest("[data-o]"); if (!b) return;
    const id = b.closest("[data-r]").dataset.r;
    if (await run(() => api(`/reports/${id}/resolve`, "POST", { outcome: b.dataset.o }), "Bajarildi")) render();
  };
}

// ---------------------------------------------------------------- orders
let ost = "pending";
async function orders(v) {
  const list = await api("/orders?status=" + ost);
  v.innerHTML = `<div class="row">${[["pending", "kutilmoqda"], ["done", "tasdiqlangan"], ["rejected", "rad etilgan"], ["cancelled", "bekor"], ["", "hammasi"]].map(o => `<button class="${ost === o[0] ? "" : "ghost"}" data-s="${o[0]}">${o[1]}</button>`).join("")}</div>
    ${list.length ? `<div class="list">${list.map(o => `<div class="item" data-o="${o.id}"><div class="grow"><b>#${o.id}</b> ${esc(o.text)} <span class="pill ${o.status === "done" ? "green" : o.status === "pending" ? "yellow" : ""}">${o.status}</span>
    <div class="muted"><a href="#" data-u="${o.user_id}">${esc(o.name)}</a> ${o.username ? "@" + esc(o.username) : ""} · ${fmt(o.ts)}${o.note ? " · " + esc(o.note) : ""}</div></div>
    ${o.status === "pending" ? `<button class="ok" data-c="ok">✅</button><button class="bad" data-c="no">❌</button>` : ""}</div>`).join("")}</div>` : `<p class="muted">Bo'sh</p>`}`;
  v.onclick = async e => {
    const s = e.target.closest("[data-s]"); if (s) { ost = s.dataset.s; return render(); }
    const u = e.target.closest("[data-u]"); if (u) { e.preventDefault(); return userSheet(+u.dataset.u); }
    const c = e.target.closest("[data-c]"); if (!c) return;
    const id = c.closest("[data-o]").dataset.o;
    if (c.dataset.c === "ok") { if (!confirm("Pul keldimi? Tasdiqlangach o'yinchiga yuraklar beriladi.")) return; if (await run(() => api(`/orders/${id}/confirm`, "POST"), "Tasdiqlandi")) render(); }
    else { const note = prompt("Rad etish sababi (ixtiyoriy):"); if (note === null) return; if (await run(() => api(`/orders/${id}/reject`, "POST", { note }), "Rad etildi")) render(); }
  };
}

// ---------------------------------------------------------------- tables
async function tables(v) {
  const list = await api("/tables");
  v.innerHTML = list.length ? `<div class="list">${list.map(t => `<div class="item" style="flex-direction:column;align-items:stretch"><b>Stol ${t.id} <span class="muted">· ${t.players.length} kishi</span></b>
    <div>${t.players.map(p => `<span class="tag" data-u="${p.id}" style="cursor:pointer">${esc(p.name)}${p.role ? " ★" : ""}</span>`).join("")}</div></div>`).join("")}</div>` : `<p class="muted">Hozir hech kim stolda emas</p>`;
  v.onclick = e => { const u = e.target.closest("[data-u]"); if (u) userSheet(+u.dataset.u); };
}

// ---------------------------------------------------------------- photos
let poff = 0;
async function photos(v) {
  const r = await api(`/photos?limit=40&offset=${poff}`);
  v.innerHTML = `<p class="muted">Yuklangan rasmlar: ${r.total}. Rasmni bosing — profil ochiladi, u yerdan olib tashlash mumkin.</p><div class="photos">${r.photos.map(p => `<div class="ph" data-u="${p.id}"><img loading="lazy" src="${esc(p.photo)}" alt=""><div>${esc(p.name)}</div></div>`).join("")}</div>
    <div class="row">${poff > 0 ? `<button class="ghost" id="pp">← Oldingi</button>` : ""}${poff + 40 < r.total ? `<button class="ghost" id="pn">Keyingi →</button>` : ""}</div>`;
  v.onclick = e => { const u = e.target.closest("[data-u]"); if (u) userSheet(+u.dataset.u); };
  if ($("#pp")) $("#pp").onclick = () => { poff -= 40; render(); };
  if ($("#pn")) $("#pn").onclick = () => { poff += 40; render(); };
}

// ---------------------------------------------------------------- chat filter
async function filter(v) {
  const f = await api("/filter"), admin = rank() >= 2;
  v.innerHTML = `${admin ? `<div class="row"><input id="fw" placeholder="so'z yoki o'zak*"><button id="fa">Qo'shish</button></div>` : ""}
    <h3>So'zlar (${f.words.length})</h3><div>${f.words.map(w => `<span class="tag">${esc(w)}${admin ? `<button data-w="${esc(w)}">✕</button>` : ""}</span>`).join("")}</div>
    <h3>Filtr to'sgan oxirgi xabarlar</h3>${f.recent.map(r => `<div class="muted">${fmt(r.ts)} · <a href="#" data-u="${r.uid}">${esc(r.name)}</a> · <span class="pill">${esc(r.kind)}</span> ${esc(r.text)}</div>`).join("") || `<div class="muted">—</div>`}`;
  if (admin) $("#fa").onclick = async () => { const w = $("#fw").value.trim(); if (w && await run(() => api("/filter/words", "POST", { word: w }), "Qo'shildi")) render(); };
  v.onclick = async e => {
    const u = e.target.closest("[data-u]"); if (u) { e.preventDefault(); return userSheet(+u.dataset.u); }
    const w = e.target.closest("[data-w]"); if (w && confirm(`"${w.dataset.w}" o'chirilsinmi?`) && await run(() => api("/filter/words/" + encodeURIComponent(w.dataset.w), "DELETE"), "O'chirildi")) render();
  };
}

// ---------------------------------------------------------------- audit
async function audit(v) {
  const list = await api("/audit?limit=100");
  v.innerHTML = `<div class="list">${list.map(a => `<div class="item"><div class="grow"><b>${esc(a.action)}</b> <span class="muted">${fmt(a.ts)}</span>
    <div class="muted">${esc(a.actor_name)} (#${a.actor})${a.target ? ` → <a href="#" data-u="${a.target}">${esc(a.target_name)}</a>` : ""} · ${esc(a.detail)}</div></div></div>`).join("") || `<p class="muted">Bo'sh</p>`}</div>`;
  v.onclick = e => { const u = e.target.closest("[data-u]"); if (u) { e.preventDefault(); userSheet(+u.dataset.u); } };
}

// ---------------------------------------------------------------- broadcast
async function broadcast(v) {
  const c = await api("/broadcast", "POST", { preview: true });
  v.innerHTML = `<p class="muted">Xabar botni ishga tushirgan va bildirishnomani o'chirmagan <b>${c.recipients}</b> kishiga boradi. Ostida "O'ynash" tugmasi bo'ladi.</p>
    <textarea id="bt" maxlength="3500" placeholder="Xabar matni"></textarea><div class="row"><button id="bs">📣 Yuborish</button><span id="bst" class="muted"></span></div>`;
  $("#bs").onclick = async () => {
    const text = $("#bt").value.trim(); if (!text) return toast("matn bo'sh", true);
    if (!confirm(`${c.recipients} kishiga yuborilsinmi?`)) return;
    if (await run(() => api("/broadcast", "POST", { text, preview: false }), "Yuborish boshlandi")) poll();
  };
  async function poll() {
    const s = await run(() => api("/broadcast/status")); if (!s) return;
    $("#bst") && ($("#bst").textContent = `${s.sent + s.failed}/${s.total} (xato: ${s.failed})`);
    if (s.running && tab === "broadcast") setTimeout(poll, 1000);
  }
  poll();
}

// ---------------------------------------------------------------- backups
async function backup(v) {
  const b = await api("/backups");
  v.innerHTML = `<p class="muted">Avtomatik: har ${b.every_h} soatda, oxirgi ${b.keep} ta saqlanadi.</p><div class="row"><button id="bn">💾 Hozir zaxira olish</button></div>
    <div class="list">${b.list.map(x => `<div class="item"><div class="grow"><b>${esc(x.name)}</b><div class="muted">${x.size} · ${fmt(x.ts)}</div></div></div>`).join("") || `<p class="muted">Hali yo'q</p>`}</div>
    <p class="muted">Tiklash serverda: <code>.venv/bin/python restore_backup.py latest</code> (avval serverni to'xtating).</p>`;
  $("#bn").onclick = async () => { $("#bn").disabled = true; if (await run(() => api("/backups", "POST"), "Zaxira tayyor")) render(); else $("#bn").disabled = false; };
}

// ---------------------------------------------------------------- start
(async () => {
  try { ME = await api("/me"); } catch (e) {
    $("#view").innerHTML = `<p class="muted">${e.status === 403 ? "Bu sahifa faqat staff uchun." : "Kirib bo'lmadi: " + esc(e.message)}<br>Telegram ichidan, /panel orqali oching.</p>`; return;
  }
  $("#who").textContent = ME.name; $("#role").textContent = ROLE_TXT[ME.role];
  drawTabs(); render();
})();

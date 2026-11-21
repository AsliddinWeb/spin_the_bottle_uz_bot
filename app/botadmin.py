"""Staff commands inside the Telegram bot (owner / admin / moderator).

Everything is role-checked in `moderation`; handlers only parse input and format answers.
Commands are silent for ordinary players (no reply at all), so nobody learns they exist.
"""
import json
import time

from aiogram import F
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from . import bot as botmod, chatfilter, config, db, moderation as mod, orders
from .bot import dp

ERR = {
    "self": "o'zingizga qo'llab bo'lmaydi", "rank": "bu odam sizdan yuqori yoki teng darajada",
    "need_admin": "bunga admin huquqi kerak", "need_mod": "bunga moderator huquqi kerak", "need_owner": "faqat owner",
    "no_user": "foydalanuvchi topilmadi", "bad_role": "rol: admin | mod | none", "bad_what": "hearts | smiles | chances | vip",
    "is_owner": "owner rolini o'zgartirib bo'lmaydi",
}
PLAYER_TEXT = {  # messages sent to the sanctioned player
    "ban": {"uz": "🚫 Akkauntingiz bloklandi.\nSabab: {r}\nMuddat: {u}", "ru": "🚫 Ваш аккаунт заблокирован.\nПричина: {r}\nСрок: {u}", "en": "🚫 Your account was banned.\nReason: {r}\nUntil: {u}"},
    "mute": {"uz": "🔇 Chatga yozish cheklandi.\nSabab: {r}\nMuddat: {u}", "ru": "🔇 Вам запрещено писать в чат.\nПричина: {r}\nСрок: {u}", "en": "🔇 You were muted.\nReason: {r}\nUntil: {u}"},
    "warn": {"uz": "⚠️ Ogohlantirish: {r}", "ru": "⚠️ Предупреждение: {r}", "en": "⚠️ Warning: {r}"},
    "unban": {"uz": "✅ Blok olib tashlandi.", "ru": "✅ Блокировка снята.", "en": "✅ Your ban was lifted."},
}


def _actor(m_or_c) -> int:
    return m_or_c.from_user.id


def _staff(uid: int) -> bool:
    return mod.rank(uid) >= mod.RANK["mod"]


async def _tell_player(uid: int, kind: str, reason: str = "", until: int = 0) -> None:
    u = db.get_user(uid)
    if not u or not u["bot_started"] or not botmod.bot:
        return
    lang = u["lang"] if u["lang"] in ("uz", "ru", "en") else "en"
    try:
        await botmod.bot.send_message(uid, PLAYER_TEXT[kind][lang].format(r=reason or "—", u=mod.human_until(until)))
    except Exception:
        pass


async def notify_player(uid: int, kind: str, reason: str = "", until: int = 0) -> None:
    await _tell_player(uid, kind, reason, until)


ORDER_TEXT = {
    "done": {"uz": "✅ #{n} buyurtma tasdiqlandi: {w}. Rahmat! 💖", "ru": "✅ Заказ #{n} подтверждён: {w}. Спасибо! 💖", "en": "✅ Order #{n} confirmed: {w}. Thank you! 💖"},
    "no": {"uz": "❌ #{n} buyurtma rad etildi.{r}", "ru": "❌ Заказ #{n} отклонён.{r}", "en": "❌ Order #{n} was declined.{r}"},
}


async def _tell_order(o, outcome: str, note: str = "") -> None:
    u = db.get_user(o["user_id"])
    if not u or not u["bot_started"] or not botmod.bot:
        return
    lang = u["lang"] if u["lang"] in ("uz", "ru", "en") else "en"
    try:
        await botmod.bot.send_message(o["user_id"], ORDER_TEXT[outcome][lang].format(n=o["id"], w=orders.describe(o), r=(" " + note) if note else ""))
    except Exception:
        pass
    await _hub().push_me(o["user_id"])


def _order_kb(oid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Tasdiqlash (pul keldi)", callback_data=f"o:{oid}:ok"),
                                                   InlineKeyboardButton(text="❌ Rad etish", callback_data=f"o:{oid}:no")]])


def _order_text(o) -> str:
    u = db.get_user(o["user_id"])
    who = f"<a href=\"tg://user?id={o['user_id']}\">{_e(u['name'] if u else '?')}</a>" + (f" @{u['username']}" if u and u["username"] else "")
    st = {"pending": "⏳ kutilmoqda", "done": "✅ tasdiqlangan", "rejected": "❌ rad etilgan", "cancelled": "🚫 bekor qilingan"}[o["status"]]
    return f"🛒 <b>Buyurtma #{o['id']}</b> — {st}\n{who} (<code>{o['user_id']}</code>)\n{_e(orders.describe(o))}"


async def alert_order(o, user) -> None:
    """Tell every admin+ about a new order (moderators never see money)."""
    if not botmod.bot:
        return
    for sid in mod.staff_ids("admin"):
        try:
            await botmod.bot.send_message(sid, _order_text(o), parse_mode="HTML", reply_markup=_order_kb(o["id"]))
        except Exception:
            pass


async def alert_staff(text: str) -> None:
    if not botmod.bot:
        return
    for sid in mod.staff_ids():
        try:
            await botmod.bot.send_message(sid, text)
        except Exception:
            pass


def _hub():
    from .game import hub
    return hub


def _card(u) -> str:
    s = mod.user_summary(u)
    ban, mute = s["ban"], s["mute"]
    lines = [
        f"👤 <b>{_e(u['name'])}</b>, {u['age']}  {'@' + u['username'] if u['username'] else ''}",
        f"ID <code>{u['id']}</code> · rol: <b>{s['role'] or 'player'}</b> · til: {u['lang']}",
        f"❤ {u['hearts']} · 😊 {u['smiles']} · 🎲 {u['chances']} · VIP: {mod.human_until(u['vip_until']) if u['vip_until'] > time.time() else '—'}",
        f"💋 {u['kisses']} · 🎁 {u['gifts_sent']}/{u['gifts_received']} · 💬 {u['msgs']} · 🎵 {u['tracks']}",
        f"⚠️ ogohlantirish: {s['warns']} · 🚩 shikoyat: {s['reports']} ({s['reporters']} kishi)",
        f"🚫 ban: {('ha, ' + mod.human_until(ban['until']) + ' — ' + ban['reason']) if ban else "yo'q"}",
        f"🔇 mute: {('ha, ' + mod.human_until(mute['until']) + ' — ' + mute['reason']) if mute else "yo'q"}",
    ]
    return "\n".join(lines)


def _e(t: str) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _user_kb(uid: int, actor: int) -> InlineKeyboardMarkup:
    b = lambda t, a: InlineKeyboardButton(text=t, callback_data=f"u:{uid}:{a}")
    rows = [[b("⚠️ Warn", "warn"), b("🔇 Mute 1h", "m1h"), b("🔇 Mute 1d", "m1d")],
            [b("🔊 Unmute", "unmute"), b("👢 Kick", "kick"), b("🖼 Rasmni olib tashlash", "unphoto")]]
    if mod.rank(actor) >= mod.RANK["admin"]:
        rows.append([b("🚫 Ban 7d", "ban7"), b("⛔ Ban ∞", "banp"), b("✅ Unban", "unban")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _do_sanction(actor: int, target: int, kind: str, seconds: int, reason: str) -> str:
    r = mod.sanction(actor, target, kind, seconds, reason)
    if isinstance(r, str):
        return "❌ " + ERR.get(r, r)
    until = int(time.time()) + seconds if seconds else 0
    await _tell_player(target, kind, reason, until)
    await _hub().apply_sanctions(target) if kind == "ban" else None
    return f"✅ {kind} #{target} → {mod.human_until(until)}"


# ---------------------------------------------------------------- commands
HELP = {
    "mod": ("<b>Moderator</b>\n/panel — web admin panel\n/user &lt;id|@nom&gt; — kartochka + tugmalar\n/reports — shikoyatlar\n/warn id matn\n/mute id 30m|2h|1d sabab\n/unmute id\n"
            "/kick id\n/rename id yangi_ism\n/unphoto id\n/audit [id]\n/stats\n/filtered — filtr to'sgan oxirgi xabarlar\n/words"),
    "admin": ("\n\n<b>Admin</b>\n/ban id 7d|perm sabab\n/unban id\n/give id hearts|smiles|chances|vip son [sabab] — manfiy son ayiradi (vip: kun)\n/broadcast matn\n/orders — kutilayotgan buyurtmalar · /confirm id · /reject id [sabab]\n/addword so'z|o'zak* · /delword so'z"),
    "owner": "\n\n<b>Owner</b>\n/role id admin|mod|none\n/backup — hozir zaxira nusxa · /backups — ro'yxat",
}


@dp.message(Command("admin"))
async def c_admin(m: Message):
    r = mod.role_of(_actor(m))
    if not r:
        return
    t = HELP["mod"] + (HELP["admin"] if mod.RANK[r] >= 2 else "") + (HELP["owner"] if r == "owner" else "")
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("panel"))
async def c_panel(m: Message):
    if not _staff(_actor(m)):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Admin panel", web_app=WebAppInfo(url=config.WEBAPP_URL + "/admin"))]])
    await m.answer("Admin panel:", reply_markup=kb)


async def _target(m: Message, tok: str):
    u = mod.find_user(tok) if tok else None
    if not u:
        await m.answer("❌ " + ERR["no_user"])
    return u


@dp.message(Command("user"))
async def c_user(m: Message, command: CommandObject):
    if not _staff(_actor(m)):
        return
    u = await _target(m, (command.args or "").strip())
    if u:
        await m.answer(_card(u), parse_mode="HTML", reply_markup=_user_kb(u["id"], _actor(m)))


def _args(command: CommandObject, n: int) -> list[str]:
    return (command.args or "").split(None, n - 1)


@dp.message(Command("ban"))
async def c_ban(m: Message, command: CommandObject):
    if mod.rank(_actor(m)) < mod.RANK["admin"]:
        return
    a = _args(command, 3)
    if len(a) < 2 or (secs := mod.parse_duration(a[1])) is None:
        return await m.answer("/ban id 7d|perm sabab")
    u = await _target(m, a[0])
    if u:
        await m.answer(await _do_sanction(_actor(m), u["id"], "ban", secs, a[2] if len(a) > 2 else "—"))


@dp.message(Command("mute"))
async def c_mute(m: Message, command: CommandObject):
    if not _staff(_actor(m)):
        return
    a = _args(command, 3)
    if len(a) < 2 or (secs := mod.parse_duration(a[1])) is None:
        return await m.answer("/mute id 30m|2h|1d|perm sabab")
    u = await _target(m, a[0])
    if u:
        await m.answer(await _do_sanction(_actor(m), u["id"], "mute", secs, a[2] if len(a) > 2 else "—"))


async def _lift(m: Message, command: CommandObject, kind: str):
    if not _staff(_actor(m)):
        return
    u = await _target(m, (command.args or "").strip())
    if not u:
        return
    r = mod.lift(_actor(m), u["id"], kind)
    if isinstance(r, str):
        return await m.answer("❌ " + ERR.get(r, r))
    await m.answer(f"✅ {kind} olib tashlandi" if r else "ℹ️ faol jazo yo'q")
    if r and kind == "ban":
        await _tell_player(u["id"], "unban")


@dp.message(Command("unban"))
async def c_unban(m: Message, command: CommandObject):
    await _lift(m, command, "ban")


@dp.message(Command("unmute"))
async def c_unmute(m: Message, command: CommandObject):
    await _lift(m, command, "mute")


@dp.message(Command("warn"))
async def c_warn(m: Message, command: CommandObject):
    if not _staff(_actor(m)):
        return
    a = _args(command, 2)
    if len(a) < 2:
        return await m.answer("/warn id matn")
    u = await _target(m, a[0])
    if u:
        r = mod.warn(_actor(m), u["id"], a[1])
        await m.answer("❌ " + ERR.get(r, r) if r else "✅ ogohlantirish yuborildi")
        if not r:
            await _tell_player(u["id"], "warn", a[1])


@dp.message(Command("kick"))
async def c_kick(m: Message, command: CommandObject):
    if not _staff(_actor(m)):
        return
    u = await _target(m, (command.args or "").strip())
    if not u:
        return
    if err := mod.can_act(_actor(m), u["id"]):
        return await m.answer("❌ " + ERR[err])
    mod.audit(_actor(m), "kick", u["id"])
    await m.answer("✅ stoldan chiqarildi" if await _hub().kick_player(u["id"]) else "ℹ️ hozir stolda emas")


@dp.message(Command("rename"))
async def c_rename(m: Message, command: CommandObject):
    if not _staff(_actor(m)):
        return
    a = _args(command, 2)
    if len(a) < 2:
        return await m.answer("/rename id yangi_ism")
    u = await _target(m, a[0])
    if u:
        r = mod.rename(_actor(m), u["id"], a[1])
        await m.answer("❌ " + ERR.get(r, r) if r else "✅ ism o'zgartirildi")


@dp.message(Command("unphoto"))
async def c_unphoto(m: Message, command: CommandObject):
    if not _staff(_actor(m)):
        return
    u = await _target(m, (command.args or "").strip())
    if u:
        r = mod.remove_photo(_actor(m), u["id"])
        await m.answer("❌ " + ERR.get(r, r) if r else "✅ rasm olib tashlandi")


@dp.message(Command("give"))
async def c_give(m: Message, command: CommandObject):
    if mod.rank(_actor(m)) < mod.RANK["admin"]:
        return
    a = _args(command, 4)
    if len(a) < 3 or not a[2].lstrip("-").isdigit():
        return await m.answer("/give id hearts|smiles|chances|vip son [sabab]")
    u = await _target(m, a[0])
    if not u:
        return
    r = mod.give(_actor(m), u["id"], a[1].lower(), int(a[2]), a[3] if len(a) > 3 else "—")
    if r:
        return await m.answer("❌ " + ERR.get(r, r))
    await _hub().push_me(u["id"])
    await m.answer("✅ " + _card(db.get_user(u["id"])).split("\n")[2], parse_mode="HTML")


@dp.message(Command("role"))
async def c_role(m: Message, command: CommandObject):
    if mod.rank(_actor(m)) < mod.RANK["owner"]:
        return
    a = _args(command, 2)
    if len(a) < 2:
        return await m.answer("/role id admin|mod|none")
    u = await _target(m, a[0])
    if u:
        r = mod.set_role(_actor(m), u["id"], "" if a[1].lower() in ("none", "player", "0") else a[1].lower())
        await m.answer("❌ " + ERR.get(r, r) if r else f"✅ rol: {a[1]}")


@dp.message(Command("audit"))
async def c_audit(m: Message, command: CommandObject):
    if not _staff(_actor(m)):
        return
    tok = (command.args or "").strip()
    u = mod.find_user(tok) if tok else None
    rows = mod.audit_rows(u["id"] if u else 0)
    if not rows:
        return await m.answer("ℹ️ bo'sh")
    await m.answer("\n".join(f"{time.strftime('%m-%d %H:%M', time.localtime(r['ts']))} #{r['actor']} {r['action']} → #{r['target']} {_e(r['detail'])}" for r in rows))


@dp.message(Command("stats"))
async def c_stats(m: Message):
    if not _staff(_actor(m)):
        return
    now = int(time.time())
    one = lambda sql, *a: db.q1(sql, *a)[0]
    await m.answer(
        f"👥 o'yinchilar: {one('SELECT COUNT(*) FROM users')} (24 soatda faol: {one('SELECT COUNT(*) FROM users WHERE last_seen>?', now - 86400)}, yangi: {one('SELECT COUNT(*) FROM users WHERE created>?', now - 86400)})\n"
        f"🟢 hozir tarmoqda: {len(_hub().clients)}\n🚫 ban: {one('SELECT COUNT(*) FROM sanctions WHERE kind=? AND active=1', 'ban')} · 🔇 mute: {one('SELECT COUNT(*) FROM sanctions WHERE kind=? AND active=1', 'mute')}\n"
        f"🚩 yangi shikoyat: {one('SELECT COUNT(*) FROM reports WHERE status=?', 'new')}\n"
        f"⭐ Stars (jami): {one('SELECT COALESCE(SUM(stars),0) FROM payments')} · 24 soatda: {one('SELECT COALESCE(SUM(stars),0) FROM payments WHERE ts>?', now - 86400)}")


# ---------------------------------------------------------------- orders (admin+)
@dp.message(Command("orders"))
async def c_orders(m: Message):
    if mod.rank(_actor(m)) < mod.RANK["admin"]:
        return
    rows = orders.pending()
    if not rows:
        return await m.answer("✅ kutilayotgan buyurtma yo'q")
    for o in rows:
        await m.answer(_order_text(o), parse_mode="HTML", reply_markup=_order_kb(o["id"]))


async def _finish_order(actor: int, oid: int, ok: bool, note: str = "") -> str:
    r = orders.confirm(actor, oid) if ok else orders.reject(actor, oid, note)
    if isinstance(r, str):
        return "❌ " + {"need_admin": ERR["need_admin"], "no_order": "buyurtma topilmadi", "handled": "allaqachon ko'rib chiqilgan"}.get(r, r)
    await _tell_order(r, "done" if ok else "no", note)
    return f"✅ #{oid} {'tasdiqlandi: ' + orders.describe(r) if ok else 'rad etildi'}"


@dp.message(Command("confirm"))
async def c_confirm(m: Message, command: CommandObject):
    if mod.rank(_actor(m)) < mod.RANK["admin"]:
        return
    a = (command.args or "").split()
    if not a or not a[0].isdigit():
        return await m.answer("/confirm buyurtma_raqami")
    await m.answer(await _finish_order(_actor(m), int(a[0]), True))


@dp.message(Command("reject"))
async def c_reject(m: Message, command: CommandObject):
    if mod.rank(_actor(m)) < mod.RANK["admin"]:
        return
    a = _args(command, 2)
    if not a or not a[0].isdigit():
        return await m.answer("/reject buyurtma_raqami [sabab]")
    await m.answer(await _finish_order(_actor(m), int(a[0]), False, a[1] if len(a) > 1 else ""))


@dp.callback_query(F.data.startswith("o:"))
async def cb_order(c: CallbackQuery):
    if mod.rank(c.from_user.id) < mod.RANK["admin"]:
        return await c.answer()
    _, oid, act = c.data.split(":")
    res = await _finish_order(c.from_user.id, int(oid), act == "ok")
    await c.answer(res[:180])
    o = orders.get(int(oid))
    if o:
        try:
            await c.message.edit_text(_order_text(o), parse_mode="HTML", reply_markup=_order_kb(o["id"]) if o["status"] == "pending" else None)
        except Exception:
            pass


# ---------------------------------------------------------------- backups (owner)
@dp.message(Command("backup"))
async def c_backup(m: Message):
    if mod.rank(_actor(m)) < mod.RANK["owner"]:
        return
    import asyncio
    from . import backup
    try:
        p = await asyncio.to_thread(backup.make_backup)
    except Exception as e:
        return await m.answer(f"❌ zaxira xatosi: {_e(e)}")
    mod.audit(_actor(m), "backup", 0, p.name)
    await m.answer(f"✅ {p.name} ({backup.human_size(p)})\nJami nusxalar: {len(backup.list_backups())} (oxirgi {backup.KEEP} tasi saqlanadi)\nPapka: {backup.DIR}")


@dp.message(Command("backups"))
async def c_backups(m: Message):
    if mod.rank(_actor(m)) < mod.RANK["owner"]:
        return
    from . import backup
    bs = backup.list_backups()
    await m.answer("\n".join(f"{b.name}  {backup.human_size(b)}" for b in bs[-10:]) or "ℹ️ zaxira hali yo'q")


# ---------------------------------------------------------------- chat filter words
@dp.message(Command("words"))
async def c_words(m: Message):
    if not _staff(_actor(m)):
        return
    w = chatfilter.words()
    await m.answer(f"📝 {len(w)} ta so'z (* = o'zak):\n" + ", ".join(w)[:3800])


@dp.message(Command("addword"))
async def c_addword(m: Message, command: CommandObject):
    if mod.rank(_actor(m)) < mod.RANK["admin"]:
        return
    w = (command.args or "").strip()
    ok = chatfilter.add_word(w, _actor(m))
    if ok:
        mod.audit(_actor(m), "addword", 0, w)
    await m.answer("✅ qo'shildi" if ok else "❌ 2–30 belgi, bo'sh joysiz. Oxiriga * qo'ysangiz o'zak bo'ladi (masalan: pizd*)")


@dp.message(Command("delword"))
async def c_delword(m: Message, command: CommandObject):
    if mod.rank(_actor(m)) < mod.RANK["admin"]:
        return
    w = (command.args or "").strip()
    ok = chatfilter.del_word(w)
    if ok:
        mod.audit(_actor(m), "delword", 0, w)
    await m.answer("✅ o'chirildi" if ok else "ℹ️ bunday so'z yo'q")


@dp.message(Command("filtered"))
async def c_filtered(m: Message):
    if not _staff(_actor(m)):
        return
    rows = list(chatfilter.FILTERED)[-15:]
    if not rows:
        return await m.answer("ℹ️ filtr hali hech narsa to'smagan")
    await m.answer("\n".join(f"{time.strftime('%H:%M', time.localtime(t))} #{u} [{k}] {_e(x)}" for t, u, k, x in reversed(rows)))


# ---------------------------------------------------------------- reports review
REASON_TXT = {"abuse": "haqorat", "spam": "spam", "nsfw": "18+/noo'rin", "fraud": "aldash", "age": "yoshi noto'g'ri"}


def _report_view(r) -> tuple[str, InlineKeyboardMarkup]:
    t = db.get_user(r["target"]); rep = db.get_user(r["reporter"])
    snap = json.loads(r["snapshot"] or "{}")
    chat = "\n".join(f"  • {_e(x)}" for x in snap.get("chat", [])) or "  —"
    n = db.q1("SELECT COUNT(*) c FROM reports WHERE target=? AND status!='dismissed'", r["target"])["c"]
    text = (f"🚩 <b>Shikoyat #{r['id']}</b> — {REASON_TXT.get(r['reason'], r['reason'])}\n"
            f"Kimga: <b>{_e(t['name'] if t else '?')}</b> (<code>{r['target']}</code>) · jami shikoyat: {n}\n"
            f"Kimdan: {_e(rep['name'] if rep else '?')} (<code>{r['reporter']}</code>)\n"
            f"Oxirgi xabarlari:\n{chat}")
    b = lambda t, a: InlineKeyboardButton(text=t, callback_data=f"r:{r['id']}:{a}")
    rows = [[b("⚠️ Warn", "warn"), b("🔇 Mute 1d", "m1d"), b("👢 Kick", "kick")],
            [b("🚫 Ban 7d", "ban7"), b("🗑 Rad etish", "dismiss"), b("➡️ Keyingisi", "next")]]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("reports"))
async def c_reports(m: Message):
    if not _staff(_actor(m)):
        return
    r = mod.next_report()
    if not r:
        return await m.answer("✅ yangi shikoyat yo'q")
    text, kb = _report_view(r)
    await m.answer(text, parse_mode="HTML", reply_markup=kb)


# ---------------------------------------------------------------- inline buttons
async def _apply(actor: int, uid: int, act: str) -> str:
    if act == "warn":
        r = mod.warn(actor, uid, "qoidalarni buzmang / please follow the rules")
        if not r:
            await _tell_player(uid, "warn", "qoidalarni buzmang")
        return "⚠️ ogohlantirish yuborildi" if not r else "❌ " + ERR.get(r, r)
    if act in ("m1h", "m1d"):
        return await _do_sanction(actor, uid, "mute", 3600 if act == "m1h" else 86400, "moderator")
    if act == "ban7":
        return await _do_sanction(actor, uid, "ban", 7 * 86400, "moderator")
    if act == "banp":
        return await _do_sanction(actor, uid, "ban", 0, "moderator")
    if act == "unmute":
        r = mod.lift(actor, uid, "mute")
        return "🔊 mute olib tashlandi" if r == 1 else ("ℹ️ faol mute yo'q" if r == 0 else "❌ " + ERR.get(r, r))
    if act == "unban":
        r = mod.lift(actor, uid, "ban")
        if r == 1:
            await _tell_player(uid, "unban")
        return "✅ ban olib tashlandi" if r == 1 else ("ℹ️ faol ban yo'q" if r == 0 else "❌ " + ERR.get(r, r))
    if act == "kick":
        if err := mod.can_act(actor, uid):
            return "❌ " + ERR[err]
        mod.audit(actor, "kick", uid)
        return "👢 chiqarildi" if await _hub().kick_player(uid) else "ℹ️ hozir stolda emas"
    if act == "unphoto":
        r = mod.remove_photo(actor, uid)
        return "🖼 olib tashlandi" if not r else "❌ " + ERR.get(r, r)
    return "?"


@dp.callback_query(F.data.startswith("u:"))
async def cb_user(c: CallbackQuery):
    if not _staff(c.from_user.id):
        return await c.answer()
    _, uid, act = c.data.split(":")
    res = await _apply(c.from_user.id, int(uid), act)
    await c.answer(res[:180], show_alert=False)
    u = db.get_user(int(uid))
    if u:
        try:
            await c.message.edit_text(_card(u), parse_mode="HTML", reply_markup=_user_kb(u["id"], c.from_user.id))
        except Exception:
            pass


@dp.callback_query(F.data.startswith("r:"))
async def cb_report(c: CallbackQuery):
    if not _staff(c.from_user.id):
        return await c.answer()
    _, rid, act = c.data.split(":")
    rid = int(rid)
    r = db.q1("SELECT * FROM reports WHERE id=?", rid)
    if not r:
        return await c.answer("yo'q")
    if act != "next":
        if r["status"] != "new":
            await c.answer("allaqachon ko'rib chiqilgan")
        else:
            res = "rad etildi" if act == "dismiss" else await _apply(c.from_user.id, r["target"], act)
            await c.answer(res[:180])
            if act == "dismiss" or not res.startswith("❌"):
                mod.resolve_report(rid, c.from_user.id, act)
    else:
        await c.answer()
    nxt = mod.next_report(rid)
    if not nxt:
        return await c.message.edit_text("✅ yangi shikoyat qolmadi")
    text, kb = _report_view(nxt)
    await c.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

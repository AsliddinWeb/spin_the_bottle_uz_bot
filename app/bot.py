"""Telegram bot: /start, referral, Stars payments."""
import asyncio
import random
import time

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import (FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice,
                           MenuButtonWebApp, Message, PreCheckoutQuery, WebAppInfo)

from . import config, db, economy
from .catalog import PACKS, VIP_DAYS, VIP_STARS

TEXT = {
    "uz": {
        "welcome": "Salom! Bu o'yin yangi tanishlar, do'stlar va hatto sevgingni topishga yordam beradi.\n"
                   "💬 Faqat haqiqiy odamlar bilan chatda suhbatlash, yangi tanishlar top va real hayotda uchrash!\n"
                   "💖 Sherigingga yoqmoqchimisan? Sovg'alar, kokteyllar tuhfa qil va o'pich yubor\n"
                   "🤡 Kimdir bezovta qiladimi? Uni pomidor, emizik bilan uring yoki masxaraboz qalpog'ini sovg'a qiling\n"
                   "🎵 YouTube'dan sevimli treklaringni o'yin stoli ustida qo'y\n"
                   "🎮 O'YNASH tugmasini bos, o'yin stoliga qo'shil, o'p va tanish!",
        "play": "O'YNASH 🍾", "bonus": "🎁 Do'sting qo'shildi: +20 ❤️", "paid": "✅ To'lov qabul qilindi! Rahmat 💖",
        "support": "To'lov bo'yicha savol: {s}",
    },
    "ru": {
        "welcome": "Привет! Эта игра позволит тебе находить новые знакомства, друзей или даже свою любовь.\n"
                   "💬 Общайся только с реальными людьми в чате, находи новые знакомства и встречайся в реале!\n"
                   "💖 Хочешь понравиться партнеру? Дари подарки, коктейли и отправляй поцелуи\n"
                   "🤡 Кто-то раздражает? Забросай его помидорами, сосками или подари шапку шута\n"
                   "🎵 Запускай любимые треки с YouTube прямо за игровым столом\n"
                   "🎮 Жми ИГРАТЬ, присоединяйся к игровому столу, целуй и знакомься!",
        "play": "ИГРАТЬ 🍾", "bonus": "🎁 Твой друг присоединился: +20 ❤️", "paid": "✅ Оплата получена! Спасибо 💖",
        "support": "Вопросы по оплате: {s}",
    },
    "en": {
        "welcome": "Hi! This game helps you meet new people, make friends or even find love.\n"
                   "💬 Chat with real people only, meet new people and meet up in real life!\n"
                   "💖 Want to impress your partner? Send gifts, cocktails and kisses\n"
                   "🤡 Someone annoying? Throw tomatoes, pacifiers at them or give them a jester hat\n"
                   "🎵 Play your favourite YouTube tracks right at the game table\n"
                   "🎮 Press PLAY, join a game table, kiss and get to know each other!",
        "play": "PLAY 🍾", "bonus": "🎁 Your friend joined: +20 ❤️", "paid": "✅ Payment received! Thank you 💖",
        "support": "Payment support: {s}",
    },
}


def lang_of(code: str | None) -> str:
    code = (code or "").lower()[:2]
    return code if code in TEXT else "en"


bot: Bot | None = Bot(config.BOT_TOKEN) if config.BOT_TOKEN else None
bot_username = ""
banner_id = ""
dp = Dispatcher()


@dp.message(Command("start"))
async def on_start(m: Message, command: CommandObject):
    tg = m.from_user
    lang = lang_of(tg.language_code)
    u, created = db.ensure_user(tg.id, tg.first_name or tg.username or "Player", lang=lang, username=tg.username or "")
    if created and command.args and command.args.startswith("ref_"):
        inviter = command.args[4:]
        if inviter.isdigit() and int(inviter) != tg.id and db.get_user(int(inviter)):
            inviter = int(inviter)
            db.x("INSERT OR IGNORE INTO referrals VALUES(?,?)", inviter, tg.id)
            db.x("UPDATE users SET ref_by=? WHERE id=?", inviter, tg.id)
            db.add_hearts(inviter, 50 if tg.is_premium else 20)  # friend with Telegram Premium pays more
            db.add_hearts(tg.id, 20)
            try:
                await bot.send_message(inviter, TEXT[db.get_user(inviter)["lang"]]["bonus"])
            except Exception:
                pass
    db.x("UPDATE users SET bot_started=1, last_seen=? WHERE id=?", int(time.time()), tg.id)
    t = TEXT[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t["play"], web_app=WebAppInfo(url=config.WEBAPP_URL))
    ]])
    global banner_id
    try:
        photo = banner_id or FSInputFile(config.ROOT / "static" / "banner.png")
        sent = await m.answer_photo(photo, caption=t["welcome"], reply_markup=kb)
        if not banner_id and sent.photo:
            banner_id = sent.photo[-1].file_id  # reuse the uploaded file next time
    except Exception as e:
        print("banner:", e)
        await m.answer(t["welcome"], reply_markup=kb)


@dp.message(Command("paysupport"))
async def on_paysupport(m: Message):
    await m.answer(TEXT[lang_of(m.from_user.language_code)]["support"].format(s=config.SUPPORT or "—"))


@dp.pre_checkout_query()
async def on_pre_checkout(q: PreCheckoutQuery):
    ok = q.invoice_payload.split(":")[0] in ("pack", "vip") and db.get_user(q.from_user.id) is not None
    await q.answer(ok=ok, error_message=None if ok else "Invalid purchase")


@dp.message(F.successful_payment)
async def on_paid(m: Message):
    sp = m.successful_payment
    if economy.record_payment(sp.telegram_payment_charge_id, m.from_user.id, sp.invoice_payload, sp.total_amount):
        economy.apply_payload(m.from_user.id, sp.invoice_payload)
        from .game import hub
        await hub.push_me(m.from_user.id)
    await m.answer(TEXT[lang_of(m.from_user.language_code)]["paid"])


async def create_invoice(uid: int, kind: str, ident: str, lang: str) -> str | None:
    if not bot:
        return None
    titles = {
        "uz": ("Yurakchalar", "{n} ❤️ yurakcha", "VIP maqom", "{d} kunlik VIP"),
        "ru": ("Сердечки", "{n} ❤️ сердечек", "VIP статус", "VIP на {d} дней"),
        "en": ("Hearts", "{n} ❤️ hearts", "VIP status", "VIP for {d} days"),
    }[lang if lang in ("uz", "ru", "en") else "en"]
    if kind == "pack" and ident in PACKS:
        stars, hearts, _ = PACKS[ident]
        title, desc = titles[0], titles[1].format(n=hearts)
    elif kind == "vip":
        stars, title, desc = VIP_STARS, titles[2], titles[3].format(d=VIP_DAYS)
    else:
        return None
    return await bot.create_invoice_link(
        title=title, description=desc, payload=f"{kind}:{ident}", provider_token="",
        currency="XTR", prices=[LabeledPrice(label=title, amount=stars)],
    )


async def run_bot() -> None:
    global bot_username
    me = await bot.get_me()
    bot_username = me.username or ""
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Play 🎮", web_app=WebAppInfo(url=config.WEBAPP_URL)))
    except Exception as e:
        print("menu button:", e)
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, handle_signals=False)


async def is_subscribed(uid: int) -> bool:
    if not config.CHANNEL:
        return config.DEV_MODE
    if not bot:
        return False
    try:
        mem = await bot.get_chat_member(config.CHANNEL, uid)
        return mem.status in ("member", "administrator", "creator")
    except Exception:
        return False


# ---------------------------------------------------------------- notifications
# Compliment teasers: (headline, body, footer, button). {e} avatar emoji, {name}, {a} ru feminine ending, {t} first letters
TEASERS = {
    "ru": [
        ("Вау, это для тебя!", "{e} {name} долго разглядывал{a} твое фото и выдал{a}: {t}...", "Кто-то впечатлён твоим фото!", "Открой комплимент 👀"),
        ("Чрезвычайная ситуация – ты в центре внимания! 🚨", "Смотря на твое фото {e} {name} со слезами на глазах, сказал{a}: {t}...", "Твоё фото вызвало эмоциональный взрыв.", "Получить комплимент 💌"),
    ],
    "uz": [
        ("Voy, bu sen uchun!", "{e} {name} rasmingga uzoq tikilib turdi va dedi: {t}...", "Kimdir rasmingdan hayratda!", "Kompliment ochish 👀"),
        ("Favqulodda holat – hamma e'tibori sendda! 🚨", "{e} {name} rasmingga qarab, ko'zlarida yosh bilan dedi: {t}...", "Rasming kuchli his-tuyg'u uyg'otdi.", "Komplimentni olish 💌"),
    ],
    "en": [
        ("Wow, this is for you!", "{e} {name} stared at your photo for a long time and said: {t}...", "Someone is impressed by your photo!", "Open the compliment 👀"),
        ("Emergency – all eyes are on you! 🚨", "{e} {name} looked at your photo with tears in their eyes and said: {t}...", "Your photo caused an emotional explosion.", "Get the compliment 💌"),
    ],
}
REMINDER = {
    "ru": "Скорее заберите ежедневный бонус ❤️ сердечек!",
    "uz": "Kunlik bonus ❤️ yurakchalarni tezroq oling!",
    "en": "Hurry, grab your daily bonus ❤️ hearts!",
}
COMMUNITY = {"ru": "Сообщество", "uz": "Jamoa", "en": "Community"}


def _play_kb(lang: str, query: str = "", community: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=TEXT[lang]["play"], web_app=WebAppInfo(url=config.WEBAPP_URL + query))]]
    if community and config.CHANNEL:
        rows.append([InlineKeyboardButton(text=COMMUNITY[lang], url="https://t.me/" + config.CHANNEL.lstrip("@"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _safe_send(uid: int, text: str, kb: InlineKeyboardMarkup) -> bool:
    """Send a bot message; if the user blocked the bot, stop notifying them."""
    try:
        await bot.send_message(uid, text, reply_markup=kb)
        return True
    except TelegramForbiddenError:
        db.x("UPDATE users SET notify=0 WHERE id=?", uid)
    except Exception as e:
        print("send failed", uid, e)
    return False


async def notify_compliment(target, sender, text: str, cid: int) -> bool:
    if not bot or not target["bot_started"] or not target["notify"]:
        return False
    lang = target["lang"] if target["lang"] in TEASERS else "en"
    head, body, foot, btn = random.choice(TEASERS[lang])
    fem = sender["gender"] == "f"
    body = body.format(e="👩" if fem else "👨", name=sender["name"], a="а" if fem else "", t=text.strip()[:2])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn, web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/?c={cid}"))]])
    return await _safe_send(target["id"], f"{head}\n\n{body}\n\n{foot}", kb)


async def reminder_loop() -> None:
    """Once a day (after REMINDER_HOUR) nudge players who haven't claimed their daily bonus."""
    while True:
        await asyncio.sleep(600)
        try:
            lt = time.localtime()
            if not config.REMINDER_HOUR <= lt.tm_hour < 22:
                continue
            today, idle = db.today(), int(time.time()) - 6 * 3600
            rows = db.q("""SELECT id, lang FROM users WHERE bot_started=1 AND notify=1 AND last_daily != ?
                           AND last_reminder != ? AND last_seen < ? LIMIT 40""", today, today, idle)
            for r in rows:
                db.x("UPDATE users SET last_reminder=? WHERE id=?", today, r["id"])
                lang = r["lang"] if r["lang"] in REMINDER else "en"
                await _safe_send(r["id"], REMINDER[lang], _play_kb(lang, community=True))
                await asyncio.sleep(0.06)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print("reminder loop:", e)


@dp.message(Command("broadcast"))
async def on_broadcast(m: Message, command: CommandObject):
    from . import moderation
    if moderation.rank(m.from_user.id) < moderation.RANK["admin"]:
        return
    text = (command.args or "").strip()
    if not text:
        return await m.answer("Usage: /broadcast <text>")
    rows = db.q("SELECT id, lang FROM users WHERE bot_started=1 AND notify=1")
    ok = 0
    for r in rows:
        lang = r["lang"] if r["lang"] in TEXT else "en"
        ok += await _safe_send(r["id"], text, _play_kb(lang, community=True))
        await asyncio.sleep(0.05)
    await m.answer(f"Sent {ok}/{len(rows)}")


from . import botadmin  # noqa: E402,F401  (registers the staff commands on dp)

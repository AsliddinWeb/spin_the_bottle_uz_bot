# Spin the Bottle — Telegram Mini App

Ko'p o'yinchili "shisha aylantirish" o'yini. Python (FastAPI + aiogram), frontend — oddiy HTML/CSS/JS.
Tillar: O'zbekcha, Русский, English.

## Imkoniyatlar
- 12 o'rindiqli stollar (99 ta), tasodifiy stol / oxirgi stollar
- Real-time (WebSocket): navbat, shisha aylanishi, "o'pishadimi?" → "javoban o'padimi?" so'rovlari, taymerlar
- Stol chati, "Tarjima" (Google Translate orqali)
- 40+ sovg'a (pomidor, baqa kabi "yomon" sovg'alar, VIP sovg'alar, 🎲 tasodifiy sovg'a)
- Musiqa: 📼/🎧 sovg'asi + YouTube havolasi → stoldagi hamma uchun yangraydi (navbat bilan)
- Yurakchalar iqtisodiyoti: kunlik bonus (5 kunlik seriya), Omad g'ildiragi, bepul vazifalar (do'st taklifi, kanalga obuna, komplimentlar)
- Telegram Stars bilan to'lov: yurakchalar paketlari va VIP
- Do'kon: shisha dizaynlari, avatar ramkalari, boosterlar (magnit, ikkilangan o'pish, qalqon)
- Yutuqlar, reytinglar (o'pishlar / sovg'alar / yurakchalar)
- AFK himoyasi, initData imzosini tekshirish, to'lovlar uchun idempotentlik

## Ishga tushirish

1. @BotFather'da bot yarating, tokenni oling. `/newapp` yoki Menu Button kerak emas — bot o'zi menyu tugmasini o'rnatadi.
2. `.env.example` ni `.env` ga nusxalang va to'ldiring (`BOT_TOKEN`, `WEBAPP_URL`).
3. Mini App uchun **HTTPS** kerak. Lokal sinov uchun:
   ```bash
   cloudflared tunnel --url http://localhost:8000   # yoki: ngrok http 8000
   ```
   Chiqqan `https://...` manzilni `.env` dagi `WEBAPP_URL` ga yozing.
4. Serverni ishga tushiring:
   ```bash
   ./run.sh
   ```
5. Botga `/start` yuboring → **O'YNASH** tugmasi.

### Brauzerda sinash (Telegramsiz)
`BOT_TOKEN` bo'sh bo'lsa server DEV rejimida ishlaydi: `http://localhost:8000/?dev=1`, boshqa o'yinchi uchun `?dev=2` (boshqa tabda).
Bu rejimda "to'lov" yurakchalarni bepul beradi. Productionda `DEV_MODE=0` bo'lishi shart (token bor bo'lsa avtomatik o'chiq).

## Bot xabarlari (bildirishnomalar)
- **Komplimentlar.** Profildagi ko'k pochta tugmasi kompliment yuboradi (1 ❤). Qabul qiluvchi tarmoqda bo'lmasa, bot unga teaser xabar yuboradi ("Открой комплимент 👀"), tugma Mini App'ni ochadi, o'qigan o'yinchi +1 ❤ oladi.
- **Kunlik bonus eslatmasi.** Bonusni olmagan va botga `/start` bosgan o'yinchilarga kuniga bir marta (`REMINDER_HOUR` dan keyin) eslatma ketadi.
- **E'lon.** `ADMIN_IDS` dagi akkaunt botga `/broadcast matn` yozsa, hammaga "O'YNASH" tugmasi bilan yuboriladi.
- O'yinchi Sozlamalar → Bildirishnomalar orqali o'chirib qo'yishi mumkin; botni bloklagan o'yinchiga boshqa yuborilmaydi.
- Faqat botga kamida bir marta `/start` bosgan o'yinchilarga xabar yuborish mumkin (Telegram qoidasi).

## Telegram Stars
Hech qanday provayder kerak emas. Bot `createInvoiceLink` (valyuta `XTR`) orqali hisob yaratadi, to'lovdan keyin `successful_payment` yurakchalarni beradi.
Telegram qoidasiga ko'ra `/paysupport` buyrug'i bor — `.env` da `SUPPORT` ni to'ldiring. Narxlar: `app/catalog.py` (`PACKS`, `VIP_STARS`).

## Sozlash
Barcha o'yin kontenti `app/catalog.py` da: sovg'alar, narxlar, g'ildirak sektorlari va ehtimollari, yutuqlar, kunlik bonus.
Vaqtlar (`SPIN_T`, `DEC_T`) — `app/game.py`.

## Tuzilma
```
app/main.py     REST API + WebSocket endpoint
app/game.py     Stol, navbat sikli, chat, sovg'alar, musiqa
app/economy.py  Bonus, g'ildirak, do'kon, to'lovlarni qo'llash
app/bot.py      /start, referal, Stars to'lovlari
app/db.py       SQLite (spin.db)
static/         Mini App (index.html, app.js, style.css, i18n.js)
```

## Eslatmalar
- Grafika original emas: emoji + CSS/SVG. O'z rasmlaringizni `static/` ga qo'yib almashtirishingiz mumkin.
- Bitta jarayon (bir nechta worker emas) — stollar xotirada saqlanadi. Katta yuklama uchun Redis kerak bo'ladi.
- `CHANNEL` bo'sh bo'lsa, obuna vazifasi faqat DEV rejimida ishlaydi.

## Profil rasmi
O'yinchi rasmni Sozlamalar → Profil sozlamalari orqali yuklaydi. Server uni 480×480 JPEG qilib `uploads/` papkasiga saqlaydi (EXIF o'chadi). `uploads/` ni zaxiralashni unutmang. Telegram rasmi faqat o'zi yuklamagan o'yinchilarda yangilanadi.

## Moderatsiya (bot ichida)
Rollar: **owner** (`.env` dagi `ADMIN_IDS`) > **admin** > **mod**. Faqat owner admin/mod tayinlaydi: `/role <id|@nom> admin|mod|none`.
Oddiy o'yinchi buyruqlarga javob olmaydi (ular borligini bilmaydi).

| Buyruq | Kim | Nima qiladi |
|---|---|---|
| `/admin` | mod+ | o'z rolingiz uchun yordam |
| `/user <id\|@nom>` | mod+ | kartochka + tugmalar (warn, mute, kick, ban...) |
| `/reports` | mod+ | shikoyatlarni birma-bir ko'rib chiqish (tugmalar bilan) |
| `/warn id matn` | mod+ | ogohlantirish |
| `/mute id 30m\|2h\|1d\|perm sabab`, `/unmute id` | mod+ | chatga yozishni cheklash |
| `/kick id` | mod+ | stoldan chiqarish |
| `/rename id ism`, `/unphoto id` | mod+ | noo'rin ism/rasmni tozalash |
| `/audit [id]`, `/stats` | mod+ | jurnal va statistika |
| `/ban id 7d\|perm sabab`, `/unban id` | admin+ | to'liq blok (o'yinga kira olmaydi) |
| `/give id hearts\|smiles\|chances\|vip son [sabab]` | admin+ | qo'lda berish; manfiy son ayiradi; limit yo'q |
| `/broadcast matn` | admin+ | hammaga e'lon |

Yuqori yoki teng darajadagi odamga jazo berib bo'lmaydi. 24 soatda 5 ta turli o'yinchi shikoyat qilsa, o'yinchi 1 soatga avtomatik mute bo'ladi va staffga xabar boradi.

## Chat filtri
Har bir chat xabari, kompliment va profil ismi tekshiriladi: taqiqlangan so'zlar (uz/ru/en), havola va `@nom`, telefon raqam, bir xil xabarni takrorlash (25 soniyada 3 marta). Buzuq xabar yetkazilmaydi, yuboruvchiga sabab aytiladi.
10 daqiqada 3 marta buzsa 10 daqiqaga avtomatik mute (staff mute olmaydi). So'zlar bazada (`badwords`), bot orqali tahrirlanadi: `/words`, `/addword so'z` yoki `/addword o'zak*`, `/delword so'z`; filtr to'sgan oxirgi xabarlar: `/filtered`.
Cheklov: bu birinchi himoya, mukammal sensura emas (yangi yozilish usullari uchun so'z qo'shib boring). Test: `tests/qa_chatfilter.py`.

## Zaxira nusxa
Server o'zi har 24 soatda `backups/spinbot-YYYYMMDD-HHMMSS.tar.gz` yaratadi (ichida `spin.db` snapshoti + `uploads/`), oxirgi 14 tasini saqlaydi. Snapshot SQLite'ning online backup usuli bilan olinadi, shuning uchun o'yin ishlab turganda ham xavfsiz, va arxivlashdan oldin yaxlitlik tekshiriladi.
- Hozir olish: botda `/backup` (faqat owner), ro'yxat: `/backups`.
- Tiklash (serverni to'xtating!): `.venv/bin/python restore_backup.py` (ro'yxat), `.venv/bin/python restore_backup.py latest`. Joriy baza va rasmlar `*.before-restore-...` nomi bilan saqlanadi.
- Sozlash (`.env`): `BACKUP_DIR`, `BACKUP_KEEP` (14), `BACKUP_EVERY_HOURS` (24).
- **Muhim:** zaxira shu kompyuterning o'zida turadi, kompyuter yoki disk buzilsa u ham yo'qoladi. `backups/` papkasini vaqti-vaqti bilan boshqa joyga (tashqi disk, bulut) nusxalang. Arxivda o'yinchilar ma'lumoti bor (ismlar, ID, rasmlar), shuning uchun uni boshqalarga bermang. `.env` (bot tokeni) arxivga kirmaydi.

## Xarid: admin orqali (Stars o'rniga)
`.env` da `PAYMENTS=manual` (standart). O'yinchi do'kondan paket tanlaydi → **buyurtma** yaratiladi (hech narsa o'zi qo'shilmaydi) → admin/ownerga botda tugmali xabar keladi → to'lovni admin o'zi qabul qiladi (karta/naqd) → **✅ Tasdiqlash** bosilsa yurakchalar (yoki VIP) avtomatik qo'shiladi va o'yinchiga bot xabar yuboradi. Moderatorlar buyurtma ko'rmaydi.
- Bot: `/orders` (kutilayotganlar, tugmalar bilan), `/confirm id`, `/reject id [sabab]`. Hammasi `audit` da.
- Himoya: bir buyurtma ikki marta qo'shilmaydi; bir o'yinchida ko'pi bilan 3 ta kutilayotgan buyurtma; miqdor buyurtma paytida qotiriladi.
- `.env` sozlamalari: `SUPPORT=@admin_nomi` (o'yinchi shu yerga yozadi), `PAY_INFO=Karta ... (to'lov ko'rsatmasi)`, `PRICES=p50=5000,p250=20000,p500=38000,p1000=70000,p2500=160000,p5000=300000,vip=60000`, `PRICE_CUR=so'm`. Narx kiritilmasa tugmada faqat "Buyurtma" ko'rinadi va narx admin bilan kelishiladi.
- Telegram Stars kodi saqlangan: `PAYMENTS=stars`.
- Test: `tests/qa_orders.py`.


## Web admin panel (`/admin`)
Staff (mod and up) send `/panel` to the bot and tap the button: a Mini App page with the dashboard (live counters, 14-day charts),
players (search, filters, full card with sanctions / balance / role actions), reports queue, manual orders (admin+), live tables,
uploaded photos, chat filter words, audit log, broadcast (admin+) and backups (owner). It uses the same `moderation` / `orders`
functions as the bot commands, so rank rules and the audit log are identical; the bot commands keep working.
Access = valid Telegram initData of a staff account (403 otherwise). In DEV_MODE only: `/admin?dev=<id>`.
Test: `tests/qa_admin.py` (67 checks, dev server on 8001 with `ADMIN_IDS=1`).

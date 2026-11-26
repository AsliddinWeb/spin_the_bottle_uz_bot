# Grafikani originalga yaqinlashtirish rejasi

Sabab (2026-11-26): buyurtmachi grafika originalga o'xshamayotganidan norozi. Shart: ish **kirishdan boshlanadi**, loadergacha hammasi bir xil bo'lishi kerak.

Cheklov: joylashuv, o'lcham, rang, harakat originalga moslanadi; rasmlar o'zimizniki bo'ladi. Originalning rasm fayllari, logo harflari va nomi ko'chirilmaydi.

## Originalning kirish ketma-ketligi (kuzatilgan, web view 362×585)
1. Telegramning qorong'i kutish oynasi: botning o'z belgisi, tepada ko'k yuklanish chizig'i (BotFather sozlamasi).
2. Tekis yashil ekran (~#7a9758), naqshsiz, juda qisqa.
3. Yashil fon + naqsh (lab, sovg'a qutisi, shisha, toj, nota, yurak, halqa, nuqta) + oq tabletka progress bar: eni ~24%→76%, markazi balandlikning ~50% ida, ichida och yashil to'ldirish.
4. Sarlavha ekrani (bar yo'qoladi): markazi yoriqroq gradient (markaz ~#8aac5c, chet ~#7c9759); sarlavha 2 qator + o'rtada kichik "и", eni ~69% (15%→84%), markazi ~49%; tik (qiyshaymagan), qalin yumaloq shrift; rang o'rtada sariq, chetda to'q sariq; tepasida ingichka och qirra; yumshoq zaytun soya, to'q kontur yo'q.
5. Stol; ustida avtomatik oyna (kuzatuvda "Ежедневный бонус", qayta yuklaganda "Изменения в VIP-статусе").

Qo'shimcha: 🔄 tugmasidagi raqam sanab kamayadi (7→6→5→2) — sanoq ekani tasdiqlandi.

## Bizdagi farqlar (362×585 da o'lchandi)
| Qism | Original | Bizda |
|---|---|---|
| Naqsh | bor | ko'rinmaydi (style.css dagi keyingi qoida uni bosib ketgan) |
| Fon | toza yashil gradient | jigarrang taxta shovqini aralashgan |
| Bar balandligi | ~50% | 46% |
| Bar eni | 24%→76% | 24%→76% (mos) |
| Sarlavha | tik, yirik, gradient, yumshoq soya | qiya, ingichkaroq, to'q kontur, ~46% balandlikda |

## 1-bosqich: kirish va loader
- [x] Fon: toza yashil, sarlavha ekranida markazi yoriqroq (jigarrang shovqin olib tashlandi; loader uslublari bitta blokka yig'ildi)
- [x] Naqsh: o'zimiz chizgan `static/boot-pattern.svg`
- [x] Progress bar: ekran o'rtasida, soyasiz
- [x] Sarlavha: tayyor rasm `static/title-{uz,ru,en}.webp` (`python3 tools/make_titles.py` chizadi). Jonli SVG matn Telegram (WebKit) da ikki chetidan kesilgan edi, 2026-11-26 da egasining Telegram'ida ko'rildi
- [x] Sarlavha shrifti: Lobster (SIL OFL), `static/fonts/lobster-*.woff2`
- [ ] Bosqichlar davomiyligi: ekran yozuvi bilan solishtirilmagan
- [x] Telegram kutish belgisi: `static/tg-loading.svg` — egasi yuklaydi: @BotFather /mybots → bot → Bot Settings → Configure Mini App → Enable Mini App (yuklanish ekrani belgisi va ranglari). BotFather faylni qabul qilishi tekshirilmagan
- [x] /start rasmi: o'z chizmamiz `static/banner.svg` → `static/banner.png` (Chrome headless, 1000×560)

Tayyor mezoni: bir xil o'lchamdagi yonma-yon skrinshotlar va buyurtmachi roziligi.

## Keyingi bosqichlar (har biri oldingisi tasdiqlangach)
2. Stol ekrani: taxta, naqsh, shisha, avatarlar, tugmalar
3. Avtomatik oynalar: kunlik bonus va boshqa popup'lar
4. Chat va pleyer
5. Sovg'alar va ikonlar (eng katta qism)
6. Profil, do'kon, reyting va boshqa oynalar
7. Animatsiyalar

## Yo'l-yo'lakay kuzatilgan (keyingi bosqichlar uchun)
Original bot chatga xabarnomalar yuboradi: "У тебя новый ухажёр" va kunlik "Скорее заберите ежедневный бонус ❤️ сердечек!", ostida tugmalar: ИГРАТЬ В MAX · ИГРАТЬ · Сообщество.

## Originaldan 2026-11-26 da olingan (2-bosqich uchun)
- Stol ustida TOP belgisi, vazifa tugmalari va kunlik sovg'a belgisi yo'q.
- Yurakcha oynasi yuqori qatori: VIP daraja · do'st uchun ❤20 · komplimentlar ❤10 ("Узнать"); pastda 6 ta paket, hammasi aylantirmasdan sig'adi.
- Yangi o'yinchi kirganda chatda "… впервые в игре! Поприветствуй и обрадуй подарочком!" kartasi va sovg'a tugmasi chiqadi.

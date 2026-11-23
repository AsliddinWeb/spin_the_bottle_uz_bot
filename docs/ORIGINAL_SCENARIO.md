# Original o'yin ssenariysi (Spin the Bottle, @spinthe_bot) va bizdagi holat

Manba: originalni Telegram'da o'zim ochib ko'rdim (2026-11-22; faqat ko'rish, hech narsa sotib olinmadi/yuborilmadi), oldingi ko'rishlar (`ORIGINAL_SPEC.md`) va foydalanuvchi skrinshotlari.
Belgilar: ✅ bizda bor · ⚠️ qisman · ❌ yo'q

## 1. O'yinchi yo'li (original)

1. **Kirish:** `/start` → ИГРАТЬ → yashil ekran → kunlik bonus → stol (300 stol, 12 o'rin).
2. **Asosiy sikl:** navbat bilan butilka aylantiriladi → juft tanlanadi → ikkalasi "Поцеловать/Отказаться" → o'pish: ❤ + 💋 hisobi. ✅
3. **Ijtimoiy qatlam:** chat, sovg'alar (bosh/qo'l joylari), imo-ishoralar, xushtorlik ("Ухаживать"), kompliment vazifasi, musiqa/video. ✅
4. **Maqsadlar (progressiya):**
   - **Reytinglar** (💋 🎵 ❤ 💞 😊, davrlar bilan). ✅
   - **Yutuqlar:** 333 yulduz (≈111 mavzuli medal × 3 daraja), har birining o'z rasmi va shartli, masalan "Хит": musiqa chalinayotganda 50 ta sovg'a olish. ⚠️ (bizda 25 ta mavzuli medal = 75 yulduz, qo'shimcha 89 ta oddiy yutuq)
   - **Ligalar (🏆 tugmasi "Лиги"):** haftalik musobaqa, olingan o'pish = liga balli, kirish o'pishlari uchun limit, jadval. ✅ (bu safar qilindi)
   - **Mavsumiy o'tkazma (Сезонный пропуск):** boosterlar shu yerdan yig'iladi. ❌
5. **Boosterlar (☰ → Бустеры):**
   - *Tanlov boosterlari* — tanlovdan keyin stol markazida: **Страстный поцелуй** va **Пощёчина**, har biri +1 liga balli (limit doirasida). ✅
   - *Liga boosterlari* — liga jadvalidan ishlatiladi: **×2 ball** (5 daqiqa, havo o'pishidan tashqari), **limitni +10 kengaytirish**, **+5 ball** (limitni hisobga olmaydi). ✅
6. **Daromad:** ❤ paketlari (Stars), VIP, g'ildirak, kunlik bonus, do'st taklifi (❤20/❤50 Premium), obuna. ✅ (to'lov qo'lda/admin orqali)
7. **Qaytarish:** kunlik bonus, bot eslatmalari, komplimentlar teaseri, aksiyalar. ✅

## 2. Musiqa va video (originalda)
- Musiqa to'xtaganda o'ng chetda **2 ta tugma**: video (kinolenta + nota) va musiqa (disk + nota). ✅ (bizda ham 2 ta: 🎬 va 🎧)
- Musiqa oynasi: 🔥 mashhur · ⭐ saralangan · 👤 **Telegram pleylist** (profildagi musiqa) · 🕒 tarix, tepada qidiruv; qatorlar (nom, ijrochi, davomiylik). ✅ (👤 va ⭐ tablari bor)
- Ijro paytida tugmalar yo'qolib, o'rnida pleyer: musiqada magnitofon, **videoda video o'sha pleyer ichida** ko'rinadi. ⚠️ (bizda video alohida kartada)
- Pleyerga bosilsa almashtirish oynasi ochiladi. ✅

## 3. Bu safar qo'shilgan (ligalar va boosterlar)
| Narsa | Qanday ishlaydi |
|-------|-----------------|
| Liga ballari | Har bir olingan o'pish = 1 ball (juft kuniga 3 o'pishgacha sanaladi). Haftalik limit 30 ball (`config.LEAGUE_LIMIT`). |
| Liga jadvali | 🏆 tugmasi: o'rin, ball/limit, ×2 qolgan vaqt, top-20, liga boosterlari tugmalari. |
| Hafta oxiri | Top-3 booster sovrini oladi (`LEAGUE_PRIZES`); har hafta bir marta (idempotent). |
| Tanlov boosterlari | O'yinchi qaror qilgach 7 soniya "🔥 / 🖐" tugmalari chiqadi; bosilsa stol markazida effekt + ovoz, hammaga ko'rinadi, +1 liga balli; bir aylanishda bir marta. |
| Boosterlar oynasi | Original guruhlari: Tanlov (2) · Liga (3) · Boshqa (magnit, ×2 yurak, qalqon — bizning qo'shimcha). Narxlar ❤ (placeholder). |

## 4. Hali qolgan (originaldan farq)
1. **Mavsumiy o'tkazma** (boosterlar va sovrinlar yo'li) — original tafsiloti ko'rilmagan.
2. **333 yutuq:** original ≈111 medal. Bizda 25 ta mavzuli medal (`app/medals.py`: Hit, Kofeman, Romantik, DJ, Bombardimonchi, Sovchi ...), qolganlarini shu jadvalga qo'shish oson (bitta qator + 2 matn).
3. **"Воздушный поцелуй"** (ligada hisobga olinmaydigan o'pish) — qoidasi aniq emas.
4. **Videoni pleyer ichida ko'rsatish** (hozir alohida suzuvchi karta).
5. Liga bo'limlari (original jadvalda "Соревнование Лиг" ishtirokchilari — bir nechta liga/divizion bo'lishi mumkin; faqat bitta umumiy jadval qilindi).
6. Ramka/medal/booster rasmlari original 3D, bizniki o'z vektor rasmlari (nusxalanmaydi).

## 5. Tur sikli: jonli kuzatuv (2026-11-23, originalda stol 193, ~12 o'yinchi)
Kadrlar 1 soniya oralig'ida olindi (faqat kuzatish, qaror tugmalari bosilmadi).

| Bosqich | Originalda ko'rilgani | Bizda (oldin → hozir) |
|---------|----------------------|------------------------|
| Spin kutish | Spinner uchun "Крути бутылочку!" (o'q bilan), boshqalar uchun "Крутит бутылочку" + o'q spinner avatariga. Aylantirmasa shisha o'zi aylanadi (~10 s ichida) | 20 s kutib turni o'tkazardi → **10 s, keyin o'zi aylanadi** (3 marta ketma-ket bo'lsa AFK chiqarish saqlandi) |
| Aylanish | ~5 s, sekin to'xtaydi | 5 s ✅ |
| Qaror sanog'i | Juft markazga o'tadi, markazda raqam **9 dan** kamayadi; spinner uchun "Твой выбор" + [Отказаться][Поцеловать], boshqalarga "Поцелуются или нет?" | 12 s ✅ yozuvlar, **sanoq bitta: 10 s** |
| Ikkinchi javob | Spinner "ha" desa yashil o'q chiqadi, "Поцелует ли в ответ?", **sanoq to'xtamaydi va qayta boshlanmaydi** (9, 8, 7 → 6, 5, 4) | alohida 12 s → **umumiy sanoq (kamida 2 s qoladi)** |
| Rad / vaqt tugashi | Natija yozuvi kutilmaydi, keyingi tur ~1 s ichida boshlanadi | 2.4 s natija → **1.2 s**, tur oralig'i 1.5 → **1.0 s** |
| O'pish | Ikkala avatarga "1" nishon ortadi, shisha darhol yana aylanadi | 3.6 s (videodan o'lchangan) ✅ |
| Spinner avatari | Kutayotgan spinner ostida o'q va yozuv | ✅ |
| Tasodifiy | Stol to'la (12), o'yinchilar kirib-chiqib turadi, o'tirgan o'rin bo'sh qolsa keyingi o'tirganlar ketma-ket spin qiladi | ✅ |

Ko'rilmaganlar: spin kutishning aniq vaqti (taxminan 8–10 s), natija matnlari rad etilganda, kutish holatidagi ("Ждем игроков…") qo'shimcha matnlar.
Test: `tests/qa_cycle.py` (5).

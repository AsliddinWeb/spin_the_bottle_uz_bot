# Original o'yin ssenariysi (Spin the Bottle, @spinthe_bot) va bizdagi holat

Manba: originalni Telegram'da o'zim ochib ko'rdim (2026-11-22; faqat ko'rish, hech narsa sotib olinmadi/yuborilmadi), oldingi ko'rishlar (`ORIGINAL_SPEC.md`) va foydalanuvchi skrinshotlari.
Belgilar: ✅ bizda bor · ⚠️ qisman · ❌ yo'q

## 1. O'yinchi yo'li (original)

1. **Kirish:** `/start` → ИГРАТЬ → yashil ekran → kunlik bonus → stol (300 stol, 12 o'rin).
2. **Asosiy sikl:** navbat bilan butilka aylantiriladi → juft tanlanadi → ikkalasi "Поцеловать/Отказаться" → o'pish: ❤ + 💋 hisobi. ✅
3. **Ijtimoiy qatlam:** chat, sovg'alar (bosh/qo'l joylari), imo-ishoralar, xushtorlik ("Ухаживать"), kompliment vazifasi, musiqa/video. ✅
4. **Maqsadlar (progressiya):**
   - **Reytinglar** (💋 🎵 ❤ 💞 😊, davrlar bilan). ✅
   - **Yutuqlar:** 333 yulduz (≈111 mavzuli medal × 3 daraja), har birining o'z rasmi va shartli, masalan "Хит": musiqa chalinayotganda 50 ta sovg'a olish. ⚠️ (bizda 89 ta oddiy sanoq yutuqlari)
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
2. **333 yutuq:** mavzuli medallar (rasm + maxsus shartlar). Bizda 89 ta sanoq yutug'i. Keyingi qadam: 20–30 mavzuli medal ("Хит", "Кофеман", "Романтик"...).
3. **"Воздушный поцелуй"** (ligada hisobga olinmaydigan o'pish) — qoidasi aniq emas.
4. **Videoni pleyer ichida ko'rsatish** (hozir alohida suzuvchi karta).
5. Liga bo'limlari (original jadvalda "Соревнование Лиг" ishtirokchilari — bir nechta liga/divizion bo'lishi mumkin; faqat bitta umumiy jadval qilindi).
6. Ramka/medal/booster rasmlari original 3D, bizniki o'z vektor rasmlari (nusxalanmaydi).

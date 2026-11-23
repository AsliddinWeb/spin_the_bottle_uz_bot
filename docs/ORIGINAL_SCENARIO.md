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
| Spin kutish | Spinner uchun "Крути бутылочку!" (o'q bilan), boshqalar uchun "Крутит бутылочку" + o'q spinner avatariga. **Aylantirmasa nima bo'lishi — TASDIQLANMAGAN** (kuzatuv paytida foydalanuvchi o'zi bosgan bo'lishi mumkin) | 20 s kutib turni o'tkazadi (3 marta ketma-ket bo'lsa AFK chiqarish) — **eski holat qaytarildi**, chunki avto-aylanish tasdiqlanmadi |
| Aylanish | ~5 s, sekin to'xtaydi | 5 s ✅ |
| Qaror sanog'i | Juft markazga o'tadi, markazda raqam **9 dan** kamayadi; spinner uchun "Твой выбор" + [Отказаться][Поцеловать], boshqalarga "Поцелуются или нет?" | 12 s ✅ yozuvlar, **sanoq bitta: 10 s** |
| Ikkinchi javob | Spinner "ha" desa yashil o'q chiqadi, "Поцелует ли в ответ?", **sanoq to'xtamaydi va qayta boshlanmaydi** (9, 8, 7 → 6, 5, 4) | alohida 12 s → **umumiy sanoq (kamida 2 s qoladi)** |
| Rad / vaqt tugashi | Natija yozuvi kutilmaydi, keyingi tur ~1 s ichida boshlanadi | 2.4 s natija → **1.2 s**, tur oralig'i 1.5 → **1.0 s** |
| O'pish | Ikkala avatarga "1" nishon ortadi, shisha darhol yana aylanadi | 3.6 s (videodan o'lchangan) ✅ |
| Spinner avatari | Kutayotgan spinner ostida o'q va yozuv | ✅ |
| Tasodifiy | Stol to'la (12), o'yinchilar kirib-chiqib turadi, o'tirgan o'rin bo'sh qolsa keyingi o'tirganlar ketma-ket spin qiladi | ✅ |

Ko'rilmaganlar: spin kutishning aniq vaqti (taxminan 8–10 s), natija matnlari rad etilganda, kutish holatidagi ("Ждем игроков…") qo'shimcha matnlar.
Test: `tests/qa_cycle.py` (5).

## 6. Chat va sovg'alar: o'zim o'ynab ko'rdim (2026-11-23, original, stol 193)
Foydalanuvchi ruxsati bilan: chatga xabar yozdim, sovg'a yubordim (qulupnay, ❤1; HUD ❤50 → ❤49 darhol).

**Chat**
- O'z xabarim boshqalarniki kabi: chapda kichik kvadrat avatar, oq pufakda **ko'k qalin ism** ("Asliddin:") + matn, tagida kulrang "Показать перевод". Yuborilgach maydon tozalanadi, chat pastga suriladi.
- O'pish qatori: matnsiz — [avatar] 💋 » [avatar] (qizil lab, yashil »). Sovg'a qatori: [yuboruvchi avatari] [sovg'a rasmi] » [oluvchi avatari], pufaksiz.
- Ism oldida daraja/rol belgilari (▲, rangli nishon), ismlar rangi rolga qarab (ko'k, qizil qalin, qora kursiv).

**Sovg'a paneli**
- Avatarga bosilgach panel darhol ochiladi: sarlavha "Отправить подарок <ism>", o'ngda yashil **+**, pastda yashil ✕. 7 ustun (kompyuterda).
- Tartib: video (❤9), musiqa (❤5), 4 ta toj (❤3), barg, gulchambar (❤2), savat, lab, tosh, qulupnay, pomidor, baqa (❤2), atirgul, konfet, o'rdak, begemot, pingvin, lola, guldasta, gul, kaktus, muzqaymoq, tort, sut, vino, viski (hammasi ❤1), keyin VIP (qulf).
- Yuborilganda: sovg'a **yuboruvchi avatari burchagidan** ~2 s ichida oluvchi avatari yoniga uchib boradi; HUD yurakchasi darhol kamayadi; panel ochiq qoladi (ketma-ket yuborish mumkin); chatga qator qo'shiladi.
- Qo'ngan sovg'a oluvchi avatarining chetida (ko'rilgan: pastki qatordagi o'rindiqda chap-o'rta, o'ng ustundagilarda o'ng-o'rta) turadi.

**Bizda o'zgargani:** sovg'alar paneli tartibi originalniki bilan bir xil qilindi (qo'shimcha sovg'alar — medal, shapka, tuxum, smuzi, pirog, bomba, shippak, chelak, VIP — oxirida); paneldagi 1-element (❤9) endi **video**, 2-si (❤5) **musiqa** oynasini ochadi.
**Ko'rilmagan:** o'z navbatimda aylantirish va o'pish javobi (navbat uzoq kelmadi), sovg'a qo'ngan joyning aniq qoidasi, jestlar paneli (😊 sarflanadi).

## 7. Ehtiyotkorlik eslatmasi (2026-11-23)
Kuzatuv paytida foydalanuvchi ham o'sha oynada bosgan ("men bosdim seni joyingdan"). Shuning uchun **mening akkauntimdagi** hodisalarga ishonmaslik kerak: o'pish nishonim oshishi, javob o'qlari, rasm ko'rish oynasining ochilishi, ehtimol avto-aylanish ham o'z-o'zidan bo'lmagan.
Ishonchli kuzatuvlar — boshqa o'yinchilar navbatlari: aylanish ~5 s, bitta umumiy sanoq (9 dan, ikkinchi javobda davom etadi), rad etilgach keyingi tur ~1 s.
Aniqlanishi kerak (foydalanuvchi sichqonchaga tegmagan holda): aylantirmagan o'yinchiga nima bo'ladi; javob bermagan o'yinchi uchun vaqt tugasa o'pish bo'ladimi; AFK uchun chiqarish bormi.

## 8. Toza kuzatuv (2026-11-23): foydalanuvchi sichqonchaga tegmadi
**Tasdiqlangan (ishonchli):**
- **Javob bermagan o'yinchi → o'pish BO'LMAYDI.** "Твой выбор" (tugmalar bilan) sanog'i 6 → 2 gacha tushdi, men bosmadim; o'pish nishonim o'zgarmadi, keyingi tur ≤4 s ichida "Крутит бутылочку" bilan boshlandi. Bizdagi mantiq (vaqt tugasa "yo'q") **to'g'ri**.
- **Yigit–qiz qoidasi originalniki:** faqat yigitlar o'tirgan stolda markazda **"Ждем девушек для начала игры"** chiqadi (bizda ham shu matn).
- Qo'l sovg'asi (ichimlik, qulupnay) avatarning **pastki o'ng burchagida** turadi (bir necha o'rindiqda ko'rildi) — bizdagi joylashuv bilan mos.
- Chatda xushtorlik qatori: [xushtor avatari] 🔒❤ "стал ухаживать ❤N" [oluvchi avatari].
- Jest avatar ustida emoji bo'lib ko'rinadi (✌️ ko'rildi) — bizda ham shunday.
- Stol almashtirish oynasida oxirgi stollar yigit/qiz soni bilan (masalan #168: 7+5), tugmada raqam (stoldagi o'yinchi soni deb taxmin).
- Spinner spin qilishi uchun odamlar odatda 7–12 s sarflaydi (kuzatuv); keyingi tur oldingisi tugagach 1–4 s ichida.

**Hali noma'lum:** spinner umuman aylantirmasa nima bo'lishi (o'tkazib yuboriladimi, o'zi aylanadimi, AFK uchun chiqarilishi). Bu faqat o'z navbatimda hech narsa qilmay kuzatib aniqlanadi; 10–12 o'yinchili stolda navbat 3–4 daqiqada keladi.

## 9. O'zimizning o'yinni o'zim o'ynab tekshirdim (2026-11-23)
Mahalliy server, 2 ta bot qiz + men (yigit), telefon o'lchami (390×760), brauzerda. Natijalar:

| Tekshiruv | Natija |
|-----------|--------|
| Kirish: yashil ekran → sarlavha → kunlik bonus (5 kun, "Получить") | ✅ original kabi |
| Tur: "Крути бутылочку!" (o'q + matn) | 🔧 tuzatildi: o'q endi shisha tomonga, matn ikki qatorda |
| Aylantirish → "Твой выбор" + [Отказаться][Поцеловать], juft markazda, raqam o'rtada | ✅ |
| Sanoq: spinner javob bergach 2-bosqichda davom etadi (10 → 8 → 8…) | ✅ |
| "Поцелует ли в ответ?" + yashil o'q; o'pishdan keyin ikkala o'q va lab izlari | ✅ |
| Sovg'a paneli: tartib (kasseta, quloqchin, 4 toj, barg, gulchambar, savat, lab, tosh, qulupnay, pomidor, baqa...) | ✅ |
| Sovg'a: HUD ❤ darhol kamaydi, avatarning pastki o'ng burchagiga qo'ndi, chatga [avatar] 🍓 » [avatar] | ✅ |
| Chat o'pish qatori [avatar] 💋 xN » [avatar] | ✅ |
| Stol almashtirish: "Случайный стол!" + oxirgi stollar (👦 N 👧 N) | ✅ |
| Yutuq oynasi | 🔧 tuzatildi: medal nomi qo'shildi, mukofot ❤1/2/3… (oldin ❤6) |
| Medal chat qatori: to'q sariq belgi + "Нома уровня N" | 🔧 katta qora ✔ o'rniga to'q sariq belgi |
| Fab tugmalari va panelning 1-2 elementi: kinolenta+nota (video), disk+nota (musiqa) | 🔧 original ikonlariga o'xshash chizildi |

**Tekshirilmagan / noaniq:** 🔄 tugmasidagi raqam (originalda ma'nosi noma'lum, bizda sanoq ko'rsatadi), o'pishdan keyingi "поцеловались!" matni (originalda bor-yo'qligi ko'rilmagan), ovozlar (quloq bilan eshitilmagan), idle spinner.

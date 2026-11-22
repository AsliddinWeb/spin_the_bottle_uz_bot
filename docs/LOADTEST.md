# Yuklama testi natijalari (2026-11-22)

Skript: `tests/load_test.py N SECS SERVER_PID` (+ `RATINGS_PER_S=<son>` og'ir REST so'rovlar uchun). N ta bot haqiqiy o'yinchidek o'ynaydi: tasodifiy stolga o'tiradi, navbatida aylantiradi, o'pish so'rovlariga javob beradi, har ~14 soniyada yozadi.
Server: `uvicorn app.main:app` (BITTA jarayon), SQLite, mahalliy Mac (zamonaviy yadro). Production serveri: 1 vCPU / 1,9 GB va boshqa loyihalar bilan bo'lishilgan, ya'ni bir yadro Mac'dagidan ~2-3 baravar sekin.

## 1) Faqat o'yin (kichik baza)
| O'yinchi | Server CPU (o'rt / max) | RAM | Chat javobi p50 / p99 | Uzilish |
|---|---|---|---|---|
| 100 | 3% / 5% | 213 MB | 2 ms / 3 ms | 0 |
| 300 | 6% / 10% | 231 MB | 2 ms / 4 ms | 0 |
| 600 | 9% / 12% | 259 MB | 1 ms / 3 ms | 0 |
| 1000 | 13% / 15% | 295 MB | 1 ms / 3 ms | 0 |

O'yin mantig'ining o'zi (stol tsikllari, WebSocket) yengil: 1 000 o'yinchi ~15% bitta yadro.

## 2) 1 000 000 ro'yxatdagi foydalanuvchi bazasi (SQLite, 91 MB) + og'ir REST
Topilgan to'siq: reytinglar va "tag task" so'rovlari butun users jadvalini skanerlardi (80-100 ms) va sinxron bo'lgani uchun BUTUN o'yin tsiklini to'xtatib turardi.

| 1 000 o'yinchi + og'ir so'rovlar | CPU o'rt | Chat p95 | `/api/me` p95 |
|---|---|---|---|
| 0 / s (oldin) | 12,5% | 2 ms | 3 ms |
| 5 / s (oldin) | 51% | 84 ms | 94 ms |
| 15 / s (oldin) | 98% (to'yingan) | 187 ms | 17 SONIYA |
| 5 / s (indeks + kesh keyin) | 23% | 18 ms | 3 ms |
| 15 / s (keyin) | 37% | 23 ms | 23 ms |
| 40 / s (keyin) | 80% | 30 ms | 39 ms |

Tuzatish: users jadvalida 6 ta indeks (kisses, gifts_received, hearts, tracks, last_seen, created), reyting top-20 ro'yxatini 20 soniya keshlash, tag task'da `ORDER BY RANDOM()` o'rniga tasodifiy id dan indeks bo'ylab yurish.
Bitta so'rov (1M bazada): reyting 85 → 14 ms, tag task 90 → 29 ms, admin statistika 200 → 66 ms, ism bo'yicha qidiruv 500 → 295 ms (LIKE '%..%', faqat admin).

## Hali o'lchanmagan / cheklovlar
- Telegram orqali haqiqiy tarmoq, TLS, nginx (kechikish qo'shiladi).
- Sovg'a, musiqa (YouTube qidiruv), rasm yuklash, g'ildirak, do'kon yuklamasi.
- Bir vaqtda ko'p yozuv (SQLite bitta yozuvchi): kiss/hediya/xarid oqimi baland bo'lganda.
- Bitta jarayon = bitta nosozlik nuqtasi va bitta yadro; 1 vCPU serverda natija Mac'dagidan ~2-3x yomon bo'ladi.

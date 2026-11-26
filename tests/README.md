# Tekshiruv skriptlari
Ajratilgan dev serverda ishga tushiriladi (haqiqiy bazaga tegmaydi):

    BOT_TOKEN= DEV_MODE=1 DB_PATH=/tmp/qa.db .venv/bin/uvicorn app.main:app --port 8001 &
    .venv/bin/python tests/qa_economy.py   # iqtisodiyot, do'kon, ijtimoiy mantiq (72 tekshiruv)
    .venv/bin/python tests/qa_game.py      # navbat, o'pish, chat, sovg'a, musiqa, jest, stol (41 tekshiruv)
    .venv/bin/python tests/qa_edge.py      # buzuq kiritish, WebSocket chidamliligi

Eslatma: qa_game.py da 4 ta "xato" ko'rinishi mumkin, bu yutuq mukofoti yurakchani qo'shgani uchun (test artefakti, xato emas).

    DB_PATH=/tmp/aq.db .venv/bin/python tests/qa_admin.py   # web admin panel API (67 tekshiruv; serverga ADMIN_IDS=1 PRICES=p500=38000 bering)

    ADMIN_IDS=204 KICK_DELAY=6 DB_PATH=/tmp/kq.db  (server)   DB_PATH=/tmp/kq.db .venv/bin/python tests/qa_kick.py   # Pinok va Qutqarish (21 tekshiruv; brauzer tabini yoping, aks holda u stolga qo'shiladi)
    DB_PATH=/tmp/rq.db .venv/bin/python tests/qa_ratings.py   # 5 reyting, davrlar, o'rinlar, DJ/hissiyot ochkolari (22 tekshiruv; server :8001)
    DB_PATH=/tmp/wq.db .venv/bin/python tests/qa_weekly.py   # haftalik top va juft kuniga 3 o'pish chegarasi (11 tekshiruv, serversiz)
    DB_PATH=/tmp/sq.db .venv/bin/python tests/qa_starter.py   # boshlang'ich vazifalar (9 tekshiruv)
    DB_PATH=/tmp/dq.db .venv/bin/python tests/qa_dtasks.py   # kunlik vazifalar (9 tekshiruv)
    DB_PATH=/tmp/kr.db .venv/bin/python tests/qa_ranks.py   # unvonlar (21 tekshiruv)
    ADMIN_IDS=1 DB_PATH=/tmp/ev.db (server)   .venv/bin/python tests/qa_events.py   # fasl tadbirlari (12 tekshiruv)
    DB_PATH=/tmp/md.db .venv/bin/python tests/qa_media.py   # musiqa/video alohida (8 tekshiruv; yangi baza kerak)
    ADMIN_IDS=204 KICK_DELAY=6 DB_PATH=/tmp/lg.db (server)   .venv/bin/python tests/qa_league.py   # ligalar va boosterlar (27 tekshiruv; modul qismi vaqtinchalik bazada)
    .venv/bin/python tests/qa_medals.py   # mavzuli medallar (18 tekshiruv; modul qismi vaqtinchalik bazada)
    .venv/bin/python tests/qa_referral.py   # taklif mukofoti (12 tekshiruv, modul)
    DB_PATH=/tmp/rl.db .venv/bin/python tests/qa_referral_live.py   # jonli (3 tekshiruv; yangi baza)
    .venv/bin/python tests/qa_cycle.py   # tur sikli: avto-aylanish va umumiy sanoq (5 tekshiruv; yangi baza)
    DB_PATH=/tmp/wn.db .venv/bin/python tests/qa_worn.py   # avatardagi sovg'alar: uch joy, chiqib qaytsa yo'qoladi (6 tekshiruv; server :8001)
    DB_PATH=/tmp/bl.db .venv/bin/python tests/qa_balance.py   # balans darhol yangilanishi, chatdagi rasmlar, ping (8 tekshiruv; server :8001)

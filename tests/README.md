# Tekshiruv skriptlari
Ajratilgan dev serverda ishga tushiriladi (haqiqiy bazaga tegmaydi):

    BOT_TOKEN= DEV_MODE=1 DB_PATH=/tmp/qa.db .venv/bin/uvicorn app.main:app --port 8001 &
    .venv/bin/python tests/qa_economy.py   # iqtisodiyot, do'kon, ijtimoiy mantiq (61 tekshiruv)
    .venv/bin/python tests/qa_game.py      # navbat, o'pish, chat, sovg'a, musiqa, jest, stol (41 tekshiruv)
    .venv/bin/python tests/qa_edge.py      # buzuq kiritish, WebSocket chidamliligi

Eslatma: qa_game.py da 4 ta "xato" ko'rinishi mumkin, bu yutuq mukofoti yurakchani qo'shgani uchun (test artefakti, xato emas).

    DB_PATH=/tmp/aq.db .venv/bin/python tests/qa_admin.py   # web admin panel API (67 tekshiruv; serverga ADMIN_IDS=1 PRICES=p500=38000 bering)

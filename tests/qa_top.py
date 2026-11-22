"""TOP badge for the top-10 kissers (direct):  DB_PATH=/tmp/tq.db .venv/bin/python tests/qa_top.py"""
import os, sys, time
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/tq.db")
from app import db, economy
res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
for u in range(1, 16): db.ensure_user(u, f"T{u}", lang="ru"); db.x("UPDATE users SET kisses=?, age=20 WHERE id=?", u * 10, u)   # 15 players, 15th has the most
db.x("UPDATE users SET kisses=0 WHERE id=1")
economy._TOP10 = (0.0, frozenset())
ids = economy.top10_ids()
chk("exactly ten, the ten with the most kisses", ids == frozenset(range(6, 16)), sorted(ids))
chk("card flag: top player yes, eleventh no, zero-kiss no", economy.user_card(15)["top"] is True and economy.user_card(5)["top"] is False and economy.user_card(1)["top"] is False)
chk("me payload has the flag", economy.me_payload(10)["top"] is True and economy.me_payload(2)["top"] is False)
db.x("UPDATE users SET kisses=1000 WHERE id=5")
chk("the set is cached (no rescan within the TTL)", economy.top10_ids() == ids)
economy._TOP10 = (time.time() - 999, frozenset())
chk("after the TTL a newcomer pushes the tenth player out", 5 in economy.top10_ids() and 6 not in economy.top10_ids(), sorted(economy.top10_ids()))
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

"""TOP ribbon for the top 10 of ANY rating (direct):  DB_PATH=/tmp/tq.db .venv/bin/python tests/qa_top.py"""
import os, sys, time
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/tq.db")
from app import db, economy
res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
def fresh(): economy._TOP10 = (0.0, frozenset()); economy._TOP.clear()
for u in range(1, 16): db.ensure_user(u, f"T{u}", lang="ru"); db.x("UPDATE users SET kisses=?, age=20 WHERE id=?", u * 10, u)   # 15 players, 15th has the most
db.x("UPDATE users SET kisses=0 WHERE id=1")
fresh(); ids = economy.top10_ids()
chk("kisses only: exactly the ten with the most", ids == frozenset(range(6, 16)), sorted(ids))
chk("card flag: top player yes, eleventh no, zero points no", economy.user_card(15)["top"] is True and economy.user_card(5)["top"] is False and economy.user_card(1)["top"] is False)
chk("me payload has the flag", economy.me_payload(10)["top"] is True and economy.me_payload(2)["top"] is False)
db.x("UPDATE users SET dj=50 WHERE id=1"); db.x("UPDATE users SET emo=5 WHERE id=2")
chk("the set is cached (no rescan within the TTL)", economy.top10_ids() == ids)
fresh(); ids = economy.top10_ids()
chk("a top DJ and a top emotional player get the ribbon too", {1, 2} <= ids and 3 not in ids, sorted(ids))
db.x("INSERT INTO courtship(target,suitor,price,ts) VALUES(3,4,9,0)"); fresh(); ids = economy.top10_ids()
chk("most expensive and most influential count as well", {3, 4} <= ids, sorted(ids))
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

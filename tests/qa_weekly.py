"""Weekly top awards + the per-pair daily cap (direct, no server needed):  DB_PATH=/tmp/wq.db .venv/bin/python tests/qa_weekly.py"""
import os, sys
from datetime import date, timedelta
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/wq.db")
from app import db, economy, weekly, config
res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
for u in range(1, 8): db.ensure_user(u, f"W{u}", lang="ru"); db.x("UPDATE users SET hearts=0, age=20 WHERE id=?", u)
today = date(2026, 11, 18)                      # a Wednesday
week, d0, d1 = weekly.last_week(today)
chk("previous week is Mon-Sun before this Monday", (week, d0, d1) == ("2026-11-09", "2026-11-09", "2026-11-15"), (week, d0, d1))
def put(uid, day, k): db.x("INSERT INTO stats_daily(day,uid,kisses) VALUES(?,?,?) ON CONFLICT(day,uid) DO UPDATE SET kisses=kisses+?", day, uid, k, k)
put(1, "2026-11-09", 30); put(1, "2026-11-15", 10)           # 40 over the week
put(2, "2026-11-12", 25)                                       # 25
put(3, "2026-11-10", 25)                                       # tie with 2 -> lower uid first
put(4, "2026-11-11", 4)                                        # below the minimum (5)
put(5, "2026-11-08", 500); put(6, "2026-11-16", 500)           # outside the week (Sunday before / Monday after)
a = weekly.award_last_week(today)
chk("three winners in order 1, 2, 3 (tie broken by id)", [x["uid"] for x in a] == [1, 2, 3] and [x["hearts"] for x in a] == config.WEEKLY_REWARDS, a)
chk("hearts paid", [db.get_user(u)["hearts"] for u in (1, 2, 3)] == config.WEEKLY_REWARDS)
chk("below-minimum and out-of-week players get nothing", all(db.get_user(u)["hearts"] == 0 for u in (4, 5, 6)))
chk("second run pays nobody (idempotent)", weekly.award_last_week(today) == [] and [db.get_user(u)["hearts"] for u in (1, 2, 3)] == config.WEEKLY_REWARDS)
chk("trophies on the profile card", economy.user_card(1)["trophies"] == {"1": 1} and economy.user_card(3)["trophies"] == {"3": 1} and economy.user_card(4)["trophies"] == {})
chk("audit entries written", db.q1("SELECT COUNT(*) c FROM audit WHERE action='weekly_award'")["c"] == 3)
# an empty week is closed once and never retried
w2 = weekly.last_week(date(2026, 12, 9))[0]
weekly.award_last_week(date(2026, 12, 9)); weekly.award_last_week(date(2026, 12, 9)); chk("empty week recorded as closed once", db.q1("SELECT COUNT(*) c FROM weekly_awards WHERE week=? AND place=0", w2)["c"] == 1)
# per-pair daily cap
ns = [db.pair_kiss(1, 2) for _ in range(5)]
chk("pair counter counts per day, order of ids does not matter", ns == [1, 2, 3, 4, 5] and db.pair_kiss(2, 1) == 6, ns)
chk("another pair starts at 1", db.pair_kiss(1, 3) == 1)
before = db.q1("SELECT COALESCE(SUM(kisses),0) s FROM stats_daily WHERE uid=7")["s"]; k0 = db.get_user(7)["kisses"]
db.inc(7, "kisses", daily=False); db.inc(7, "kisses")
chk("daily=False keeps the lifetime counter but skips the lists", db.get_user(7)["kisses"] == k0 + 2 and db.q1("SELECT COALESCE(SUM(kisses),0) s FROM stats_daily WHERE uid=7")["s"] == before + 1)
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

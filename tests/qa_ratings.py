"""Rating lists with day/week/month/all periods. Dev server: BOT_TOKEN= DEV_MODE=1 DB_PATH=/tmp/rq.db PORT=8001, same DB_PATH here:
   DB_PATH=/tmp/rq.db .venv/bin/python tests/qa_ratings.py"""
import json, os, sys, urllib.request, urllib.error
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/rq.db")
from app import db
B = "localhost:8001"; res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    try: return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e: return e.code, {}
for u in (1, 2, 3, 4): call("/api/profile", u, {"name": f"R{u}", "birth": "2000-01-01", "gender": "m", "lang": "ru"})
# user 1: 10 kisses today; user 2: 5 today + 20 a week ago; user 3: 100 a month+ ago; user 4: nothing
db.inc(1, "kisses", 10); db.inc(2, "kisses", 5)
db.x("UPDATE users SET kisses=kisses+20 WHERE id=2"); db.x("INSERT INTO stats_daily(day,uid,kisses) VALUES(date('now','localtime','-6 days'),2,20) ON CONFLICT(day,uid) DO UPDATE SET kisses=kisses+20")
db.x("UPDATE users SET kisses=kisses+100 WHERE id=3"); db.x("INSERT INTO stats_daily(day,uid,kisses) VALUES(date('now','localtime','-40 days'),3,100)")
c, r = call("/api/ratings/kisses?period=day", 4)
chk("day list has today's players only, best first", c == 200 and [x["id"] for x in r["rows"]] == [1, 2] and r["rows"][0]["v"] == 10 and r["period"] == "day", r)
chk("player with nothing today: mine 0, rank 0", r["mine"] == 0 and r["rank"] == 0, r)
c, r = call("/api/ratings/kisses?period=week", 2)
chk("week includes the 6-days-old kisses (user 2 leads with 25)", [x["id"] for x in r["rows"]] == [2, 1] and r["rows"][0]["v"] == 25 and r["mine"] == 25 and r["rank"] == 1, r)
c, r = call("/api/ratings/kisses?period=month", 1)
chk("month excludes 40-days-old kisses", 3 not in [x["id"] for x in r["rows"]] and r["rank"] == 2, r)
c, r = call("/api/ratings/kisses?period=all", 1)
chk("all-time uses the lifetime counters (user 3 first with 100)", [x["id"] for x in r["rows"]][:3] == [3, 2, 1] and r["rank"] == 3, r)
chk("default period is all", call("/api/ratings/kisses", 1)[1]["rows"][0]["id"] == 3)
chk("bad period rejected", call("/api/ratings/kisses?period=year", 1)[0] == 404)
chk("court ignores the period (still answers)", call("/api/ratings/court?period=week", 1)[0] == 200)
chk("hearts rating removed", call("/api/ratings/hearts", 1)[0] == 404)
db.inc(1, "tracks", 3); db.inc(2, "gifts_received", 2)
chk("tracks day list", [x["id"] for x in call("/api/ratings/tracks?period=day", 3)[1]["rows"]] == [1])
chk("gifts day list", [x["id"] for x in call("/api/ratings/gifts?period=day", 3)[1]["rows"]] == [2])
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

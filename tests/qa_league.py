"""Ligalar va boosterlar. 1) modul darajasida (vaqtinchalik baza), 2) API + WebSocket (dev server :8001, DB_PATH shu server bazasi)."""
import asyncio, json, os, sqlite3, sys, tempfile, urllib.request, urllib.error
from datetime import date, timedelta
SRV_DB = os.environ.get("DB_PATH", "/tmp/lg.db")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []; passed = 0


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


# ---------------------------------------------------------------- 1) modul
tmp = os.path.join(tempfile.mkdtemp(), "lg.db"); os.environ["DB_PATH"] = tmp; sys.path.insert(0, ROOT)
from app import config, db, league  # noqa: E402
for u in (1, 2, 3, 4):
    db.x("INSERT INTO users(id,name,created) VALUES(?,?,0)", u, f"U{u}")
ok("boshida 0", league.points(1) == 0 and league.limit(1) == config.LEAGUE_LIMIT)
ok("1 ball", league.add_points(1, 1) == 1 and league.points(1) == 1)
league.add_points(1, 500); ok("limit yopadi", league.points(1) == config.LEAGUE_LIMIT, league.points(1))
ok("limitdan keyin 0", league.add_points(1, 1) == 0)
db.inv_add(1, "league_limit", 1); ok("limit boosteri", league.use(1, "league_limit") and league.limit(1) == config.LEAGUE_LIMIT + config.LEAGUE_LIMIT_PLUS)
ok("limit kengaygach qo'shadi", league.add_points(1, 3) == 3)
db.inv_add(1, "league_plus5", 1); before = league.points(1); league.add_points(1, 500)
ok("+5 limitni hisobga olmaydi", league.use(1, "league_plus5") and league.points(1) == before + (league.limit(1) - before) + 5, league.points(1))
ok("inventarsiz ishlatib bo'lmaydi", not league.use(2, "league_x2"))
db.inv_add(2, "league_x2", 1); ok("x2 yoqildi", league.use(2, "league_x2") and league.info(2)["x2_left"] > 250)
ok("x2: 1 o'pish = 2 ball", league.add_points(2, 1) == 2)
ok("noma'lum booster rad", not league.use(2, "magnet"))
ok("top tartibi", [r["uid"] for r in league.top()] == [1, 2], league.top())
ok("rank", league.info(1)["rank"] == 1 and league.info(2)["rank"] == 2)
# haftalik sovrinlar: o'tgan haftaga ball yozamiz
lw = league.week_key(date.today() - timedelta(days=7))
for u, p in ((1, 20), (2, 12), (3, 6), (4, 2)):
    db.x("INSERT INTO league_points(week,uid,pts) VALUES(?,?,?)", lw, u, p)
aw = league.award_last_week()
ok("3 ta sovrin (4-o'rin chegaradan past)", [a["uid"] for a in aw] == [1, 2, 3], aw)
ok("sovrin inventarga tushdi", db.inv(1).get("kiss_fire", {}).get("qty") == 3 and db.inv(3).get("slap", {}).get("qty") == 1)
ok("ikkinchi marta to'lanmaydi", league.award_last_week() == [])


# ---------------------------------------------------------------- 2) API + WS
import websockets  # noqa: E402
B = "localhost:8001"


def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    try:
        return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        return e.code, {}


async def api_part():
    con = sqlite3.connect(SRV_DB)
    for uid, g in ((101, "m"), (102, "f")):
        call("/api/profile", uid, {"name": f"L{uid}", "birth": "2000-01-01", "gender": g, "lang": "ru"})
    c, r = call("/api/league", 101); ok("API liga", c == 200 and r["me"]["pts"] == 0 and r["me"]["limit"] == config.LEAGUE_LIMIT and r["top"] == [], r)
    for item in ("league_x2", "league_limit", "league_plus5", "kiss_fire", "slap"):
        con.execute("INSERT INTO inventory(user_id,item,qty) VALUES(101,?,2) ON CONFLICT(user_id,item) DO UPDATE SET qty=2", (item,))
    for item in ("slap", "kiss_fire"):
        con.execute("INSERT INTO inventory(user_id,item,qty) VALUES(102,?,2) ON CONFLICT(user_id,item) DO UPDATE SET qty=2", (item,))
    con.commit()
    c, r = call("/api/league/use", 101, {"item": "league_plus5"}); ok("API +5", c == 200 and r["league"]["pts"] == 5, r.get("league"))
    c, r = call("/api/league/use", 101, {"item": "league_limit"}); ok("API limit +10", r["league"]["limit"] == config.LEAGUE_LIMIT + 10, r.get("league"))
    c, r = call("/api/league/use", 101, {"item": "league_x2"}); ok("API x2", r["league"]["x2_left"] > 250, r.get("league"))
    c, _ = call("/api/league/use", 101, {"item": "slap"}); ok("tanlov boosterini ligada ishlatib bo'lmaydi", c == 400)
    c, r = call("/api/store/buy", 102, {"item": "kiss_fire"}); ok("booster sotib olinadi", c == 200 and r["inv"]["kiss_fire"]["qty"] == 3, r.get("inv"))
    c, r = call("/api/store/buy", 102, {"item": "kiss_fire"}); ok("yana sotib olinadi (to'planadi)", c == 200 and r["inv"]["kiss_fire"]["qty"] == 4)
    con.execute("UPDATE inventory SET qty=2 WHERE user_id=102 AND item='kiss_fire'"); con.commit()
    # stolda: tanlov boosteri
    st, events = {}, []
    async def player(uid):
        ws = await websockets.connect(f"ws://{B}/ws?init=dev:{uid}")
        async def rd():
            async for raw in ws:
                m = json.loads(raw)
                if m.get("t") == "state": st[uid] = m
                if m.get("t") == "chat" and m.get("k") == "boost": events.append(m)
        asyncio.create_task(rd()); await ws.send(json.dumps({"t": "join", "table": 9})); return ws
    w1, w2 = await player(101), await player(102)
    spinner, spun = None, False
    for _ in range(120):
        await asyncio.sleep(.25)
        s = st.get(101, {})
        phase = s.get("phase")
        if phase == "spin_wait" and not spun:
            await (w1 if s.get("turn") == 101 else w2).send(json.dumps({"t": "spin"})); spun = True
        if phase == "ask_spinner": spinner = s.get("turn"); break
    ok("o'pish bosqichiga yetdik", spinner in (101, 102), json.dumps(st.get(101, {}))[:200])
    ws = w1 if spinner == 101 else w2
    await ws.send(json.dumps({"t": "boost", "kind": "slap"})); await asyncio.sleep(1)
    ok("boost hodisasi keldi", len({e["id"] for e in events}) == 1 and events[0]["boost"] == "slap", events)
    await ws.send(json.dumps({"t": "boost", "kind": "kiss_fire"})); await asyncio.sleep(1)
    ok("bir aylanishda bitta boost", len({e["id"] for e in events}) == 1, events)
    inv = call("/api/me", spinner)[1]["inv"]
    ok("slap 2 -> 1, kiss_fire tegilmadi", inv.get("slap", {}).get("qty") == 1 and inv.get("kiss_fire", {}).get("qty") == 2, (spinner, inv))
    await w1.close(); await w2.close(); con.close()

asyncio.run(api_part())
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

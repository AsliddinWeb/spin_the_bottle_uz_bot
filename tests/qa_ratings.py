"""Original-style ratings: kisses / dj / dear / influence / emotion, periods, places, TOP ribbon and the counters behind them.
Fresh dev server on :8001 with the same DB_PATH here."""
import asyncio, json, os, sys, urllib.request, urllib.error
import websockets
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/rq.db")
from app import db
B = "localhost:8001"; res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    try: return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e: return e.code, {}

async def main():
    for u, g in ((1, "m"), (2, "f"), (3, "m"), (4, "f")):
        call("/api/profile", u, {"name": f"R{u}", "birth": "2000-01-01", "gender": g, "lang": "ru"}); db.x("UPDATE users SET hearts=500, smiles=20 WHERE id=?", u)
    got = []
    async def player(uid):
        ws = await websockets.connect(f"ws://{B}/ws?init=dev:{uid}")
        async def rd():
            async for raw in ws:
                got.append((uid, json.loads(raw)))
        asyncio.create_task(rd()); await ws.send(json.dumps({"t": "join", "table": 61})); await asyncio.sleep(.8); return ws
    a, b = await player(1), await player(2)
    send = lambda ws, **m: ws.send(json.dumps(m))
    await send(a, t="gift", to=0, gift="music_now", url="https://youtu.be/dQw4w9WgXcQ"); await asyncio.sleep(4)
    from app.catalog import GIFT_MAP
    price = GIFT_MAP["music_now"][2]
    chk("music: one DJ point per heart spent", db.get_user(1)["dj"] == price, (db.get_user(1)["dj"], price))
    await send(b, t="gift", to=1, gift="rose"); await asyncio.sleep(1)
    chk("a gift received during one's own song adds a point", db.get_user(1)["dj"] == price + 1, db.get_user(1)["dj"])
    await send(a, t="gift", to=2, gift="rose"); await asyncio.sleep(1)
    chk("a gift received during someone else's song adds nothing", db.get_user(2)["dj"] == 0, db.get_user(2)["dj"])
    await send(a, t="gesture", id="nohearts"); await asyncio.sleep(1)   # a free-to-use gesture costing 1 token
    emo = db.get_user(1)["emo"]
    chk("gesture: one emotion point per token spent", emo == 1 and 20 - db.get_user(1)["smiles"] == 1, (emo, db.get_user(1)["smiles"]))
    call("/api/court", 1, {"to": 2}); call("/api/court", 3, {"to": 2}); call("/api/court", 3, {"to": 4})
    c, r = call("/api/ratings/dear", 2); chk("most expensive: the courted players, by price", [x["id"] for x in r["rows"]] == [2, 4] and r["rows"][0]["v"] == 2 and r["mine"] == 2 and r["rank"] == 1, r)
    c, r = call("/api/ratings/influence", 3); chk("most influential: the sum of running courtships", r["rows"][0]["id"] == 3 and r["rows"][0]["v"] == 3 and r["mine"] == 3 and r["rank"] == 1, r)
    chk("a suitor who was outbid has no influence and no place", call("/api/ratings/influence", 1)[1]["mine"] == 0 and call("/api/ratings/influence", 1)[1]["rank"] == 0)
    await asyncio.sleep(21)   # the column lists are shared and cached for 20 s
    for k, ids in (("dj", [1]), ("emotion", [1])):
        for period in ("all", "day", "week", "month"):
            c, r = call(f"/api/ratings/{k}?period={period}", 2); chk(f"{k} {period}", c == 200 and [x["id"] for x in r["rows"]] == ids and r["rank"] == 0, r)
    db.x("UPDATE users SET kisses=7 WHERE id=4"); db.x("INSERT INTO stats_daily(day,uid,kisses) VALUES(date('now','localtime','-40 days'),4,7)")
    chk("kisses: old points count only for all time", call("/api/ratings/kisses?period=month", 4)[1]["mine"] == 0 and call("/api/ratings/kisses", 4)[1]["mine"] >= 7)
    chk("dear/influence ignore the period", call("/api/ratings/dear?period=day", 2)[0] == 200 and call("/api/ratings/influence?period=week", 3)[0] == 200)
    for old in ("gifts", "tracks", "court", "hearts"): chk(f"old rating {old} removed", call(f"/api/ratings/{old}", 1)[0] == 404)
    card = call("/api/user/2", 1)[1]
    chk("profile: five counters with places", set(card["stats"]) == {"kisses", "dj", "dear", "influence", "emotion"} and card["ranks"]["dear"] == 1 and card["ranks"]["emotion"] == 0 and card["court_next"] == 3, (card["stats"], card["ranks"]))
    await a.close(); await b.close()

asyncio.run(main())
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

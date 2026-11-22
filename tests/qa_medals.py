"""Mavzuli medallar. 1) modul darajasida (vaqtinchalik baza), 2) API + WebSocket (dev server :8001, DB_PATH shu server bazasi)."""
import asyncio, json, os, sys, tempfile, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []; passed = 0


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


# ---------------------------------------------------------------- 1) modul
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "md.db"); sys.path.insert(0, ROOT)
from app import db, medals  # noqa: E402
for u in (1, 2):
    db.x("INSERT INTO users(id,name,created,hearts) VALUES(?,?,0,0)", u, f"U{u}")
ok("25 ta medal, 75 yulduz", len(medals.MEDALS) == 25 and len(medals.public()) == 25)
ok("id lar noyob", len({m[0] for m in medals.MEDALS}) == 25)
ok("chegaralar o'sib boradi", all(t[0] < t[1] < t[2] for _, _, t, _, _ in medals.MEDALS))
ok("boshida 0", all(v == [0, 0] for v in medals.progress(1).values()))
for _ in range(4): medals.inc(1, "coffee")
ok("4 ta kofe: hali daraja yo'q", medals.progress(1)["coffee"] == [4, 0] and medals.check(1) == [])
medals.inc(1, "coffee"); got = medals.check(1)
ok("5 ta kofe: 1-daraja + 5 yurak", got == [{"id": "coffee", "tier": 1, "reward": 5}] and db.get_user(1)["hearts"] == 5, got)
ok("qayta tekshirsa to'lamaydi", medals.check(1) == [] and db.get_user(1)["hearts"] == 5)
medals.inc(1, "coffee", 200); got = medals.check(1)
ok("katta sakrash: 2 va 3-daraja birga", [g["tier"] for g in got] == [2, 3] and db.get_user(1)["hearts"] == 5 + 10 + 20, got)
ok("noma'lum kalit e'tiborsiz", (medals.inc(1, "nonsense"), medals.progress(1))[1]["coffee"][1] == 3)
db.x("UPDATE users SET kisses=100 WHERE id=2")
ok("users ustuni: kisser 2-daraja", medals.progress(2)["kisser"] == [100, 2], medals.progress(2)["kisser"])
medals.gift_sent(1, "bomb", "bad"); medals.gift_sent(1, "wine", "gift"); medals.gift_sent(1, "rose", "gift"); medals.gift_sent(1, "ring", "gift")
v = medals.values(1)
ok("yuborilgan sovg'a hisoblagichlari", v["bomb_s"] == 1 and v["bad_s"] == 1 and v["drinks_s"] == 1 and v["flowers_s"] == 1 and v["ring_s"] == 1, v)
medals.gift_received(2, "crown1", "gift", True, True); medals.gift_received(2, "tomato", "bad", False, False); medals.gift_received(2, "cake", "gift", False, False); medals.gift_received(2, "frog", "bad", False, False); medals.gift_received(2, "tea", "gift", False, False)
v = medals.values(2)
ok("olingan sovg'a hisoblagichlari", v["royal_r"] == 1 and v["head_r"] == 1 and v["hit"] == 1 and v["bad_r"] == 2 and v["sweets_r"] == 1 and v["animals_r"] == 1 and v["coffee"] == 1, v)


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


async def live():
    for uid, g in ((201, "m"), (202, "f")):
        call("/api/profile", uid, {"name": f"M{uid}", "birth": "2000-01-01", "gender": g, "lang": "ru"})
    c, cfg = call("/api/config", 201); ok("config da medallar", c == 200 and len(cfg["medals"]) == 25)
    got = {201: [], 202: []}
    async def player(uid):
        ws = await websockets.connect(f"ws://{B}/ws?init=dev:{uid}")
        async def rd():
            async for raw in ws:
                m = json.loads(raw)
                if m.get("t") == "medals": got[uid].append(m["list"])
        asyncio.create_task(rd()); await ws.send(json.dumps({"t": "join", "table": 14})); return ws
    w1, w2 = await player(201), await player(202)
    await asyncio.sleep(1)
    await w1.send(json.dumps({"t": "gift", "to": 202, "gift": "coffee"})); await asyncio.sleep(1.5)
    me1, me2 = call("/api/me", 201)[1]["medals"], call("/api/me", 202)[1]["medals"]
    ok("yuboruvchida: ichimlik sanaldi", me1["bartender"][0] == 1 and me1["generous"][0] == 1, (me1["bartender"], me1["generous"]))
    ok("oluvchida: kofe sanaldi", me2["coffee"][0] == 1 and me2["favorite"][0] == 1, (me2["coffee"], me2["favorite"]))
    ok("ikkalasi stolga qo'shilgan (joins)", me1["traveler"][0] >= 1 and me2["traveler"][0] >= 1)
    await w1.send(json.dumps({"t": "gift", "to": 202, "gift": "bomb"})); await asyncio.sleep(1.5)
    me1, me2 = call("/api/me", 201)[1]["medals"], call("/api/me", 202)[1]["medals"]
    ok("bomba va yomon sovg'a", me1["bomber"][0] == 1 and me1["joker"][0] == 1 and me2["target"][0] == 1, (me1["bomber"], me2["target"]))
    ok("bomber 1-daraja (1 ta bomba) va xabar keldi", me1["bomber"][1] == 1 and any(any(x["id"] == "bomber" for x in lst) for lst in got[201]), got[201])
    await w1.close(); await w2.close()

asyncio.run(live())
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

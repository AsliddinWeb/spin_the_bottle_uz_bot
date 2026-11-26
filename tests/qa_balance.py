"""Ikki akkauntli sinovda topilgan xatolar (server tomoni): yurakcha soni sovg'a va o'pishdan keyin darhol keladi,
chat qatorlarida rasm bor, ping javob oladi. Dev server :8001 va shu serverning bazasi DB_PATH da (yangi baza)."""
import asyncio, json, os, sys, urllib.request
import websockets
sys.path.insert(0, "."); from app import db  # noqa: E402
B = "localhost:8001"; fails = []; passed = 0
PH = {601: "https://example.com/a.jpg", 602: "https://example.com/b.jpg"}


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(r).read())


async def main():
    for uid, g in ((601, "m"), (602, "f")):
        call("/api/profile", uid, {"name": f"B{uid}", "birth": "2000-01-01", "gender": g, "lang": "ru"})
        db.x("UPDATE users SET photo=?, hearts=50 WHERE id=?", PH[uid], uid)
    got = {601: [], 602: []}

    async def player(uid):
        ws = await websockets.connect(f"ws://{B}/ws?init=dev:{uid}")

        async def rd():
            async for raw in ws:
                got[uid].append(json.loads(raw))
        asyncio.create_task(rd()); await ws.send(json.dumps({"t": "join", "table": 51})); await asyncio.sleep(.8); return ws

    a, b = await player(601), await player(602)
    w = {601: a, 602: b}
    await a.send(json.dumps({"t": "ping"})); await asyncio.sleep(.4)
    ok("ping javob oladi", any(m["t"] == "pong" for m in got[601]))
    # medallar/yutuqlar oldindan to'lab qo'yiladi, shunda 'me' faqat to'lov sababli kelishi kerak
    await a.send(json.dumps({"t": "gift", "to": 602, "gift": "rose"})); await asyncio.sleep(1.2)
    got[601].clear()
    await a.send(json.dumps({"t": "gift", "to": 602, "gift": "rose"})); await asyncio.sleep(1.2)
    me = [m for m in got[601] if m["t"] == "me"]
    ok("sovg'adan keyin yuboruvchiga yangi balans keladi", me and me[-1]["me"]["hearts"] == db.get_user(601)["hearts"], me and me[-1]["me"]["hearts"])
    line = [m for m in got[602] if m.get("t") == "chat" and m.get("k") == "gift"][-1]
    ok("sovg'a qatorida ikkala rasm bor", line.get("photo") == PH[601] and line.get("to_photo") == PH[602], line)
    # o'pish: ikkala tomonga 'me'
    def last_state(): return [m for m in got[601] if m["t"] == "state"][-1]
    for attempt in range(3):
        for _ in range(160):
            await asyncio.sleep(.25)
            if last_state()["phase"] == "spin_wait": break
        turn = last_state()["turn"]
        for u in got: got[u] = [m for m in got[u] if m["t"] == "state"][-1:]
        await w[turn].send(json.dumps({"t": "spin"}))
        for _ in range(60):
            await asyncio.sleep(.25)
            if last_state()["phase"] == "ask_spinner": break
        await w[turn].send(json.dumps({"t": "decide", "v": True})); await asyncio.sleep(.6)
        await w[1203 - turn].send(json.dumps({"t": "decide", "v": True})); await asyncio.sleep(1)
        if last_state().get("result") == "kiss": break
    ok("o'pish bo'ldi", last_state().get("result") == "kiss", last_state().get("phase"))
    for u in (601, 602):
        me = [m for m in got[u] if m["t"] == "me"]
        ok(f"o'pishdan keyin {u} ga yangi balans", me and me[-1]["me"]["hearts"] == db.get_user(u)["hearts"], me and me[-1]["me"]["hearts"])
    kiss = [m for m in got[601] if m.get("t") == "chat" and m.get("k") == "kiss"]
    ok("o'pish qatorida rasmlar bor", kiss and kiss[-1].get("photo") and kiss[-1].get("to_photo"), kiss)
    # keyin kirgan o'yinchi tarixda rasmlarni oladi
    await b.close(); await asyncio.sleep(.8); got[602].clear(); b = await player(602)
    hist = [m for m in got[602] if m["t"] == "joined"][-1]["history"]
    rows = [m for m in hist if m["k"] in ("gift", "kiss")]
    ok("tarixdagi qatorlarda rasmlar saqlangan", rows and all(m.get("photo") and m.get("to_photo") for m in rows), len(rows))
    await a.close(); await b.close()

asyncio.run(main())
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

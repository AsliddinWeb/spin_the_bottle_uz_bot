"""Sovg'a avatarda faqat o'yinchi stolda o'tirgancha turadi (original kuzatuvi): uchta joy (bosh / ichimlik / boshqa), chiqib qaytsa yo'qoladi.
Dev server :8001 kerak (yangi baza tavsiya)."""
import asyncio, json, urllib.request
import websockets
B = "localhost:8001"; fails = []; passed = 0


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


def call(path, uid, body):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST")
    urllib.request.urlopen(r).read()


async def main():
    for uid, g in ((501, "m"), (502, "f")):
        call("/api/profile", uid, {"name": f"W{uid}", "birth": "2000-01-01", "gender": g, "lang": "ru"})
    st = {}

    async def player(uid, table=41):
        ws = await websockets.connect(f"ws://{B}/ws?init=dev:{uid}")

        async def rd():
            async for raw in ws:
                m = json.loads(raw)
                if m.get("t") == "state": st[uid] = m
        asyncio.create_task(rd()); await ws.send(json.dumps({"t": "join", "table": table})); await asyncio.sleep(.8); return ws

    a, b = await player(501), await player(502)
    seat = lambda: next(s for s in st[501]["seats"] if s["uid"] == 502)
    for g in ("crown1", "coffee", "rose"):
        await a.send(json.dumps({"t": "gift", "to": 502, "gift": g})); await asyncio.sleep(1)
    got = seat()["gifts"]
    ok("uchta sovg'a birga turadi", set(got) == {"head", "hand", "side"}, got)
    ok("bosh: toj, ichimlik: kofe, boshqa: atirgul", got.get("head") == "👑" and got.get("side") == "🌹" and got.get("hand") not in (None, "👑", "🌹"), got)
    await a.send(json.dumps({"t": "gift", "to": 502, "gift": "candy"})); await asyncio.sleep(1)
    ok("shu joydagi yangi sovg'a eskisini almashtiradi", seat()["gifts"].get("side") != "🌹" and seat()["gifts"].get("head") == "👑", seat()["gifts"])
    await b.send(json.dumps({"t": "leave"})); await asyncio.sleep(.8)
    await b.send(json.dumps({"t": "join", "table": 41})); await asyncio.sleep(1)
    ok("stoldan chiqib qaytsa sovg'alar yo'qoladi", seat()["gifts"] == {}, seat()["gifts"])
    await a.send(json.dumps({"t": "gift", "to": 502, "gift": "king"})); await asyncio.sleep(1)
    await b.send(json.dumps({"t": "join", "table": 42})); await asyncio.sleep(.8); await b.send(json.dumps({"t": "join", "table": 41})); await asyncio.sleep(1)
    ok("stol almashtirib qaytsa ham yo'qoladi", seat()["gifts"] == {}, seat()["gifts"])
    await a.send(json.dumps({"t": "gift", "to": 502, "gift": "king"})); await asyncio.sleep(1)
    await b.close(); await asyncio.sleep(.8); b = await player(502)
    ok("ilovani yopib ochsa ham yo'qoladi", seat()["gifts"] == {}, seat()["gifts"])
    await a.close(); await b.close()

asyncio.run(main())
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

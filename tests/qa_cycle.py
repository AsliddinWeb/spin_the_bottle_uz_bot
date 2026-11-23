"""Tur sikli: (1) spin qilmagan o'yinchi turi ~20 s dan keyin o'tkaziladi (original xatti-harakati tasdiqlanmagan), (2) qaror sanog'i bitta umumiy (original kuzatuvi):
spinner javob bergach ikkinchi bosqichda deadline o'zgarmaydi. Dev server :8001 kerak (yangi baza tavsiya)."""
import asyncio, json, time, urllib.request
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
    for uid, g in ((401, "m"), (402, "f")):
        call("/api/profile", uid, {"name": f"C{uid}", "birth": "2000-01-01", "gender": g, "lang": "ru"})
    st, seen = {}, []
    async def player(uid):
        ws = await websockets.connect(f"ws://{B}/ws?init=dev:{uid}")
        async def rd():
            async for raw in ws:
                m = json.loads(raw)
                if m.get("t") == "state":
                    st[uid] = m
                    if uid == 401: seen.append((time.time(), m["phase"], m["deadline"], m["now"], m["turn"]))
        asyncio.create_task(rd()); await ws.send(json.dumps({"t": "join", "table": 31})); return ws
    w = {401: await player(401), 402: await player(402)}
    # 1) hech kim spin qilmaydi: spin_wait ~20 s, keyin tur o'tkazib yuboriladi (shisha aylanmaydi)
    t_wait = t_end = None; first = None; spun = False
    for _ in range(200):
        await asyncio.sleep(.25)
        s = st.get(401, {}); ph = s.get("phase")
        if ph == "spinning": spun = True
        if ph == "spin_wait" and t_wait is None: t_wait, first = time.time(), s["turn"]
        if t_wait and (ph != "spin_wait" or s.get("turn") != first): t_end = time.time(); break
    ok("kutish ~20 s (18-23)", t_end and 18 <= t_end - t_wait <= 23, t_end and round(t_end - t_wait, 1))
    ok("idle o'yinchi uchun shisha aylanmadi (tur o'tkazildi)", not spun)
    # 2) birinchi javob 2 s dan keyin: ikkinchi bosqich deadline i bir xil
    sent = False
    for _ in range(160):
        await asyncio.sleep(.25)
        ph = st[401]["phase"]
        if ph == "spin_wait" and not sent: await w[st[401]["turn"]].send(json.dumps({"t": "spin"})); sent = True
        if ph == "ask_spinner": break
    spinner = st[401]["turn"]
    d1 = st[401]["deadline"]; await asyncio.sleep(2)
    await w[spinner].send(json.dumps({"t": "decide", "v": True}))
    for _ in range(40):
        await asyncio.sleep(.1)
        if st[401]["phase"] == "ask_target": break
    d2 = st[401]["deadline"]
    ok("ikkinchi bosqich boshlandi", st[401]["phase"] == "ask_target")
    ok("sanoq bitta (deadline bir xil)", abs(d2 - d1) < 150, (d1, d2))
    ok("qolgan vaqt 2 s dan ko'p", d2 - st[401]["now"] > 2000, d2 - st[401]["now"])
    for ws in w.values(): await ws.close()

asyncio.run(main())
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

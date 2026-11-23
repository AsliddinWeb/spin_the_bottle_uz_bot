"""Tur sikli originaldagidek: (1) spin qilmagan o'yinchi uchun shisha ~10 s dan keyin o'zi aylanadi, (2) qaror sanog'i bitta umumiy:
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
    # 1) hech kim spin qilmaydi: spin_wait -> ~10 s -> spinning (o'zi aylanadi)
    t_wait = t_spin = None
    for _ in range(200):
        await asyncio.sleep(.25)
        ph = st.get(401, {}).get("phase")
        if ph == "spin_wait" and t_wait is None: t_wait = time.time()
        if ph == "spinning" and t_wait: t_spin = time.time(); break
    ok("shisha o'zi aylandi", t_spin is not None)
    ok("kutish ~10 s (8-13)", t_spin and 8 <= t_spin - t_wait <= 13, t_spin and round(t_spin - t_wait, 1))
    # 2) birinchi javob 2 s dan keyin: ikkinchi bosqich deadline i bir xil
    spinner = st[401]["turn"]; target = 402 if spinner == 401 else 401
    for _ in range(80):
        await asyncio.sleep(.25)
        if st[401]["phase"] == "ask_spinner": break
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

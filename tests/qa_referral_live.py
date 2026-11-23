"""Jonli: do'stning 50-o'pishi stolda sodir bo'lganda taklif qiluvchiga ❤20 tushadi. Dev server :8001 + DB_PATH (yangi baza)."""
import asyncio, json, os, sqlite3, urllib.request
import websockets
DB = os.environ.get("DB_PATH", "/tmp/rl.db"); B = "localhost:8001"; fails = []; passed = 0


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(r).read())


async def main():
    for uid, g in ((300, "m"), (301, "m"), (302, "f")):
        call("/api/profile", uid, {"name": f"R{uid}", "birth": "2000-01-01", "gender": g, "lang": "ru"})
    con = sqlite3.connect(DB)
    con.execute("UPDATE users SET kisses=49 WHERE id=301")
    for p in (7001, 7002, 7003): con.execute("INSERT INTO pair_kisses(day,lo,hi,n) VALUES('2026-01-01',?,?,1)", (min(301, p), max(301, p)))
    con.execute("INSERT INTO referrals(inviter,invited,paid,ts) VALUES(300,301,0,0)"); con.commit()
    h0 = call("/api/me", 300)["hearts"]
    got, st = [], {}
    async def player(uid):
        ws = await websockets.connect(f"ws://{B}/ws?init=dev:{uid}")
        async def rd():
            async for raw in ws:
                m = json.loads(raw)
                if m.get("t") == "state": st[uid] = m
                if m.get("t") == "ref_paid": got.append(m)
        asyncio.create_task(rd()); await ws.send(json.dumps({"t": "join", "table": 21})) if uid != 300 else None; return ws   # the inviter only listens, he is not at the table
    inviter = await player(300)
    w1, w2 = await player(301), await player(302)
    ws = {301: w1, 302: w2}
    for _ in range(200):
        await asyncio.sleep(.25)
        s = st.get(301, {}); ph = s.get("phase")
        if ph == "spin_wait" and s.get("turn") in ws and s.get("turn") != 300: await ws[s["turn"]].send(json.dumps({"t": "spin"}))
        if ph == "ask_spinner" and s.get("turn") in ws: await ws[s["turn"]].send(json.dumps({"t": "decide", "v": True}))
        if ph == "ask_target" and s.get("target") in ws: await ws[s["target"]].send(json.dumps({"t": "decide", "v": True}))
        if got: break
    await asyncio.sleep(1)
    ok("taklif qiluvchiga xabar keldi", len(got) == 1 and got[0]["hearts"] == 20, got)
    ok("❤20 tushdi", call("/api/me", 300)["hearts"] == h0 + 20, (h0, call("/api/me", 300)["hearts"]))
    ok("yozuv to'langan", con.execute("SELECT paid FROM referrals WHERE invited=301").fetchone()[0] == 1)
    await inviter.close(); await w1.close(); await w2.close(); con.close()

asyncio.run(main())
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

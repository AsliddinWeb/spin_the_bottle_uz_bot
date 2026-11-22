"""Kick & Rescue. Dev server: ADMIN_IDS=204 KICK_DELAY=6 BOT_TOKEN= DEV_MODE=1 DB_PATH=/tmp/kq.db PORT=8001, same DB_PATH here:
   DB_PATH=/tmp/kq.db .venv/bin/python tests/qa_kick.py"""
import asyncio, json, os, sys, urllib.request
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/kq.db")
import websockets
B = "localhost:8001"; res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
def api(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(r).read())
for u in (201, 202, 203, 204, 205, 206): api("/api/profile", u, {"name": f"K{u}", "birth": "2000-01-01", "gender": "m", "lang": "ru"})
hearts = lambda u: api("/api/me", u)["hearts"]

class P:
    def __init__(self, uid): self.uid, self.ws, self.ev, self.state, self.task = uid, None, [], None, None
    async def start(self, table):
        self.ws = await websockets.connect(f"ws://{B}/ws?init=dev:{self.uid}")
        self.task = asyncio.create_task(self.reader()); await self.send({"t": "join", "table": table})
    async def reader(self):
        try:
            async for raw in self.ws:
                m = json.loads(raw); self.ev.append(m)
                if m.get("t") == "state": self.state = m
        except Exception: pass
    async def send(self, m): await self.ws.send(json.dumps(m))
    def kinds(self, k): return [e for e in self.ev if e.get("t") == "chat" and e.get("k") == k]
    def toasts(self): return [e["key"] for e in self.ev if e.get("t") == "toast"]
    def left(self): return [e for e in self.ev if e.get("t") == "left"]
    def seated(self): return bool(self.state and any(s["uid"] == self.uid for s in self.state["seats"]))

async def main():
    a, b, c, d = P(201), P(202), P(203), P(204)
    for p in (a, b, c, d): await p.start(1)
    await asyncio.sleep(1.2)
    chk("4 players seated", all(p.seated() for p in (a, b, c, d)))
    h = hearts(201)
    # 1. free kick
    await a.send({"t": "kick", "to": 202}); await asyncio.sleep(.6)
    chk("kick announced in chat", len(c.kinds("kick")) == 1 and c.kinds("kick")[0]["to_uid"] == 202)
    chk("state carries the pending kick", c.state and [k["uid"] for k in c.state["kicks"]] == [202])
    chk("first kick is free", hearts(201) == h, (h, hearts(201)))
    # 2. restrictions while pending
    await a.send({"t": "kick", "to": 203}); await asyncio.sleep(.3)
    chk("one pending kick per kicker", "kick_busy" in a.toasts(), a.toasts())
    await c.send({"t": "kick", "to": 202}); await asyncio.sleep(.3)
    chk("already pending target refused", "kick_pending" in c.toasts(), c.toasts())
    await d.send({"t": "kick", "to": 203}); await asyncio.sleep(.3)
    chk("owner/staff target... (204 is owner) kicker may kick normal player", len(d.kinds("kick")) == 2)
    await c.send({"t": "kick", "to": 204}); await asyncio.sleep(.3)
    chk("staff cannot be kicked", "kick_staff" in c.toasts(), c.toasts())
    # 3. rescue rules
    hb = hearts(201); await a.send({"t": "rescue", "to": 202}); await asyncio.sleep(.3)
    chk("kicker cannot rescue their own kick", hearts(201) == hb and not a.kinds("rescue"))
    await b.send({"t": "rescue", "to": 202}); await asyncio.sleep(.3)
    chk("target cannot rescue themselves", not b.kinds("rescue"))
    hc = hearts(203)
    await c.send({"t": "rescue", "to": 202}); await asyncio.sleep(.6)
    chk("rescue costs 3 hearts and is announced", hearts(203) == hc - 3 and len(a.kinds("rescue")) == 1, (hc, hearts(203)))
    chk("rescued kick is gone", c.state and all(k["uid"] != 202 for k in c.state["kicks"]))
    await asyncio.sleep(3.0)
    chk("rescued player stays", b.seated() and not b.left())
    # 4. kick not rescued: leaves after the delay and cannot rejoin
    # 204 kicked 203 earlier and nobody rescued 203: that kick times out now
    await asyncio.sleep(3.0)
    chk("203 was kicked by 204 and nobody rescued: removed", c.left() and c.left()[0]["reason"] == "kicked", c.left())
    chk("kickout announced", len(a.kinds("kickout")) >= 1)
    await c.send({"t": "join", "table": 1}); await asyncio.sleep(.6)
    chk("kicked player cannot rejoin that table", "kick_banned" in c.toasts() and not any(e.get("t") == "joined" and e.get("table") == 1 for e in c.ev[-6:]), c.toasts())
    await c.send({"t": "join", "table": "random"}); await asyncio.sleep(.8)
    chk("random join avoids the banned table", not any(e.get("t") == "joined" and e.get("table") == 1 for e in c.ev[-4:]))
    # 5. paid kick (free one already used by 201)
    h = hearts(201); await a.send({"t": "kick", "to": 202}); await asyncio.sleep(.6)
    chk("second kick costs 10 hearts", hearts(201) == h - 10, (h, hearts(201)))
    await b.send({"t": "leave"}); await asyncio.sleep(.5)
    chk("leaving while kicked cancels the kick", a.state and all(k["uid"] != 202 for k in a.state["kicks"]))
    # 6. few players
    chk("table now has 2 players (201, 204)", len(a.state["seats"]) == 2, [s["uid"] for s in a.state["seats"]])
    await a.send({"t": "kick", "to": 204}); await asyncio.sleep(.3)
    chk("needs at least 3 players", "kick_few" in a.toasts(), a.toasts())
    for p in (a, b, c, d):
        try: await p.ws.close()
        except Exception: pass
asyncio.run(main())
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

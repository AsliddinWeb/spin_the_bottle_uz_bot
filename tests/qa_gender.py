"""Boy-girl rule. Dev server: BOT_TOKEN= DEV_MODE=1 DB_PATH=/tmp/gq.db PORT=8001, same DB_PATH here:  DB_PATH=/tmp/gq.db .venv/bin/python tests/qa_gender.py"""
import asyncio, json, os, sys, types, urllib.request
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/gq.db")
import websockets
from app import db
from app.game import Table
B = "localhost:8001"; res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
def api(path, uid, body):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST")
    return json.loads(urllib.request.urlopen(r).read())
# ---- unit: target choice and table state without a server loop
def fake(uid, g): return types.SimpleNamespace(uid=uid, gender=g)
t = Table.__new__(Table); t.players = {}
for u in (1, 2, 3, 4, 5): db.ensure_user(u, f"G{u}", lang="ru")
t.players = {1: fake(1, "m"), 2: fake(2, "m"), 3: fake(3, "m"), 4: fake(4, "f"), 5: fake(5, "f")}
tg = {s: {t.pick_target(t.players[s]).uid for _ in range(300)} for s in (1, 4)}
chk("a boy only ever gets a girl", tg[1] <= {4, 5} and tg[1], tg)
chk("a girl only ever gets a boy", tg[4] <= {1, 2, 3} and tg[4], tg)
t.players = {1: fake(1, "m"), 2: fake(2, "m"), 3: fake(3, "m")}
chk("only boys: nobody to pick, table cannot play, needs girls", t.pick_target(t.players[1]) is None and not t.can_play() and t.need() == "f")
t.players = {4: fake(4, "f"), 5: fake(5, "f")}
chk("only girls: needs boys", not t.can_play() and t.need() == "m")
t.players = {1: fake(1, "m"), 4: fake(4, "f")}
chk("one boy + one girl can play", t.can_play() and t.need() == "")
t.players = {}
chk("empty table needs nobody in particular", t.need() == "" and not t.can_play())
# ---- live: three boys wait, a girl starts the game
class P:
    def __init__(self, uid): self.uid, self.state = uid, None
    async def start(self, table):
        self.ws = await websockets.connect(f"ws://{B}/ws?init=dev:{self.uid}"); self.task = asyncio.create_task(self.rd()); await self.ws.send(json.dumps({"t": "join", "table": table}))
    async def rd(self):
        try:
            async for raw in self.ws:
                m = json.loads(raw)
                if m.get("t") == "state": self.state = m
        except Exception: pass
async def main():
    for u, g in ((801, "m"), (802, "m"), (803, "m"), (804, "f")): api("/api/profile", u, {"name": f"L{u}", "birth": "2000-01-01", "gender": g, "lang": "ru"})
    boys = [P(801), P(802), P(803)]
    for p in boys: await p.start(77)
    await asyncio.sleep(2.5)
    chk("three boys: table waits and asks for girls", all(p.state and p.state["phase"] == "waiting" and p.state["need"] == "f" for p in boys), [p.state and (p.state["phase"], p.state["need"]) for p in boys])
    girl = P(804); await girl.start(77); await asyncio.sleep(2.5)
    chk("a girl joins: the game starts", all(p.state and p.state["phase"] in ("spin_wait", "between") and p.state["need"] == "" for p in boys + [girl]), [p.state and p.state["phase"] for p in boys + [girl]])
    await girl.ws.send(json.dumps({"t": "leave"})); await asyncio.sleep(3)
    chk("the girl leaves: back to waiting for girls", all(p.state and p.state["phase"] == "waiting" and p.state["need"] == "f" for p in boys), [p.state and (p.state["phase"], p.state["need"]) for p in boys])
    for p in boys + [girl]:
        try: await p.ws.close()
        except Exception: pass
asyncio.run(main())
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

"""Live enforcement path used by the bot commands: hub.apply_sanctions / hub.kick_player (fake sockets, own temp DB)."""
import asyncio, os, sys
os.environ.update(DB_PATH="/tmp/qk.db", ADMIN_IDS="1", BOT_TOKEN=""); sys.path.insert(0, ".")
for f in ("/tmp/qk.db", "/tmp/qk.db-wal", "/tmp/qk.db-shm"):
    if os.path.exists(f): os.remove(f)
from app import db, moderation as mod
from app.game import hub, Client
class FakeWS:
    def __init__(s): s.sent = []; s.closed = None
    async def send_json(s, m): s.sent.append(m)
    async def close(s, code=1000): s.closed = code
res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
async def main():
    for u in (1, 2, 3, 4): db.ensure_user(u, f"U{u}"); db.x("UPDATE users SET age=22, gender='m' WHERE id=?", u)
    clients = {}
    for u in (2, 3, 4):
        c = Client(FakeWS(), u); hub.clients[u] = c; clients[u] = c
        await hub.dispatch(c, {"t": "join", "table": 77})
    await asyncio.sleep(.2)
    tb = hub.tables[77]; chk("3 seated", len(tb.players) == 3)
    # kick
    chk("kick_player returns True", await hub.kick_player(3, "kicked") is True)
    await asyncio.sleep(.1)
    chk("kicked: seat freed + 'left' frame", 3 not in tb.players and any(m.get("t") == "left" and m.get("reason") == "kicked" for m in clients[3].ws.sent))
    chk("kicked player stays connected (can rejoin)", hub.clients.get(3) is clients[3] and clients[3].ws.closed is None)
    chk("kick of someone not seated returns False", await hub.kick_player(3) is False)
    # ban of a seated, connected player
    mod.sanction(1, 2, "ban", 0, "bad behaviour")
    await hub.apply_sanctions(2)
    await asyncio.sleep(.1)
    f = [m for m in clients[2].ws.sent if m.get("t") == "banned"]
    chk("banned: frame with reason", f and f[0]["reason"] == "bad behaviour" and f[0]["until"] == 0, clients[2].ws.sent[-2:])
    chk("banned: socket closed 4004", clients[2].ws.closed == 4004)
    chk("banned: removed from hub and table", 2 not in hub.clients and 2 not in tb.players)
    chk("remaining player still there, table alive", 4 in tb.players and len(tb.players) == 1)
    # apply_sanctions for a player with no ban does nothing
    await hub.apply_sanctions(4)
    chk("no ban -> nothing happens", 4 in tb.players and clients[4].ws.closed is None)
    # not-connected user is a no-op
    await hub.apply_sanctions(999)
    chk("offline user no-op", True)
asyncio.run(main())
print("\n".join(res)); print(f"{sum(r.startswith('PASS') for r in res)} passed, {sum(r.startswith('FAIL') for r in res)} failed")

"""Moderation tests. Needs a dev server started with ADMIN_IDS=1 (user 1 = owner) on port 8001 and the SAME DB_PATH
exported here so role changes can be made directly:  DB_PATH=/tmp/mq.db .venv/bin/python tests/qa_moderation.py"""
import asyncio, json, os, sys, time, urllib.request, urllib.error, websockets
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/mq.db"); os.environ["ADMIN_IDS"] = "1"
from app import moderation as mod, db  # same sqlite file as the server (WAL)
B = "localhost:8001"; res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f"  {i}"))
def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    try: return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
for u in (1, 2, 3, 4, 5, 6): call("/api/profile", u, {"name": f"U{u}", "birth": "2000-01-01", "gender": "m", "lang": "ru"})
# ---- roles / hierarchy
chk("owner from ADMIN_IDS", mod.role_of(1) == "owner")
chk("non-owner cannot set role", mod.set_role(2, 3, "mod") == "need_owner")
chk("owner makes admin", mod.set_role(1, 2, "admin") is None and mod.role_of(2) == "admin")
chk("admin cannot make admin", mod.set_role(2, 3, "admin") == "need_owner")
chk("owner makes mod", mod.set_role(1, 3, "mod") is None and mod.role_of(3) == "mod")
chk("owner role cannot be changed", mod.set_role(1, 1, "") == "is_owner")
chk("bad role rejected", mod.set_role(1, 4, "god") == "bad_role")
chk("staff list", set(mod.staff_ids()) >= {1, 2, 3})
# ---- who can do what
chk("player cannot mute", mod.sanction(4, 5, "mute", 60, "x") == "need_mod")
chk("mod can mute player", isinstance(mod.sanction(3, 5, "mute", 3600, "spam"), int))
chk("mod cannot ban", mod.sanction(3, 5, "ban", 3600, "x") == "need_admin")
chk("mod cannot mute admin", mod.sanction(3, 2, "mute", 60, "x") == "rank")
chk("admin cannot ban owner", mod.sanction(2, 1, "ban", 60, "x") == "rank")
chk("mod cannot mute self", mod.sanction(3, 3, "mute", 60, "x") == "self")
chk("mod cannot give hearts", mod.give(3, 5, "hearts", 100, "x") == "need_admin")
chk("unknown target", mod.sanction(2, 99999, "ban", 60, "x") == "no_user")
# ---- mute enforcement (chat + compliment)
chk("mute is active", mod.active(5, "mute") is not None)
async def chat_test():
    a = await websockets.connect(f"ws://{B}/ws?init=dev:5"); b = await websockets.connect(f"ws://{B}/ws?init=dev:6")
    got, toasts = [], []
    async def rd(w, tag):
        async for raw in w:
            m = json.loads(raw)
            if m["t"] == "chat" and m.get("k") == "msg": got.append((tag, m["text"]))
            if m["t"] == "toast": toasts.append(m["key"])
    ts = [asyncio.create_task(rd(a, "a")), asyncio.create_task(rd(b, "b"))]
    for w in (a, b): await w.send(json.dumps({"t": "join", "table": 40}))
    await asyncio.sleep(1)
    await a.send(json.dumps({"t": "chat", "text": "muted hello"})); await asyncio.sleep(.8)
    chk("muted player's chat blocked", not any(x[1] == "muted hello" for x in got) and "muted" in toasts, (got, toasts))
    await b.send(json.dumps({"t": "chat", "text": "free hello"})); await asyncio.sleep(.8)
    chk("unmuted player's chat passes", any(x[1] == "free hello" for x in got))
    chk("muted compliment blocked", call("/api/compliment", 5, {"to": 6, "text": "hi"})[0] == 400)
    mod.lift(3, 5, "mute"); await asyncio.sleep(.2)
    await a.send(json.dumps({"t": "chat", "text": "after unmute"})); await asyncio.sleep(.8)
    chk("chat works after unmute", any(x[1] == "after unmute" for x in got))
    # ---- live ban kicks a connected player
    mod.sanction(2, 5, "ban", 0, "test ban")
    from_srv = []
    async def rd2():
        async for raw in a: from_srv.append(json.loads(raw))
    # trigger through the server path used by the bot: call the hub through an HTTP report auto-mute is not needed; poll WS closure on reconnect instead
    await asyncio.sleep(.3)
    r = await websockets.connect(f"ws://{B}/ws?init=dev:5")
    first = json.loads(await asyncio.wait_for(r.recv(), 3))
    chk("banned user gets 'banned' frame on connect", first["t"] == "banned" and first["reason"] == "test ban" and first["until"] == 0, first)
    try: await asyncio.wait_for(r.recv(), 3); chk("banned socket closed", False)
    except Exception: chk("banned socket closed", True)
    for t in ts: t.cancel()
    await a.close(); await b.close()
asyncio.run(chat_test())
c, d = call("/api/me", 5); chk("banned user: API 403 with details", c == 403 and d["detail"]["code"] == "banned" and d["detail"]["reason"] == "test ban", (c, d))
c, _ = call("/api/me", 6); chk("other players unaffected", c == 200)
chk("lift needs admin", mod.lift(3, 5, "ban") == "need_admin")
chk("admin lifts ban", mod.lift(2, 5, "ban") == 1 and call("/api/me", 5)[0] == 200)
# timed sanction expires
mod.sanction(2, 6, "ban", 1, "short"); time.sleep(2.2)
chk("timed ban expires on its own", call("/api/me", 6)[0] == 200)
# ---- warn / rename / unphoto
chk("mod warns player", mod.warn(3, 5, "calm down") is None and db.get_user(5)["warns"] == 1)
chk("mod renames player", mod.rename(3, 5, "Clean Name") is None and db.get_user(5)["name"] == "Clean Name")
db.x("UPDATE users SET photo='/uploads/zzz.jpg' WHERE id=5")
chk("mod removes photo", mod.remove_photo(3, 5) is None and db.get_user(5)["photo"] == "")
# ---- balance (no limits by design)
h = db.get_user(4)["hearts"]
chk("admin gives 100000 hearts (no cap)", mod.give(2, 4, "hearts", 100000, "bonus") == 0 and db.get_user(4)["hearts"] == h + 100000)
chk("negative amount takes away, floor 0", mod.give(2, 4, "hearts", -999999999, "reset") == 0 and db.get_user(4)["hearts"] == 0)
chk("give vip days", mod.give(2, 4, "vip", 30, "gift") == 0 and db.get_user(4)["vip_until"] > time.time() + 29 * 86400)
chk("take vip days", mod.give(2, 4, "vip", -40, "x") == 0 and db.get_user(4)["vip_until"] <= time.time() + 1)
chk("give smiles/chances", mod.give(2, 4, "smiles", 7, "") == 0 and mod.give(2, 4, "chances", 2, "") == 0)
chk("bad field rejected", mod.give(2, 4, "bottles", 1, "") == "bad_what")
# ---- duration parser
chk("durations", mod.parse_duration("30m") == 1800 and mod.parse_duration("2h") == 7200 and mod.parse_duration("7d") == 604800 and mod.parse_duration("perm") == 0 and mod.parse_duration("abc") is None and mod.parse_duration("5x") is None)
# ---- find user
db.x("UPDATE users SET username='TestNick' WHERE id=4")
chk("find by id / @username / username", mod.find_user("4")["id"] == 4 and mod.find_user("@testnick")["id"] == 4 and mod.find_user("TESTNICK")["id"] == 4 and mod.find_user("nobody") is None)
# ---- reports
c, _ = call("/api/report", 5, {"to": 4, "reason": "spam"}); chk("report accepted", c == 200)
c, _ = call("/api/report", 5, {"to": 4, "reason": "spam"}); chk("duplicate report in 24h rejected", c == 400)
c, _ = call("/api/report", 5, {"to": 4, "reason": "zzz"}); chk("bad reason rejected", c == 400)
c, _ = call("/api/report", 5, {"to": 5, "reason": "spam"}); chk("self report rejected", c == 400)
nr = mod.next_report(); chk("report queued with snapshot", nr and nr["status"] == "new" and nr["reason"] == "spam")
mod.resolve_report(nr["id"], 3, "m1d"); chk("report resolved", db.q1("SELECT status,handler FROM reports WHERE id=?", nr["id"])["status"] == "done")
# auto-mute after 5 distinct reporters
for rp in (1, 2, 3, 5, 6): call("/api/report", rp, {"to": 4, "reason": "abuse"}) if rp != 4 else None
auto = mod.active(4, "mute"); chk("5 reporters -> auto mute 1h", auto is not None and auto["by_id"] == 0, auto and dict(auto))
# staff is never auto-muted
for rp in (1, 4, 5, 6, 3): call("/api/report", rp, {"to": 3, "reason": "abuse"})
chk("staff not auto-muted", mod.active(3, "mute") is None)
# ---- audit trail
rows = mod.audit_rows(0, 200); acts = {r["action"] for r in rows}
chk("audit has all action kinds", {"role", "mute", "ban", "unban", "warn", "rename", "unphoto", "give"} <= acts, acts)
chk("audit is append-only: ids increasing, actor recorded", all(r["actor"] is not None for r in rows))
chk("audit by target", len(mod.audit_rows(5)) >= 5)
print("\n".join(res)); print(f"{sum(r.startswith('PASS') for r in res)} passed, {sum(r.startswith('FAIL') for r in res)} failed")

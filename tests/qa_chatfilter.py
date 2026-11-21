"""Chat filter tests (own temp DB, fake sockets). Run: .venv/bin/python tests/qa_chatfilter.py"""
import asyncio, os, sys
os.environ.update(DB_PATH="/tmp/qc.db", ADMIN_IDS="1", BOT_TOKEN=""); sys.path.insert(0, ".")
for f in ("/tmp/qc.db", "/tmp/qc.db-wal", "/tmp/qc.db-shm"):
    if os.path.exists(f): os.remove(f)
from app import db, moderation as mod, chatfilter as cf
from app.game import hub, Client
res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
bad = ["ты сука", "С У К А", "суууука", "хуй тебе", "Пизда", "fuck you", "f u c k", "shit!", "bitch", "sik tir", "siktir", "qo'taq", "qotaqvoy", "blyat", "Mudaaak", "nahuy", "sikaman"]
good = ["salom", "qalaysiz", "классик", "klassik", "musiqa", "assalom", "Sukhrob", "Хуршид", "привет как дела", "class", "shitake", "sikl", "kotta", "кот", "бляха", "skayp", "men 22 yoshdaman", "1990 yil", "12345"]
chk("bad words caught", not [t for t in bad if not cf.check(9, t, repeat=False)], [t for t in bad if not cf.check(9, t, repeat=False)])
chk("innocent words pass", not [t for t in good if cf.check(8, t, repeat=False)], [t for t in good if cf.check(8, t, repeat=False)])
chk("links caught", all(cf.check(7, t, repeat=False) == "link" for t in ["t.me/abc", "https://x.com", "google.com", "@username123", "www.site.uz"]))
chk("phones caught", all(cf.check(6, t, repeat=False) == "phone" for t in ["+998 90 123 45 67", "998901234567", "90-123-45-67"]))
r = [cf.check(5, "same text") for _ in range(4)]; chk("repeat spam after 3rd", r == [None, None, "repeat", "repeat"], r)
chk("different texts are not repeats", all(cf.check(4, f"msg {i}") is None for i in range(6)))
# staff-editable list
chk("add word", cf.add_word("zzzword", 1) and cf.check(3, "zzzword", repeat=False) == "words")
chk("add stem", cf.add_word("qwerty*", 1) and cf.check(3, "qwertyuiop", repeat=False) == "words")
chk("bad word input rejected", not cf.add_word("a", 1) and not cf.add_word("two words", 1))
chk("delete word", cf.del_word("zzzword") and cf.check(3, "zzzword", repeat=False) is None)
chk("words listed", "qwerty*" in cf.words() and len(cf.words()) > 50)
cf.del_word("qwerty*")
# strikes -> auto-mute through the real chat handler
class FakeWS:
    def __init__(s): s.sent = []
    async def send_json(s, m): s.sent.append(m)
    async def close(s, code=1000): pass
async def main():
    for u in (1, 2, 3): db.ensure_user(u, f"U{u}"); db.x("UPDATE users SET age=22, gender='m' WHERE id=?", u)
    cs = {u: Client(FakeWS(), u) for u in (2, 3)}
    for u, c in cs.items(): hub.clients[u] = c; await hub.dispatch(c, {"t": "join", "table": 90})
    await asyncio.sleep(.2)
    tb = hub.tables[90]
    async def say(c, text): c.last_chat = 0; await tb.handle_chat(c, text)
    await say(cs[2], "salom hammaga")
    chk("clean message delivered", any(m.get("k") == "msg" and m["text"] == "salom hammaga" for m in cs[3].ws.sent))
    await say(cs[2], "ты сука")
    toasts = [m["key"] for m in cs[2].ws.sent if m.get("t") == "toast"]
    chk("bad message blocked + sender told", "filtered_words" in toasts and not any(m.get("text") == "ты сука" for m in cs[3].ws.sent), toasts)
    await say(cs[2], "t.me/spam"); await say(cs[2], "call 998901234567")
    chk("3 strikes -> auto-mute 10 min", mod.active(2, "mute") is not None and mod.active(2, "mute")["by_id"] == 0)
    n = len([m for m in cs[3].ws.sent if m.get("k") == "msg"])
    await say(cs[2], "salom yana"); chk("muted player's clean message blocked too", len([m for m in cs[3].ws.sent if m.get("k") == "msg"]) == n)
    chk("filtered list for staff", len(cf.FILTERED) >= 3)
    chk("audit has the auto mute", any(r["action"] == "mute" and "chat filter" in r["detail"] for r in mod.audit_rows(0, 50)))
    # staff are never auto-muted
    mod.set_role(1, 3, "mod")
    for t in ("fuck", "fuck", "fuck"): await say(cs[3], t)
    chk("staff exempt from auto-mute", mod.active(3, "mute") is None)
asyncio.run(main())
print("\n".join(res)); print(f"{sum(r.startswith('PASS') for r in res)} passed, {sum(r.startswith('FAIL') for r in res)} failed")

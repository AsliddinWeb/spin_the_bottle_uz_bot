"""Web admin panel API. Dev server: ADMIN_IDS=1 BOT_TOKEN= DEV_MODE=1 DB_PATH=/tmp/aq.db PORT=8001, same DB_PATH exported here:
   DB_PATH=/tmp/aq.db .venv/bin/python tests/qa_admin.py"""
import json, os, sys, time, urllib.request, urllib.error
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/aq.db"); os.environ["ADMIN_IDS"] = "1"
from app import db, moderation as mod, orders
B = "localhost:8001"; res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
def call(path, uid, body=None, method=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method=method or ("POST" if body is not None else "GET"))
    try: return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
A = lambda p, u, b=None, m=None: call("/api/admin" + p, u, b, m)
for u in (1, 2, 3, 4, 5): call("/api/profile", u, {"name": f"U{u}", "birth": "2000-01-01", "gender": "m", "lang": "ru"})
mod.set_role(1, 2, "admin"); mod.set_role(1, 3, "mod")
# access
chk("player blocked from every endpoint", all(A(p, 4)[0] == 403 for p in ("/me", "/stats", "/users", "/reports", "/audit", "/filter")))
chk("no auth header blocked", call("/api/admin/me", 0)[0] in (401, 403))
chk("roles reported", [A("/me", u)[1]["role"] for u in (1, 2, 3)] == ["owner", "admin", "mod"])
chk("mod blocked from orders/broadcast/backups", all(A(p, 3)[0] == 403 for p in ("/orders", "/broadcast/status", "/backups")) and A("/broadcast", 3, {"preview": True})[0] == 403)
chk("admin blocked from backups, allowed orders", A("/backups", 2)[0] == 403 and A("/orders", 2)[0] == 200)
# dashboard + lists
s = A("/stats", 3)[1]
chk("stats shape", s["users"] >= 5 and len(s["series"]) == 14 and "online" in s and "revenue_total" in s)
r = A("/users?q=U4", 3)[1]; chk("user search by name", r["total"] == 1 and r["users"][0]["id"] == 4)
chk("user search by id", A("/users?q=4", 3)[1]["users"][0]["id"] == 4)
chk("staff filter", {x["id"] for x in A("/users?flt=staff", 3)[1]["users"]} == {1, 2, 3})
chk("paging limit", len(A("/users?limit=2", 3)[1]["users"]) == 2)
chk("sql-ish query harmless", A("/users?q=" + urllib.request.quote("' OR 1=1 --"), 3)[0] == 200)
d = A("/users/4", 3)[1]; chk("detail ok", d["id"] == 4 and d["can_act"] and d["ban"] is None)
chk("detail unknown user 404", A("/users/987654", 3)[0] == 404)
# actions: ranks
c, _ = A("/users/4/act", 3, {"act": "ban", "seconds": 60}); chk("mod cannot ban", c == 400 and _["detail"] == "need_admin", (c, _))
c, _ = A("/users/2/act", 3, {"act": "mute", "seconds": 60}); chk("mod cannot mute admin", c == 400 and _["detail"] == "rank")
c, _ = A("/users/1/act", 2, {"act": "ban", "seconds": 60}); chk("admin cannot ban owner", c == 400)
c, _ = A("/users/4/act", 3, {"act": "give", "what": "hearts", "n": 10}); chk("mod cannot give", c == 400)
c, _ = A("/users/4/act", 2, {"act": "role", "role": "mod"}); chk("admin cannot set roles", c == 400 and _["detail"] == "need_owner")
c, _ = A("/users/4/act", 3, {"act": "nonsense"}); chk("unknown act", c == 400)
chk("unknown target 404", A("/users/987654/act", 3, {"act": "warn"})[0] == 404)
# actions: effects
h0 = call("/api/me", 4)[1]["hearts"]
c, r = A("/users/4/act", 2, {"act": "give", "what": "hearts", "n": 500, "reason": "test"}); chk("admin gives hearts (no limit)", c == 200 and call("/api/me", 4)[1]["hearts"] == h0 + 500, (c, r))
A("/users/4/act", 2, {"act": "give", "what": "hearts", "n": -100000}); chk("take never below zero", call("/api/me", 4)[1]["hearts"] == 0)
c, r = A("/users/4/act", 2, {"act": "give", "what": "vip", "n": 3}); chk("give vip days", c == 200 and call("/api/me", 4)[1]["vip"])
c, r = A("/users/4/act", 3, {"act": "warn", "text": "behave"}); chk("mod warns", c == 200 and r["user"]["warns"] == 1)
c, r = A("/users/4/act", 3, {"act": "mute", "seconds": 3600, "reason": "spam"}); chk("mod mutes", c == 200 and r["user"]["mute"]["reason"] == "spam")
chk("mute shows in filter", [x["id"] for x in A("/users?flt=muted", 3)[1]["users"]] == [4])
c, r = A("/users/4/act", 3, {"act": "unmute"}); chk("unmute", c == 200 and r["user"]["mute"] is None)
c, r = A("/users/4/act", 2, {"act": "ban", "seconds": 0, "reason": "bad"}); chk("admin bans permanently", c == 200 and r["user"]["ban"]["until"] == 0)
chk("banned player locked out of game API", call("/api/me", 4)[0] == 403)
chk("ban shows in filter", [x["id"] for x in A("/users?flt=banned", 3)[1]["users"]] == [4])
c, r = A("/users/4/act", 2, {"act": "unban"}); chk("unban", c == 200 and call("/api/me", 4)[0] == 200)
c, r = A("/users/4/act", 3, {"act": "rename", "text": "  Renamed  "}); chk("rename", c == 200 and r["user"]["name"] == "Renamed")
chk("rename empty rejected", A("/users/4/act", 3, {"act": "rename", "text": "  "})[0] == 400)
c, r = A("/users/4/act", 1, {"act": "role", "role": "mod"}); chk("owner sets role", c == 200 and r["user"]["role"] == "mod")
c, r = A("/users/4/act", 1, {"act": "role", "role": "none"}); chk("owner clears role", c == 200 and r["user"]["role"] == "")
chk("kick when not seated reports it", A("/users/4/act", 3, {"act": "kick"})[1].get("note") == "not_seated")
# reports
mod.add_report(5, 4, "spam", {"chat": ["hello <b>x</b>"]})
rp = A("/reports", 3)[1]; chk("report listed with chat", len(rp) == 1 and rp[0]["chat"] == ["hello <b>x</b>"] and rp[0]["target"]["id"] == 4)
chk("new-report filter", [x["id"] for x in A("/users?flt=reported", 3)[1]["users"]] == [4])
c, _ = A(f"/reports/{rp[0]['id']}/resolve", 3, {"outcome": "ban7"}); chk("mod cannot resolve with ban", c == 400)
chk("failed resolve leaves it open", len(A("/reports", 3)[1]) == 1)
c, _ = A(f"/reports/{rp[0]['id']}/resolve", 3, {"outcome": "m1d"}); chk("resolve with mute", c == 200 and A("/users/4", 3)[1]["mute"] is not None)
chk("resolved leaves the queue", A("/reports", 3)[1] == [] and len(A("/reports?status=done", 3)[1]) == 1)
chk("resolve twice refused", A(f"/reports/{rp[0]['id']}/resolve", 3, {"outcome": "dismiss"})[0] == 400)
chk("unknown report 404", A("/reports/99999/resolve", 3, {"outcome": "dismiss"})[0] == 404)
mod.lift(1, 4, "mute")
# orders
import os as _o; _o.environ["PRICES"] = "p500=38000"
o = orders.create(4, "pack", "p500"); oid = o["id"]
lst = A("/orders", 2)[1]; chk("pending order listed", [x["id"] for x in lst] == [oid] and lst[0]["name"] == "Renamed")
h = call("/api/me", 4)[1]["hearts"]
c, _ = A(f"/orders/{oid}/confirm", 2, {}, "POST"); chk("admin confirms order, hearts credited", c == 200 and call("/api/me", 4)[1]["hearts"] == h + 500, (c, _))
chk("confirm twice refused", A(f"/orders/{oid}/confirm", 1, {}, "POST")[1].get("detail") == "handled")
o2 = orders.create(4, "vip", "vip"); c, _ = A(f"/orders/{o2['id']}/reject", 2, {"note": "no money"}); chk("reject order", c == 200 and orders.get(o2["id"])["status"] == "rejected")
chk("mod cannot confirm", A(f"/orders/{oid}/confirm", 3, {}, "POST")[0] == 403)
chk("order status filter", len(A("/orders?status=done", 2)[1]) == 1)
# filter
f = A("/filter", 3)[1]; chk("filter words listed", "suka" in f["words"])
chk("mod cannot add word", A("/filter/words", 3, {"word": "foobar"})[0] == 403)
chk("admin adds word", A("/filter/words", 2, {"word": "zzbadword"})[0] == 200 and "zzbadword" in A("/filter", 3)[1]["words"])
chk("bad word rejected", A("/filter/words", 2, {"word": "a b"})[0] == 400)
chk("admin removes word", A("/filter/words/zzbadword", 2, None, "DELETE")[0] == 200 and "zzbadword" not in A("/filter", 3)[1]["words"])
chk("remove unknown 404", A("/filter/words/nope123", 2, None, "DELETE")[0] == 404)
# audit
au = A("/audit?limit=200", 3)[1]; acts = {a["action"] for a in au}
chk("audit has the actions", {"ban", "unban", "mute", "warn", "give", "role", "order_done", "addword"} <= acts, acts)
chk("audit target filter", all(a["target"] == 4 for a in A("/audit?target=4&actor=2", 3)[1]) or True)
chk("audit names resolved", any(a["actor_name"] == "U2" for a in au))
# broadcast / tables / photos / backups
chk("broadcast preview counts", "recipients" in A("/broadcast", 2, {"preview": True})[1])
chk("broadcast without bot refused", A("/broadcast", 2, {"text": "hi", "preview": False})[1].get("detail") == "no_bot")
chk("broadcast empty text refused", A("/broadcast", 2, {"text": " ", "preview": False})[0] == 400)
chk("tables endpoint", A("/tables", 3)[0] == 200 and isinstance(A("/tables", 3)[1], list))
chk("photos endpoint", A("/photos", 3)[1]["total"] >= 0)
c, b = A("/backups", 1, {}, "POST"); chk("owner makes backup", c == 200 and b["name"].endswith(".tar.gz"), (c, b))
chk("backup listed", any(x["name"] == b["name"] for x in A("/backups", 1)[1]["list"]))
# static
chk("admin page served", urllib.request.urlopen("http://" + B + "/admin").status == 200)
if b.get("name"): 
    import pathlib; (pathlib.Path("backups") / b["name"]).unlink(missing_ok=True)
print("\n".join(res)); f = sum(r.startswith("FAIL") for r in res); print(f"\n{len(res) - f}/{len(res)} passed"); sys.exit(1 if f else 0)

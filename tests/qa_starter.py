"""Starter tasks (first spin / kiss / gift). Needs a dev server on :8001 and DB_PATH pointing at its database."""
import json, os, sqlite3, urllib.request, urllib.error
B = "http://localhost:8001"; fails = []; passed = 0
DB = os.environ.get("DB_PATH", "/tmp/sq.db")


def call(path, uid, body=None):
    r = urllib.request.Request(B + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    try:
        return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


call("/api/profile", 77, {"name": "S", "birth": "2000-01-01", "gender": "m", "lang": "uz"})
m = call("/api/me", 77)[1]
ok("three starter tasks", [x["id"] for x in m["starter"]] == ["st_spin", "st_kiss", "st_gift"], m["starter"])
ok("none done at start", not any(x["done"] for x in m["starter"]))
c, _ = call("/api/starter/claim", 77, {"id": "st_spin"}); ok("claim before done rejected", c == 400)
c, _ = call("/api/starter/claim", 77, {"id": "nope"}); ok("unknown id rejected", c == 400)
con = sqlite3.connect(DB); con.execute("UPDATE users SET spins=1, kisses=1, gifts_sent=1 WHERE id=77"); con.commit(); con.close()
m = call("/api/me", 77)[1]; ok("all done after activity", all(x["done"] for x in m["starter"]))
h = m["hearts"]
c, r = call("/api/starter/claim", 77, {"id": "st_spin"}); ok("claim ok", c == 200 and r["hearts"] == h + 3, r.get("hearts"))
c, _ = call("/api/starter/claim", 77, {"id": "st_spin"}); ok("double claim rejected", c == 400)
call("/api/starter/claim", 77, {"id": "st_kiss"}); c, r = call("/api/starter/claim", 77, {"id": "st_gift"})
ok("total +9", r["hearts"] == h + 9, r.get("hearts"))
ok("list disappears when all claimed", r["starter"] == [], r["starter"])
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

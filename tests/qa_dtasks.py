"""Kunlik vazifalar. Dev server :8001 kerak, DB_PATH uning bazasi."""
import json, os, sqlite3, urllib.request, urllib.error, datetime
B = "http://localhost:8001"; fails = []; passed = 0
DB = os.environ.get("DB_PATH", "/tmp/dq.db")


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


call("/api/profile", 78, {"name": "D", "birth": "2000-01-01", "gender": "f", "lang": "uz"})
m = call("/api/me", 78)[1]
d = m["dtasks"]
ok("3 ta vazifa", len(d) == 3 and len({x["id"] for x in d}) == 3, d)
ok("kun ichida bir xil", call("/api/me", 78)[1]["dtasks"] == d)
ok("boshida progress 0", all(x["n"] == 0 and not x["claimed"] for x in d))
t0 = d[0]
c, _ = call("/api/dtask/claim", 78, {"id": t0["id"]}); ok("bajarilmay olib bo'lmaydi", c == 400)
c, _ = call("/api/dtask/claim", 78, {"id": "nope"}); ok("noma'lum id rad", c == 400)
col = {"kiss3": "kisses", "msg5": "msgs", "gift1": "gifts_sent", "music1": "tracks", "spin3": "spins"}[t0["id"]]
con = sqlite3.connect(DB)
con.execute("INSERT INTO stats_daily(day,uid) VALUES(?,78) ON CONFLICT(day,uid) DO NOTHING", (datetime.date.today().isoformat(),))
con.execute(f"UPDATE stats_daily SET {col}=? WHERE uid=78 AND day=?", (t0["goal"], datetime.date.today().isoformat())); con.commit(); con.close()
m = call("/api/me", 78)[1]; x = next(i for i in m["dtasks"] if i["id"] == t0["id"]); ok("progress ko'rinadi", x["n"] == x["goal"], x)
h = m["hearts"]
c, r = call("/api/dtask/claim", 78, {"id": t0["id"]}); ok("claim ok", c == 200 and r["hearts"] == h + t0["reward"], r.get("hearts"))
c, _ = call("/api/dtask/claim", 78, {"id": t0["id"]}); ok("ikki marta rad", c == 400)
ok("claimed belgisi", next(i for i in r["dtasks"] if i["id"] == t0["id"])["claimed"])
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

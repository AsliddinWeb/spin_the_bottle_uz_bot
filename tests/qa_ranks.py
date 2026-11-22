"""Unvonlar (o'pishlar bo'yicha). Dev server :8001 va DB_PATH kerak."""
import json, os, sqlite3, urllib.request, urllib.error
B = "http://localhost:8001"; fails = []; passed = 0
DB = os.environ.get("DB_PATH", "/tmp/kr.db")


def call(path, uid, body=None):
    r = urllib.request.Request(B + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(r).read())


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


call("/api/profile", 79, {"name": "R", "birth": "2000-01-01", "gender": "m", "lang": "uz"})
ok("config ranks", call("/api/config", 79)["ranks"] == [0, 10, 50, 200, 1000])
con = sqlite3.connect(DB)
for k, want in ((0, 0), (9, 0), (10, 1), (49, 1), (50, 2), (199, 2), (200, 3), (999, 3), (1000, 4), (5000, 4)):
    con.execute("UPDATE users SET kisses=? WHERE id=79", (k,)); con.commit()
    ok(f"me rank {k}", call("/api/me", 79)["rank"] == want, call("/api/me", 79)["rank"])
    ok(f"card rank {k}", call("/api/user/79", 79)["rank"] == want)
con.close()
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

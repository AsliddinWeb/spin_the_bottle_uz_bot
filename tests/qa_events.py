"""Fasl tadbirlari (admin API + o'yinchi payloadi). Server: ADMIN_IDS=1 DEV_MODE=1 DB_PATH=/tmp/ev.db, test shu bazani ko'rsatadi."""
import json, urllib.request, urllib.error
B = "http://localhost:8001"; fails = []; passed = 0


def call(path, uid, body=None, method=None):
    r = urllib.request.Request(B + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method=method or ("POST" if body is not None else "GET"))
    try:
        return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


call("/api/profile", 1, {"name": "Admin", "birth": "2000-01-01", "gender": "m", "lang": "ru"})
call("/api/profile", 80, {"name": "P", "birth": "2000-01-01", "gender": "f", "lang": "ru"})
ok("tadbir yo'q", call("/api/me", 80)[1]["event"] is None)
c, _ = call("/api/admin/events", 80, {"uz": "X"}); ok("oddiy o'yinchi rad", c == 403)
c, _ = call("/api/admin/events", 1, {"uz": "", "bonus": 2, "days": 7}); ok("bo'sh nom rad", c == 400)
c, _ = call("/api/admin/events", 1, {"uz": "X", "bonus": 99, "days": 7}); ok("katta bonus rad", c == 400)
c, _ = call("/api/admin/events", 1, {"uz": "X", "bonus": 2, "days": 999}); ok("uzun muddat rad", c == 400)
c, r = call("/api/admin/events", 1, {"uz": "Sevishganlar kuni", "ru": "День влюблённых", "en": "Valentine", "emoji": "💘", "bonus": 2, "days": 7})
ok("tadbir yaratildi", c == 200 and r.get("id"), r); eid = r.get("id")
ev = call("/api/me", 80)[1]["event"]
ok("o'yinchi tilida nom", ev and ev["name"] == "День влюблённых" and ev["bonus"] == 2 and ev["emoji"] == "💘", ev)
c, r = call("/api/admin/events", 1); ok("admin ro'yxat", c == 200 and r["active"]["id"] == eid and len(r["list"]) == 1)
c, _ = call(f"/api/admin/events/{eid}/stop", 80, {}); ok("o'yinchi to'xtata olmaydi", c == 403)
c, _ = call(f"/api/admin/events/{eid}/stop", 1, {}); ok("to'xtatildi", c == 200)
ok("to'xtagach yo'q", call("/api/me", 80)[1]["event"] is None)
c, _ = call("/api/admin/events/9999/stop", 1, {}); ok("yo'q tadbir 404", c == 404)
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

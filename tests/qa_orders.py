"""Manual-purchase orders. Dev server needs: ADMIN_IDS=1 PRICES="p500=38000,vip=60000" PAY_INFO=... SUPPORT=@adminuser, port 8001,
and the same DB_PATH exported:  DB_PATH=/tmp/oq.db .venv/bin/python tests/qa_orders.py"""
import json, os, sys, time, urllib.request, urllib.error
sys.path.insert(0, "."); os.environ.setdefault("DB_PATH", "/tmp/oq.db"); os.environ["ADMIN_IDS"] = "1"
os.environ["PRICES"] = "p500=38000,vip=60000"
from app import orders, db, moderation as mod, config
B = "localhost:8001"; res = []
def chk(n, c, i=""): res.append(("PASS " if c else "FAIL ") + n + ("" if c else f" {i}"))
def call(path, uid, body=None):
    r = urllib.request.Request("http://" + B + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "X-Init-Data": f"dev:{uid}"}, method="POST" if body is not None else "GET")
    try: return 200, json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
for u in (1, 2, 3, 4): call("/api/profile", u, {"name": f"U{u}", "birth": "2000-01-01", "gender": "m", "lang": "ru"})
mod.set_role(1, 2, "admin"); mod.set_role(1, 3, "mod")
cfg = call("/api/config", 4)[1]
chk("config: manual mode + pay info", cfg["payments"] == "manual" and cfg["pay_info"].startswith("Karta"))
chk("config: prices shown, missing price empty", [p["price"] for p in cfg["packs"] if p["id"] == "p500"] == ["38000 so'm"] and [p["price"] for p in cfg["packs"] if p["id"] == "p50"] == [""] and cfg["vip"]["price"] == "60000 so'm")
h0 = call("/api/me", 4)[1]["hearts"]
c, r = call("/api/orders", 4, {"kind": "pack", "id": "p500"})
chk("order created, nothing credited", c == 200 and r["order"]["status"] == "pending" and r["order"]["hearts"] == 500 and r["support"] == "@adminuser" and call("/api/me", 4)[1]["hearts"] == h0, (c, r))
oid = r["order"]["id"]
c, _ = call("/api/orders", 4, {"kind": "pack", "id": "p500"}); chk("same item twice rejected", c == 400)
c, _ = call("/api/orders", 4, {"kind": "pack", "id": "pXXX"}); chk("unknown pack rejected", c == 400)
chk("2nd and 3rd item allowed", call("/api/orders", 4, {"kind": "vip", "id": ""})[0] == 200 and call("/api/orders", 4, {"kind": "pack", "id": "p50"})[0] == 200)
c, _ = call("/api/orders", 4, {"kind": "pack", "id": "p250"}); chk("4th pending order rejected (limit 3)", c == 400)
chk("my orders list", len(call("/api/orders", 4)[1]) == 3)
# who may confirm
chk("player cannot confirm", orders.confirm(4, oid) == "need_admin")
chk("moderator cannot confirm (no money access)", orders.confirm(3, oid) == "need_admin")
chk("unknown order", orders.confirm(2, 99999) == "no_order")
chk("still not credited", call("/api/me", 4)[1]["hearts"] == h0)
r = orders.confirm(2, oid); chk("admin confirms -> 500 hearts credited", isinstance(r, dict) and call("/api/me", 4)[1]["hearts"] == h0 + 500, r)
chk("confirm twice never credits twice", orders.confirm(2, oid) == "handled" and orders.confirm(1, oid) == "handled" and call("/api/me", 4)[1]["hearts"] == h0 + 500)
chk("reject after confirm refused", orders.reject(2, oid) == "handled")
# vip order
vip = [o for o in call("/api/orders", 4)[1] if o["kind"] == "vip"][0]
chk("vip not active before confirm", not call("/api/me", 4)[1]["vip"])
chk("owner confirms vip -> VIP active", isinstance(orders.confirm(1, vip["id"]), dict) and call("/api/me", 4)[1]["vip"])
# reject
p50 = [o for o in call("/api/orders", 4)[1] if o["item"] == "p50"][0]; h1 = call("/api/me", 4)[1]["hearts"]
chk("reject: no credit, status rejected", isinstance(orders.reject(2, p50["id"], "no payment"), dict) and call("/api/me", 4)[1]["hearts"] == h1 and orders.get(p50["id"])["status"] == "rejected")
# cancel
c, r = call("/api/orders", 4, {"kind": "pack", "id": "p50"}); chk("can order again after finishing", c == 200)
chk("player cancels own pending", call(f"/api/orders/{r['order']['id']}/cancel", 4, {})[0] == 200 and orders.get(r["order"]["id"])["status"] == "cancelled")
c, r2 = call("/api/orders", 3, {"kind": "pack", "id": "p50"})
chk("other player cannot cancel someone else's order", call(f"/api/orders/{r2['order']['id']}/cancel", 4, {})[0] == 400)
chk("cancelled order cannot be confirmed", orders.confirm(2, r["order"]["id"]) == "handled")
# stars invoice endpoint is closed in manual mode only when a bot is configured; in dev (no bot) it still grants free for local testing
chk("dev free grant still works (no bot)", call("/api/shop/invoice", 4, {"kind": "pack", "id": "p50"})[0] == 200)
# audit
acts = [(r["action"], r["actor"]) for r in mod.audit_rows(0, 100)]
chk("audit: order_done / order_rejected by the right actors", ("order_done", 2) in acts and ("order_done", 1) in acts and ("order_rejected", 2) in acts, acts)
print("\n".join(res)); print(f"{sum(r.startswith('PASS') for r in res)} passed, {sum(r.startswith('FAIL') for r in res)} failed")

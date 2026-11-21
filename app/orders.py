"""Manual purchases: the player places an order, an admin receives the money outside the bot and confirms it here.

Nothing is credited until an admin (rank admin+) confirms. The amount is frozen when the order is created, so a later
catalog change cannot alter what was agreed. Confirm/reject are atomic (status must still be 'pending').
"""
import time

from . import config, db, economy, moderation as mod
from .catalog import PACKS, VIP_DAYS

MAX_PENDING = 3


def _init() -> None:
    db.x("""CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT, item TEXT,
        hearts INTEGER, price TEXT, status TEXT DEFAULT 'pending', ts INTEGER, handler INTEGER DEFAULT 0, handled_ts INTEGER DEFAULT 0, note TEXT DEFAULT '')""")
    db.x("CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id, status)")


_init()


def price_text(item: str) -> str:
    p = config.PRICES.get(item, "")
    return f"{p} {config.PRICE_CUR}" if p else ""


def create(uid: int, kind: str, item: str) -> dict | str:
    """kind pack|vip. Returns the order row as dict, or an error code."""
    if kind == "pack":
        if item not in PACKS:
            return "bad_item"
        hearts = PACKS[item][1]
    elif kind == "vip":
        item, hearts = "vip", 0
    else:
        return "bad_item"
    if db.q1("SELECT COUNT(*) c FROM orders WHERE user_id=? AND status='pending'", uid)["c"] >= MAX_PENDING:
        return "too_many"
    if db.q1("SELECT 1 FROM orders WHERE user_id=? AND status='pending' AND item=?", uid, item):
        return "already"
    oid = db.x("INSERT INTO orders(user_id,kind,item,hearts,price,ts) VALUES(?,?,?,?,?,?)",
               uid, kind, item, hearts, price_text(item), int(time.time())).lastrowid
    return dict(db.q1("SELECT * FROM orders WHERE id=?", oid))


def get(oid: int):
    return db.q1("SELECT * FROM orders WHERE id=?", oid)


def pending(limit: int = 10) -> list:
    return db.q("SELECT * FROM orders WHERE status='pending' ORDER BY id LIMIT ?", limit)


def mine(uid: int, limit: int = 10) -> list:
    return [dict(r) for r in db.q("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", uid, limit)]


def describe(o) -> str:
    what = f"VIP {VIP_DAYS} kun" if o["kind"] == "vip" else f"❤{o['hearts']}"
    return f"{what}" + (f" · {o['price']}" if o["price"] else "")


def confirm(actor: int, oid: int) -> str | dict:
    if mod.rank(actor) < mod.RANK["admin"]:
        return "need_admin"
    o = get(oid)
    if not o:
        return "no_order"
    cur = db.x("UPDATE orders SET status='done', handler=?, handled_ts=? WHERE id=? AND status='pending'", actor, int(time.time()), oid)
    if cur.rowcount != 1:  # someone else already handled it: never credit twice
        return "handled"
    economy.apply_payload(o["user_id"], f"{o['kind']}:{o['item']}")
    mod.audit(actor, "order_done", o["user_id"], f"#{oid} {describe(o)}")
    return dict(o)


def reject(actor: int, oid: int, note: str = "") -> str | dict:
    if mod.rank(actor) < mod.RANK["admin"]:
        return "need_admin"
    o = get(oid)
    if not o:
        return "no_order"
    cur = db.x("UPDATE orders SET status='rejected', handler=?, handled_ts=?, note=? WHERE id=? AND status='pending'", actor, int(time.time()), note[:200], oid)
    if cur.rowcount != 1:
        return "handled"
    mod.audit(actor, "order_rejected", o["user_id"], f"#{oid} {note}")
    return dict(o)


def cancel(uid: int, oid: int) -> bool:
    return db.x("UPDATE orders SET status='cancelled', handled_ts=? WHERE id=? AND user_id=? AND status='pending'", int(time.time()), oid, uid).rowcount == 1

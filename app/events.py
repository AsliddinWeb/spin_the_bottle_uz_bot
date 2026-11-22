"""Seasonal events: an admin starts an event for N days; while it runs every kiss pays `bonus` extra hearts and players see a banner."""
import json
import time

from . import db

db._db.execute("CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, emoji TEXT, bonus INTEGER, starts INTEGER, ends INTEGER, enabled INTEGER DEFAULT 1, creator INTEGER DEFAULT 0)")
_CACHE: tuple[float, dict | None] = (0.0, None)


def _row(r) -> dict:
    return {"id": r["id"], "name": json.loads(r["name"]), "emoji": r["emoji"], "bonus": r["bonus"], "starts": r["starts"], "ends": r["ends"], "enabled": bool(r["enabled"])}


def active() -> dict | None:
    """The running event (the one that ends last if several overlap); cached for 20 s."""
    global _CACHE
    now = time.time()
    if now - _CACHE[0] > 20:
        r = db.q1("SELECT * FROM events WHERE enabled=1 AND starts<=? AND ends>? ORDER BY ends DESC LIMIT 1", int(now), int(now))
        _CACHE = (now, _row(r) if r else None)
    return _CACHE[1]


def bonus() -> int:
    e = active()
    return e["bonus"] if e else 0


def public(lang: str) -> dict | None:
    e = active()
    if not e:
        return None
    return {"id": e["id"], "name": e["name"].get(lang) or e["name"].get("uz") or "", "emoji": e["emoji"], "bonus": e["bonus"], "ends": e["ends"]}


def create(name: dict, emoji: str, bonus_hearts: int, days: float, creator: int) -> int | None:
    name = {k: str(name.get(k, "")).strip()[:40] for k in ("uz", "ru", "en")}
    if not name["uz"] or not 0 <= bonus_hearts <= 20 or not 0 < days <= 60:
        return None
    for k in ("ru", "en"):
        name[k] = name[k] or name["uz"]
    now = int(time.time())
    cur = db.x("INSERT INTO events(name,emoji,bonus,starts,ends,creator) VALUES(?,?,?,?,?,?)", json.dumps(name, ensure_ascii=False), (emoji.strip() or "\U0001F389")[:4], bonus_hearts, now, now + int(days * 86400), creator)
    reset()
    return cur.lastrowid


def stop(eid: int) -> bool:
    ok = db.q1("SELECT id FROM events WHERE id=?", eid) is not None
    if ok:
        db.x("UPDATE events SET enabled=0 WHERE id=?", eid)
        reset()
    return ok


def listing() -> list:
    return [_row(r) for r in db.q("SELECT * FROM events ORDER BY id DESC LIMIT 30")]


def reset() -> None:
    global _CACHE
    _CACHE = (0.0, None)

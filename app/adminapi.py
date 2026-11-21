"""Web admin panel API (/api/admin/*). Same rules as the bot commands: every action goes through `moderation` / `orders`,
so rank checks and the audit log are identical. Access = valid Telegram initData of a staff member (mod or higher).
"""
import asyncio
import json
import re
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from . import auth, backup, bot as botmod, chatfilter, config, db, moderation as mod, orders

router = APIRouter(prefix="/api/admin")
ADMIN = mod.RANK["admin"]
OWNER = mod.RANK["owner"]


def staff(x_init_data: str = Header(default="")):
    u = auth.authenticate(x_init_data)
    if not u or mod.rank(u["id"]) < mod.RANK["mod"]:
        raise HTTPException(403, "forbidden")
    return u


def _need(u, level: int) -> None:
    if mod.rank(u["id"]) < level:
        raise HTTPException(403, "need_role")


def _fail(code: str):
    raise HTTPException(400, code)


def _hub():
    from .game import hub
    return hub


def _ba():
    from . import botadmin
    return botadmin


def _user_row(u) -> dict:
    now = time.time()
    return {
        "id": u["id"], "name": u["name"], "username": u["username"], "age": u["age"], "gender": u["gender"], "lang": u["lang"],
        "photo": u["photo"], "hearts": u["hearts"], "smiles": u["smiles"], "chances": u["chances"], "kisses": u["kisses"],
        "gifts_sent": u["gifts_sent"], "gifts_received": u["gifts_received"], "msgs": u["msgs"], "tracks": u["tracks"],
        "vip_until": u["vip_until"] if u["vip_until"] > now else 0, "role": mod.role_of(u["id"]), "warns": u["warns"],
        "created": u["created"], "last_seen": u["last_seen"], "bot_started": u["bot_started"],
        "online": u["id"] in _hub().clients,
    }


def _sanc(s) -> dict | None:
    return {"id": s["id"], "until": s["until"], "reason": s["reason"], "by": s["by_id"], "ts": s["ts"]} if s else None


# ---------------------------------------------------------------- who am I / dashboard
@router.get("/me")
async def me(u=Depends(staff)):
    return {"id": u["id"], "name": u["name"], "role": mod.role_of(u["id"]), "dev": config.DEV_MODE}


def _money(price: str) -> int:
    m = re.match(r"\s*(\d[\d\s.,]*)", price or "")
    return int(re.sub(r"\D", "", m.group(1))) if m else 0


@router.get("/stats")
async def stats(u=Depends(staff)):
    now = int(time.time())
    one = lambda sql, *a: db.q1(sql, *a)[0]
    day = lambda ts: time.strftime("%m-%d", time.localtime(ts))
    days = [now - 86400 * i for i in range(13, -1, -1)]
    new_by, rev_by, ord_by = {}, {}, {}
    for r in db.q("SELECT created FROM users WHERE created>?", now - 14 * 86400):
        new_by[day(r["created"])] = new_by.get(day(r["created"]), 0) + 1
    for r in db.q("SELECT handled_ts, price FROM orders WHERE status='done' AND handled_ts>?", now - 14 * 86400):
        d = day(r["handled_ts"])
        rev_by[d] = rev_by.get(d, 0) + _money(r["price"]); ord_by[d] = ord_by.get(d, 0) + 1
    hub = _hub()
    return {
        "users": one("SELECT COUNT(*) FROM users"), "active24": one("SELECT COUNT(*) FROM users WHERE last_seen>?", now - 86400),
        "new24": one("SELECT COUNT(*) FROM users WHERE created>?", now - 86400), "online": len(hub.clients),
        "seated": sum(len(t.players) for t in hub.tables.values()), "tables_live": sum(1 for t in hub.tables.values() if t.players),
        "bans": one("SELECT COUNT(*) FROM sanctions WHERE kind='ban' AND active=1 AND (until=0 OR until>?)", now),
        "mutes": one("SELECT COUNT(*) FROM sanctions WHERE kind='mute' AND active=1 AND (until=0 OR until>?)", now),
        "reports_new": one("SELECT COUNT(*) FROM reports WHERE status='new'"),
        "orders_pending": one("SELECT COUNT(*) FROM orders WHERE status='pending'"),
        "revenue_total": sum(_money(r["price"]) for r in db.q("SELECT price FROM orders WHERE status='done'")),
        "cur": config.PRICE_CUR,
        "series": [{"d": day(t), "new": new_by.get(day(t), 0), "rev": rev_by.get(day(t), 0), "orders": ord_by.get(day(t), 0)} for t in days],
    }


# ---------------------------------------------------------------- users
@router.get("/users")
async def users(q: str = "", flt: str = "", limit: int = 30, offset: int = 0, u=Depends(staff)):
    limit = max(1, min(limit, 100))
    where, args = [], []
    q = q.strip()
    if q:
        if q.lstrip("-").isdigit():
            where.append("id=?"); args.append(int(q))
        else:
            where.append("(lower(name) LIKE ? OR lower(username) LIKE ?)"); args += [f"%{q.lstrip('@').lower()}%"] * 2
    now = int(time.time())
    if flt == "banned":
        where.append("id IN (SELECT user_id FROM sanctions WHERE kind='ban' AND active=1 AND (until=0 OR until>?))"); args.append(now)
    elif flt == "muted":
        where.append("id IN (SELECT user_id FROM sanctions WHERE kind='mute' AND active=1 AND (until=0 OR until>?))"); args.append(now)
    elif flt == "staff":
        ids = mod.staff_ids()
        where.append(f"id IN ({','.join('?' * len(ids))})"); args += ids
    elif flt == "vip":
        where.append("vip_until>?"); args.append(now)
    elif flt == "online":
        ids = list(_hub().clients) or [0]
        where.append(f"id IN ({','.join('?' * len(ids))})"); args += ids
    elif flt == "reported":
        where.append("id IN (SELECT target FROM reports WHERE status='new')")
    w = (" WHERE " + " AND ".join(where)) if where else ""
    total = db.q1(f"SELECT COUNT(*) FROM users{w}", *args)[0]
    rows = db.q(f"SELECT * FROM users{w} ORDER BY last_seen DESC, id DESC LIMIT ? OFFSET ?", *args, limit, max(0, offset))
    return {"total": total, "users": [_user_row(r) for r in rows]}


@router.get("/users/{uid}")
async def user_detail(uid: int, u=Depends(staff)):
    t = db.get_user(uid)
    if not t:
        raise HTTPException(404, "no_user")
    s = mod.user_summary(t)
    now_table = next((tb.id for tb in _hub().tables.values() if uid in tb.players), 0)
    return {
        **_user_row(t), "ban": _sanc(s["ban"]), "mute": _sanc(s["mute"]), "reports": s["reports"], "reporters": s["reporters"],
        "table": now_table, "my_rank": mod.rank(u["id"]), "can_act": mod.can_act(u["id"], uid) is None,
        "history": [{**_sanc(r), "kind": r["kind"], "active": r["active"]} for r in db.q("SELECT * FROM sanctions WHERE user_id=? ORDER BY id DESC LIMIT 15", uid)],
        "audit": [dict(r) for r in mod.audit_rows(uid, 15)],
        "orders": [dict(r) for r in db.q("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", uid)],
        "gifts": [dict(r) for r in db.q("SELECT sender, target, gift, emoji, ts FROM gifts_log WHERE sender=? OR target=? ORDER BY id DESC LIMIT 12", uid, uid)],
    }


class Act(BaseModel):
    act: str
    seconds: int = 0           # ban / mute: 0 = permanent
    reason: str = ""
    text: str = ""             # warn text, new name
    what: str = ""             # give: hearts|smiles|chances|vip
    n: int = 0
    role: str = ""


@router.post("/users/{uid}/act")
async def user_act(uid: int, b: Act, u=Depends(staff)):
    actor, ba, hub = u["id"], _ba(), _hub()
    if not db.get_user(uid):
        raise HTTPException(404, "no_user")
    reason = (b.reason or "panel").strip()[:200]
    out = ""
    if b.act in ("ban", "mute"):
        if b.seconds < 0:
            _fail("bad_duration")
        r = mod.sanction(actor, uid, b.act, b.seconds, reason)
        if isinstance(r, str):
            _fail(r)
        until = int(time.time()) + b.seconds if b.seconds else 0
        await ba.notify_player(uid, b.act, reason, until)
        if b.act == "ban":
            await hub.apply_sanctions(uid)
        else:
            await hub.push_me(uid)
    elif b.act in ("unban", "unmute"):
        r = mod.lift(actor, uid, b.act[2:])
        if isinstance(r, str):
            _fail(r)
        if b.act == "unban" and r:
            await ba.notify_player(uid, "unban")
        out = "none_active" if not r else ""
    elif b.act == "warn":
        text = (b.text or reason)[:200]
        r = mod.warn(actor, uid, text)
        if r:
            _fail(r)
        await ba.notify_player(uid, "warn", text)
    elif b.act == "kick":
        if err := mod.can_act(actor, uid):
            _fail(err)
        mod.audit(actor, "kick", uid)
        out = "" if await hub.kick_player(uid) else "not_seated"
    elif b.act == "rename":
        if not b.text.strip():
            _fail("empty")
        if r := mod.rename(actor, uid, b.text):
            _fail(r)
        await hub.push_me(uid)
    elif b.act == "unphoto":
        if r := mod.remove_photo(actor, uid):
            _fail(r)
        await hub.push_me(uid)
    elif b.act == "give":
        if r := mod.give(actor, uid, b.what, b.n, reason):
            _fail(r)
        await hub.push_me(uid)
    elif b.act == "role":
        if r := mod.set_role(actor, uid, "" if b.role in ("", "none", "player") else b.role):
            _fail(r)
    else:
        _fail("bad_act")
    return {"ok": True, "note": out, "user": await user_detail(uid, u)}


# ---------------------------------------------------------------- reports
def _report(r) -> dict:
    t, rep = db.get_user(r["target"]), db.get_user(r["reporter"])
    snap = json.loads(r["snapshot"] or "{}")
    return {
        "id": r["id"], "ts": r["ts"], "reason": r["reason"], "status": r["status"], "outcome": r["outcome"], "handler": r["handler"],
        "target": {"id": r["target"], "name": t["name"] if t else "?", "photo": t["photo"] if t else ""},
        "reporter": {"id": r["reporter"], "name": rep["name"] if rep else "?"},
        "chat": snap.get("chat", []),
        "total": db.q1("SELECT COUNT(*) FROM reports WHERE target=? AND status!='dismissed'", r["target"])[0],
    }


@router.get("/reports")
async def reports(status: str = "new", limit: int = 50, u=Depends(staff)):
    st = status if status in ("new", "done", "dismissed") else "new"
    rows = db.q("SELECT * FROM reports WHERE status=? ORDER BY id DESC LIMIT ?", st, max(1, min(limit, 100)))
    return [_report(r) for r in rows]


class Resolve(BaseModel):
    outcome: str  # warn | m1d | kick | ban7 | dismiss


@router.post("/reports/{rid}/resolve")
async def resolve(rid: int, b: Resolve, u=Depends(staff)):
    r = db.q1("SELECT * FROM reports WHERE id=?", rid)
    if not r:
        raise HTTPException(404, "no_report")
    if r["status"] != "new":
        _fail("handled")
    if b.outcome != "dismiss":
        act = {"warn": Act(act="warn", text="qoidalarni buzmang / please follow the rules"),
               "m1d": Act(act="mute", seconds=86400, reason="report"),
               "kick": Act(act="kick"), "ban7": Act(act="ban", seconds=7 * 86400, reason="report")}.get(b.outcome)
        if not act:
            _fail("bad_outcome")
        await user_act(r["target"], act, u)   # raises 400 with the same codes as a normal action
    mod.resolve_report(rid, u["id"], b.outcome)
    return {"ok": True}


# ---------------------------------------------------------------- orders (admin+)
def _order(o) -> dict:
    t = db.get_user(o["user_id"])
    return {**dict(o), "name": t["name"] if t else "?", "username": t["username"] if t else "", "text": orders.describe(o)}


@router.get("/orders")
async def orders_list(status: str = "pending", limit: int = 60, u=Depends(staff)):
    _need(u, ADMIN)
    where, args = ("WHERE status=?", [status]) if status in ("pending", "done", "rejected", "cancelled") else ("", [])
    return [_order(o) for o in db.q(f"SELECT * FROM orders {where} ORDER BY id DESC LIMIT ?", *args, max(1, min(limit, 200)))]


class Note(BaseModel):
    note: str = ""


@router.post("/orders/{oid}/confirm")
async def order_confirm(oid: int, u=Depends(staff)):
    _need(u, ADMIN)
    r = orders.confirm(u["id"], oid)
    if isinstance(r, str):
        _fail(r)
    await _ba()._tell_order(r, "done")
    return {"ok": True}


@router.post("/orders/{oid}/reject")
async def order_reject(oid: int, b: Note, u=Depends(staff)):
    _need(u, ADMIN)
    r = orders.reject(u["id"], oid, b.note)
    if isinstance(r, str):
        _fail(r)
    await _ba()._tell_order(r, "no", b.note)
    return {"ok": True}


# ---------------------------------------------------------------- chat filter
@router.get("/filter")
async def filter_info(u=Depends(staff)):
    chatfilter.check(0, "x", repeat=False) if not chatfilter._loaded else None  # make sure words are loaded
    return {"words": chatfilter.words(), "recent": [
        {"ts": ts, "uid": uid, "kind": kind, "text": text, "name": (db.get_user(uid) or {"name": "?"})["name"]}
        for ts, uid, kind, text in reversed(chatfilter.FILTERED)]}


class Word(BaseModel):
    word: str


@router.post("/filter/words")
async def filter_add(b: Word, u=Depends(staff)):
    _need(u, ADMIN)
    if not chatfilter.add_word(b.word, u["id"]):
        _fail("bad_word")
    mod.audit(u["id"], "addword", 0, b.word)
    return {"ok": True}


@router.delete("/filter/words/{word}")
async def filter_del(word: str, u=Depends(staff)):
    _need(u, ADMIN)
    if not chatfilter.del_word(word):
        raise HTTPException(404, "no_word")
    mod.audit(u["id"], "delword", 0, word)
    return {"ok": True}


# ---------------------------------------------------------------- audit
@router.get("/audit")
async def audit_list(target: int = 0, actor: int = 0, action: str = "", limit: int = 60, u=Depends(staff)):
    where, args = [], []
    if target:
        where.append("target=?"); args.append(target)
    if actor:
        where.append("actor=?"); args.append(actor)
    if action:
        where.append("action=?"); args.append(action)
    w = (" WHERE " + " AND ".join(where)) if where else ""
    rows = db.q(f"SELECT * FROM audit{w} ORDER BY id DESC LIMIT ?", *args, max(1, min(limit, 200)))
    name = lambda i: ((db.get_user(i) or {"name": "system" if i == 0 else f"#{i}"})["name"]) if i else "system"
    return [{**dict(r), "actor_name": name(r["actor"]), "target_name": name(r["target"]) if r["target"] else ""} for r in rows]


# ---------------------------------------------------------------- backups (owner)
def _bk(p) -> dict:
    return {"name": p.name, "size": backup.human_size(p), "ts": int(p.stat().st_mtime)}


@router.get("/backups")
async def backups(u=Depends(staff)):
    _need(u, OWNER)
    return {"keep": backup.KEEP, "every_h": backup.EVERY // 3600, "list": [_bk(p) for p in reversed(backup.list_backups())]}


@router.post("/backups")
async def backup_now(u=Depends(staff)):
    _need(u, OWNER)
    try:
        p = await asyncio.to_thread(backup.make_backup)
    except Exception as e:
        raise HTTPException(500, f"backup_failed: {e}")
    mod.audit(u["id"], "backup", 0, p.name)
    return _bk(p)


# ---------------------------------------------------------------- broadcast (admin+)
class Broadcast(BaseModel):
    text: str = ""
    preview: bool = True   # true = only count the recipients


_bcast = {"running": False, "sent": 0, "total": 0, "failed": 0}


@router.post("/broadcast")
async def broadcast(b: Broadcast, u=Depends(staff)):
    _need(u, ADMIN)
    rows = db.q("SELECT id, lang FROM users WHERE bot_started=1 AND notify=1")
    if b.preview:
        return {"recipients": len(rows)}
    text = b.text.strip()
    if not text or len(text) > 3500:
        _fail("bad_text")
    if not botmod.bot:
        _fail("no_bot")
    if _bcast["running"]:
        _fail("busy")
    mod.audit(u["id"], "broadcast", 0, f"{len(rows)}: {text[:200]}")
    _bcast.update(running=True, sent=0, total=len(rows), failed=0)

    async def run():
        try:
            for r in rows:
                lang = r["lang"] if r["lang"] in botmod.TEXT else "en"
                ok = await botmod._safe_send(r["id"], text, botmod._play_kb(lang, community=True))
                _bcast["sent" if ok else "failed"] += 1
                await asyncio.sleep(0.05)
        finally:
            _bcast["running"] = False
    asyncio.create_task(run())
    return {"started": True, "recipients": len(rows)}


@router.get("/broadcast/status")
async def broadcast_status(u=Depends(staff)):
    _need(u, ADMIN)
    return _bcast


# ---------------------------------------------------------------- live tables + photo review
@router.get("/tables")
async def tables(u=Depends(staff)):
    out = []
    for t in sorted(_hub().tables.values(), key=lambda t: t.id):
        if not t.players:
            continue
        out.append({"id": t.id, "players": [
            {"id": p.uid, "name": (db.get_user(p.uid) or {"name": "?"})["name"], "seat": p.seat, "role": mod.role_of(p.uid)}
            for p in t.players.values()]})
    return out


@router.get("/photos")
async def photos(limit: int = 40, offset: int = 0, u=Depends(staff)):
    like = "/uploads/%"
    total = db.q1("SELECT COUNT(*) FROM users WHERE photo LIKE ?", like)[0]
    rows = db.q("SELECT id, name, photo, last_seen FROM users WHERE photo LIKE ? ORDER BY rowid DESC LIMIT ? OFFSET ?",
                like, max(1, min(limit, 100)), max(0, offset))
    return {"total": total, "photos": [dict(r) for r in rows]}

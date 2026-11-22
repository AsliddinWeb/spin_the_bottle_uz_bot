import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, bot as botmod, config, db, economy, orders
from .catalog import (TAGS, ACHIEVEMENTS, CHANCE_PACKS, CHANCE_PRICE, DAILY, GESTURES, GIFTS, ITEMS, PACKS, VIP_DAYS,
                      VIP_SMILES, VIP_STARS, WHEEL)
from .game import hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(botmod.run_bot()) if botmod.bot else None
    reminder = asyncio.create_task(botmod.reminder_loop()) if botmod.bot else None
    from . import backup
    backups = asyncio.create_task(backup.backup_loop())
    if not botmod.bot:
        print("BOT_TOKEN not set: running web-only in DEV mode (open http://localhost:%d/?dev=1)" % config.PORT)
    yield
    for tk in (task, reminder, backups):
        if tk:
            tk.cancel()


app = FastAPI(lifespan=lifespan)
UPLOADS = config.ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=config.ROOT / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")


from . import adminapi  # noqa: E402
app.include_router(adminapi.router)


@app.get("/admin")
async def admin_page():
    return FileResponse(config.ROOT / "static" / "admin.html", headers={"Cache-Control": "no-cache"})


@app.get("/")
async def index():
    return FileResponse(config.ROOT / "static" / "index.html", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------- REST
class Profile(BaseModel):
    name: str
    age: int = 0
    birth: str = ""  # ISO date; when given the age is derived from it
    gender: str
    lang: str


class Item(BaseModel):
    item: str


class Invoice(BaseModel):
    kind: str
    id: str = ""


class Target(BaseModel):
    to: int


class ReportReq(BaseModel):
    to: int
    reason: str = "abuse"


class TagVote(BaseModel):
    to: int
    tag: str


class Compliment(BaseModel):
    to: int
    text: str


class Notify(BaseModel):
    on: bool


class TaskReq(BaseModel):
    id: str


@app.get("/api/config")
async def get_config():
    return {
        "gifts": [{"id": g[0], "emoji": g[1], "price": g[2], "kind": g[3], "vip": g[4]} for g in GIFTS],
        "packs": [{"id": k, "stars": v[0], "hearts": v[1], "bonus": v[2], "price": orders.price_text(k)} for k, v in PACKS.items()],
        "vip": {"stars": VIP_STARS, "days": VIP_DAYS, "price": orders.price_text("vip")},
        "payments": config.PAYMENTS, "pay_info": config.PAY_INFO,
        "items": [{"id": k, **v} for k, v in ITEMS.items()],
        "daily": DAILY, "chance_price": CHANCE_PRICE, "chance_packs": [{"n": n, "price": p} for n, p in CHANCE_PACKS.items()],
        "wheel": [{"kind": w[0], "amount": w[1]} for w in WHEEL],
        "achievements": [{"id": a[0], "stat": a[1], "need": a[2], "reward": a[3]} for a in ACHIEVEMENTS],
        "gestures": [{"id": g[0], "emoji": g[1], "price": g[2], "stat": g[3], "need": g[4], "vip": g[5]} for g in GESTURES],
        "vip_smiles": VIP_SMILES, "tags": TAGS,
        "dev": config.DEV_MODE, "bot": botmod.bot_username, "channel": config.CHANNEL,
        "support": config.SUPPORT,
    }


@app.get("/api/me")
async def get_me(u=Depends(auth.current_user)):
    return economy.me_payload(u["id"])


@app.post("/api/profile")
async def set_profile(p: Profile, u=Depends(auth.current_user)):
    name = p.name.strip()[:24]
    from . import chatfilter
    if chatfilter.check(u["id"], name, repeat=False):
        raise HTTPException(400, "bad_name")
    age = economy.age_from_birth(p.birth) if p.birth else p.age
    if not name or not 14 <= age <= 99 or p.gender not in ("m", "f") or p.lang not in ("uz", "ru", "en"):
        raise HTTPException(400, "invalid")
    db.x("UPDATE users SET name=?, age=?, birth=?, gender=?, lang=? WHERE id=?", name, age, p.birth if p.birth else "", p.gender, p.lang, u["id"])
    return economy.me_payload(u["id"])


@app.post("/api/photo")
async def upload_photo(request: Request, u=Depends(auth.current_user)):
    """Raw image body -> square 480px JPEG stored under /uploads (re-encoded, so no metadata or odd formats survive)."""
    from io import BytesIO
    from PIL import Image, ImageOps
    data = await request.body()
    if not 0 < len(data) <= 3_000_000:
        raise HTTPException(413, "too_big")
    try:
        im = ImageOps.exif_transpose(Image.open(BytesIO(data))).convert("RGB")
    except Exception:
        raise HTTPException(400, "bad_image")
    im = ImageOps.fit(im, (480, 480), Image.LANCZOS)
    name = f"{u['id']}_{int(time.time())}.jpg"
    im.save(UPLOADS / name, "JPEG", quality=85, optimize=True)
    old = u["photo"]
    db.x("UPDATE users SET photo=? WHERE id=?", f"/uploads/{name}", u["id"])
    if old.startswith("/uploads/"):
        (UPLOADS / old.rsplit("/", 1)[1]).unlink(missing_ok=True)
    return economy.me_payload(u["id"])


@app.get("/api/music/popular")
async def music_popular(u=Depends(auth.current_user)):
    rows = db.q("SELECT vid, MAX(title) AS title, COUNT(*) AS n FROM tracks_log GROUP BY vid ORDER BY n DESC, MAX(id) DESC LIMIT 20")
    return [{"vid": r["vid"], "title": r["title"]} for r in rows]


_search_cache: dict[str, tuple[float, list]] = {}


@app.get("/api/music/search")
async def music_search(q: str, u=Depends(auth.current_user)):
    """YouTube search for the music picker (cached 10 min, one request per query)."""
    import httpx
    import re as _re
    q = q.strip()[:80]
    if len(q) < 2:
        return []
    hit = _search_cache.get(q.lower())
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    out: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
            r = await c.get("https://www.youtube.com/results", params={"search_query": q},
                            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ru"})
        m = _re.search(r"var ytInitialData = (\{.*?\});</script>", r.text, _re.S)
        if m:
            def walk(o):
                if len(out) >= 20:
                    return
                if isinstance(o, dict):
                    v = o.get("videoRenderer")
                    if v and "videoId" in v:
                        out.append({"vid": v["videoId"], "title": "".join(x.get("text", "") for x in v["title"].get("runs", []))[:100]})
                    for x in o.values():
                        walk(x)
                elif isinstance(o, list):
                    for x in o:
                        walk(x)
            walk(json.loads(m.group(1)))
    except Exception:
        return []
    if len(_search_cache) > 200:
        _search_cache.clear()
    _search_cache[q.lower()] = (time.time(), out)
    return out


@app.get("/api/music/history")
async def music_history(u=Depends(auth.current_user)):
    rows = db.q("SELECT vid, title FROM tracks_log WHERE user_id=? GROUP BY vid ORDER BY MAX(id) DESC LIMIT 20", u["id"])
    return [{"vid": r["vid"], "title": r["title"]} for r in rows]


@app.post("/api/daily/claim")
async def daily_claim(u=Depends(auth.current_user)):
    r = economy.claim_daily(u["id"])
    if not r:
        raise HTTPException(400, "already_claimed")
    return {**r, "me": economy.me_payload(u["id"])}


@app.get("/api/wheel")
async def wheel_info(u=Depends(auth.current_user)):
    return {"winner": economy.last_winner()}


@app.post("/api/wheel/spin")
async def wheel_spin(u=Depends(auth.current_user)):
    r = economy.spin_wheel(u["id"])
    if not r:
        raise HTTPException(400, "no_chances")
    return {**r, "me": economy.me_payload(u["id"])}


class ChancePack(BaseModel):
    n: int = 1


@app.post("/api/wheel/buy")
async def wheel_buy(b: ChancePack | None = None, u=Depends(auth.current_user)):
    n = b.n if b else 1
    if n not in CHANCE_PACKS:
        raise HTTPException(400, "bad_pack")
    if not economy.buy_chance(u["id"], n):
        raise HTTPException(400, "no_hearts")
    return economy.me_payload(u["id"])


@app.post("/api/store/buy")
async def store_buy(b: Item, u=Depends(auth.current_user)):
    r = economy.buy_item(u["id"], b.item)
    if r != "ok":
        raise HTTPException(400, r)
    return economy.me_payload(u["id"])


@app.post("/api/store/equip")
async def store_equip(b: Item, u=Depends(auth.current_user)):
    if not economy.equip(u["id"], b.item):
        raise HTTPException(400, "not_owned")
    return economy.me_payload(u["id"])


@app.post("/api/store/arm")
async def store_arm(b: Item, u=Depends(auth.current_user)):
    if not economy.arm(u["id"], b.item):
        raise HTTPException(400, "none")
    return economy.me_payload(u["id"])


@app.post("/api/orders")
async def create_order(b: Invoice, u=Depends(auth.current_user)):
    from . import botadmin
    if config.PAYMENTS != "manual":
        raise HTTPException(400, "not_manual")
    o = orders.create(u["id"], b.kind, b.id)
    if isinstance(o, str):
        raise HTTPException(400, o)
    await botadmin.alert_order(o, u)
    return {"order": o, "support": config.SUPPORT, "pay_info": config.PAY_INFO}


@app.get("/api/orders")
async def my_orders(u=Depends(auth.current_user)):
    return orders.mine(u["id"])


@app.post("/api/orders/{oid}/cancel")
async def cancel_order(oid: int, u=Depends(auth.current_user)):
    if not orders.cancel(u["id"], oid):
        raise HTTPException(400, "cannot")
    return {"ok": True}


@app.post("/api/shop/invoice")
async def shop_invoice(b: Invoice, u=Depends(auth.current_user)):
    if config.PAYMENTS == "manual" and botmod.bot:  # real money goes through an admin, never an auto-credit
        raise HTTPException(400, "manual")
    payload = f"{b.kind}:{b.id}"
    if b.kind not in ("pack", "vip") or (b.kind == "pack" and b.id not in PACKS):
        raise HTTPException(400, "bad")
    if config.DEV_MODE and not botmod.bot:
        # no Telegram: grant directly so the flow can be tested in a browser
        economy.apply_payload(u["id"], payload)
        return {"dev": True, "me": economy.me_payload(u["id"])}
    link = await botmod.create_invoice(u["id"], b.kind, b.id, u["lang"])
    if not link:
        raise HTTPException(400, "bad")
    return {"link": link}


@app.post("/api/vip/collect")
async def vip_collect(u=Depends(auth.current_user)):
    if not economy.collect_vip_smiles(u["id"]):
        raise HTTPException(400, "nothing")
    return economy.me_payload(u["id"])


@app.get("/api/ratings/{kind}")
async def ratings(kind: str, u=Depends(auth.current_user)):
    if kind not in ("kisses", "gifts", "hearts", "tracks", "court"):
        raise HTTPException(404)
    return economy.top(kind, u["id"])


def _table_row(tid: int) -> dict:
    t = hub.table(tid)
    m, f = t.counts()
    return {"id": t.id, "m": m, "f": f}


@app.get("/api/tables/recent")
async def recent_tables(u=Depends(auth.current_user)):
    rows = db.q("SELECT table_id FROM recent_tables WHERE user_id=? ORDER BY ts DESC LIMIT 5", u["id"])
    recent = [_table_row(r["table_id"]) for r in rows]
    seen = {r["id"] for r in recent}
    busy = sorted((t for t in hub.tables.values() if t.players and t.id not in seen), key=lambda t: -len(t.players))[:5]
    return {"recent": recent, "popular": [_table_row(t.id) for t in busy]}


@app.get("/api/user/{uid}")
async def user_card(uid: int, u=Depends(auth.current_user)):
    card = economy.user_card(uid)
    if not card:
        raise HTTPException(404)
    return card


@app.post("/api/court")
async def court(b: Target, u=Depends(auth.current_user)):
    r = economy.court(u["id"], b.to)
    if isinstance(r, str):
        raise HTTPException(400, r)
    await hub.push_court(b.to)
    tb = hub.clients.get(u["id"]) and hub.clients[u["id"]].table
    if tb and b.to in tb.players:
        await tb.say("court", uid=u["id"], name=u["name"], photo=u["photo"], to_uid=b.to, to_name=tb.players[b.to].name, price=r)
    await hub.push_me(b.to)
    return {"price": r, "me": economy.me_payload(u["id"])}


@app.post("/api/compliment")
async def send_compliment(b: Compliment, u=Depends(auth.current_user)):
    from . import chatfilter, moderation
    if moderation.active(u["id"], "mute"):
        raise HTTPException(400, "muted")
    if (k := chatfilter.check(u["id"], b.text, repeat=False)):
        raise HTTPException(400, "filtered_" + k)
    r = economy.send_compliment(u["id"], b.to, b.text)
    if isinstance(r, str):
        raise HTTPException(400, r)
    target = db.get_user(b.to)
    online = hub.clients.get(b.to)
    if online:
        await online.send({"t": "compliment", "id": r, "uid": u["id"], "name": u["name"], "photo": u["photo"], "text": b.text.strip()[:200]})
    else:
        await botmod.notify_compliment(target, u, b.text, r)
    return {"me": economy.me_payload(u["id"])}


@app.get("/api/tagtask")
async def tagtask(u=Depends(auth.current_user)):
    return economy.tag_task(u["id"])


@app.post("/api/tagtask/vote")
async def tagtask_vote(b: TagVote, u=Depends(auth.current_user)):
    r = economy.tag_vote(u["id"], b.to, b.tag)
    if r in ("bad", "already"):
        raise HTTPException(400, r)
    return {"result": r, "task": economy.tag_task(u["id"]), "me": economy.me_payload(u["id"])}


@app.get("/api/compliments/unread")
async def unread(u=Depends(auth.current_user)):
    return economy.unread_compliments(u["id"])


@app.post("/api/compliments/{cid}/read")
async def read_compliment(cid: int, u=Depends(auth.current_user)):
    if not economy.read_compliment(u["id"], cid):
        raise HTTPException(400, "done")
    return economy.me_payload(u["id"])


@app.post("/api/notify")
async def set_notify(b: Notify, u=Depends(auth.current_user)):
    db.x("UPDATE users SET notify=? WHERE id=?", int(b.on), u["id"])
    return economy.me_payload(u["id"])


@app.post("/api/report")
async def report(b: ReportReq, u=Depends(auth.current_user)):
    from . import botadmin, moderation
    tu = db.get_user(b.to)
    snap = {"name": tu["name"] if tu else "", "chat": []}
    cl = hub.clients.get(b.to)
    if cl and cl.table:  # what the reported player said at their table right now
        snap["chat"] = [m["text"] for m in cl.table.chat if m.get("k") == "msg" and m.get("uid") == b.to][-5:]
    r = moderation.add_report(u["id"], b.to, b.reason, snap)
    if r in ("bad", "dup"):
        raise HTTPException(400, r)
    if r == "auto":
        await hub.apply_sanctions(b.to)
        await botadmin.alert_staff(f"🚨 Auto-mute: #{b.to} (5+ shikoyat / 24 soat). /user {b.to}")
    return {"ok": True}


@app.get("/api/tasks")
async def tasks(u=Depends(auth.current_user)):
    refs = db.q1("SELECT COUNT(*) AS c FROM referrals WHERE inviter=?", u["id"])["c"]
    done = db.claimed(u)
    return {
        "invited": refs, "subscribe_done": "subscribe" in done,
        "compliments_done": "compliments" in done, "compliments_progress": u["gifts_received"],
        "link": f"https://t.me/{botmod.bot_username}?start=ref_{u['id']}" if botmod.bot_username else "",
    }


@app.post("/api/tasks/claim")
async def claim_task(b: TaskReq, u=Depends(auth.current_user)):
    uid, done = u["id"], db.claimed(u)
    if b.id in done:
        raise HTTPException(400, "done")
    if b.id == "subscribe":
        if not await botmod.is_subscribed(uid):
            raise HTTPException(400, "not_subscribed")
        reward = 5
    elif b.id == "compliments":
        if u["gifts_received"] < 5:
            raise HTTPException(400, "not_ready")
        reward = 10
    else:
        raise HTTPException(404)
    db.add_claimed(uid, b.id)
    db.add_hearts(uid, reward)
    return economy.me_payload(uid)


# ----------------------------------------------------------- WebSocket
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, init: str = ""):
    u = auth.authenticate(init)
    await ws.accept()
    if not u:
        await ws.close(4003)
        return
    if info := auth.ban_info(u["id"]):
        await ws.send_json({"t": "banned", **info})
        await ws.close(4004)
        return
    db.touch_seen(u["id"])
    client = await hub.connect(ws, u["id"])
    await client.send({"t": "hello", "me": economy.me_payload(u["id"])})
    await hub.push_court(u["id"])
    try:
        while True:
            # clients ping every 25s; a socket silent for 50s is dead (closed app, lost network)
            raw = await asyncio.wait_for(ws.receive_text(), timeout=50)
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if isinstance(msg, dict):
                if msg.get("t") == "ping":
                    await client.send({"t": "pong"})
                    continue
                try:  # one malformed message must never drop the whole connection
                    await hub.dispatch(client, msg)
                except (ValueError, TypeError, KeyError, AttributeError):
                    pass
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        db.touch_seen(u["id"])
        await hub.drop(client)

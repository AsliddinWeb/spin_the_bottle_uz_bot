"""Hearts economy: profile payload, daily bonus, wheel, shop, purchases."""
import random
import time
from datetime import date, timedelta

from . import config, db
from .catalog import (CHANCE_PACKS, CHANCE_PRICE, DAILY, ITEMS, PACKS, TAG_TASK_NEED, TAG_TASK_REWARD, TAGS, VIP_DAYS, VIP_SMILES, WHEEL, dj_level)


def daily_info(u) -> dict:
    today = date.today()
    last = u["last_daily"]
    yesterday = (today - timedelta(days=1)).isoformat()
    available = last != today.isoformat()
    streak = u["streak"] if last in (today.isoformat(), yesterday) else 0
    day = streak % len(DAILY) if available else (streak - 1) % len(DAILY)
    return {"available": available, "day": day, "streak": streak}


def me_payload(uid: int) -> dict:
    u = db.get_user(uid)
    return {
        "id": uid, "name": u["name"], "age": u["age"], "birth": u["birth"], "gender": u["gender"], "photo": u["photo"],
        "lang": u["lang"], "hearts": u["hearts"], "smiles": u["smiles"], "chances": u["chances"], "kisses": u["kisses"],
        "gifts_sent": u["gifts_sent"], "gifts_received": u["gifts_received"], "spins": u["spins"],
        "msgs": u["msgs"], "streak": u["streak"], "vip": db.is_vip(u), "vip_until": u["vip_until"],
        "frame": u["frame"], "bottle": u["bottle"], "inv": db.inv(uid),
        "daily": daily_info(u), "claimed": db.claimed(u), "notify": bool(u["notify"]),
        "ach": [r["ach"] for r in db.q("SELECT ach FROM achievements WHERE user_id=?", uid)],
        "server_time": int(time.time()), "kick_free_in": max(0, (u["kick_free_ts"] or 0) - int(time.time())),
    }


def claim_daily(uid: int) -> dict | None:
    u = db.get_user(uid)
    info = daily_info(u)
    if not info["available"]:
        return None
    reward = DAILY[info["day"]] * (2 if db.is_vip(u) else 1)
    new_streak = info["streak"] + 1
    db.x("UPDATE users SET last_daily=?, streak=? WHERE id=?", db.today(), new_streak, uid)
    db.add_hearts(uid, reward)
    if info["day"] == len(DAILY) - 1:
        db.inc(uid, "chances")
    db.check_achievements(uid)
    return {"reward": reward}


def spin_wheel(uid: int) -> dict | None:
    cur = db.x("UPDATE users SET chances=chances-1 WHERE id=? AND chances>0", uid)
    if cur.rowcount != 1:
        return None
    idx = random.choices(range(len(WHEEL)), [w[2] for w in WHEEL])[0]
    kind, amount, _ = WHEEL[idx]
    if kind == "hearts":
        db.add_hearts(uid, amount)
    elif kind == "smiles":
        db.x("UPDATE users SET smiles=smiles+? WHERE id=?", amount, uid)
    else:
        db.inc(uid, "chances", amount)
    if kind == "hearts" and amount >= 25:
        u = db.get_user(uid)
        db.x("INSERT INTO wheel_log(user_id,name,kind,amount,ts) VALUES(?,?,?,?,?)",
             uid, u["name"], kind, amount, int(time.time()))
    return {"index": idx, "kind": kind, "amount": amount}


def last_winner() -> dict | None:
    r = db.q1("SELECT w.name, w.amount, u.photo FROM wheel_log w JOIN users u ON u.id=w.user_id ORDER BY w.id DESC LIMIT 1")
    return dict(r) if r else None


def buy_chance(uid: int, n: int = 1) -> bool:
    price = CHANCE_PACKS.get(n)
    if price is None or not db.spend_hearts(uid, price):
        return False
    db.inc(uid, "chances", n)
    return True


def buy_item(uid: int, item: str) -> str:
    it = ITEMS.get(item)
    if not it:
        return "bad_item"
    have = db.inv(uid).get(item)
    if it["kind"] != "booster" and have and have["qty"] > 0:
        return "owned"
    if not db.spend_hearts(uid, it["price"]):
        return "no_hearts"
    db.inv_add(uid, item)
    return "ok"


def equip(uid: int, item: str) -> bool:
    it = ITEMS.get(item)
    have = db.inv(uid).get(item)
    if item == "" or (it and it["kind"] == "frame" and have and have["qty"] > 0):
        db.x("UPDATE users SET frame=? WHERE id=?", item, uid)
        return True
    if it and it["kind"] == "bottle" and have and have["qty"] > 0:
        db.x("UPDATE users SET bottle=? WHERE id=?", item, uid)
        return True
    return False


def arm(uid: int, item: str) -> bool:
    it = ITEMS.get(item)
    if not it or it["kind"] != "booster":
        return False
    cur = db.x("UPDATE inventory SET qty=qty-1, armed=armed+1 WHERE user_id=? AND item=? AND qty>0", uid, item)
    return cur.rowcount == 1


def grant_pack(uid: int, pack_id: str) -> int:
    stars, hearts, _ = PACKS[pack_id]
    db.add_hearts(uid, hearts)
    return hearts


def grant_vip(uid: int) -> None:
    u = db.get_user(uid)
    base = max(u["vip_until"], int(time.time()))
    db.x("UPDATE users SET vip_until=? WHERE id=?", base + VIP_DAYS * 86400, uid)
    db.inc(uid, "chances")


def record_payment(charge_id: str, uid: int, payload: str, stars: int) -> bool:
    """Idempotent: returns False if this charge was already processed."""
    cur = db.x("INSERT OR IGNORE INTO payments VALUES(?,?,?,?,?)", charge_id, uid, payload, stars, int(time.time()))
    return cur.rowcount == 1


def apply_payload(uid: int, payload: str) -> None:
    kind, _, ident = payload.partition(":")
    if kind == "pack" and ident in PACKS:
        grant_pack(uid, ident)
    elif kind == "vip":
        grant_vip(uid)


def user_card(uid: int) -> dict | None:
    u = db.get_user(uid)
    if not u:
        return None
    court = db.q1("SELECT c.price, c.suitor, s.name, s.photo FROM courtship c JOIN users s ON s.id=c.suitor WHERE c.target=?", uid)
    gifts = [{"emoji": r["emoji"], "n": r["c"]} for r in db.q(
        "SELECT emoji, COUNT(*) c FROM gifts_log WHERE target=? GROUP BY emoji ORDER BY c DESC, MAX(id) DESC LIMIT 40", uid)]
    recent = [{"emoji": r["emoji"], "name": r["name"], "photo": r["photo"]} for r in db.q(
        """SELECT g.emoji, s.name, s.photo FROM gifts_log g JOIN users s ON s.id=g.sender
           WHERE g.target=? ORDER BY g.id DESC LIMIT 6""", uid)]
    return {
        "id": uid, "name": u["name"], "age": u["age"], "gender": u["gender"], "photo": u["photo"],
        "gifts": gifts, "recent": recent, "gifts_sent": u["gifts_sent"],
        "vip": db.is_vip(u), "frame": u["frame"], "kisses": u["kisses"], "tracks": u["tracks"], "dj": dj_level(u["tracks"]),
        "gifts_received": u["gifts_received"],
        "trophies": {str(r["place"]): r["c"] for r in db.q("SELECT place, COUNT(*) c FROM weekly_awards WHERE uid=? AND place>0 GROUP BY place", uid)},
        "ach": [r["ach"] for r in db.q("SELECT ach FROM achievements WHERE user_id=?", uid)],
        "suitor": dict(id=court["suitor"], name=court["name"], photo=court["photo"], price=court["price"]) if court else None,
    }


def court(suitor: int, target: int) -> str | int:
    """Pay to become target's suitor (price = current + 1). Returns new price or an error code."""
    if suitor == target or not db.get_user(target):
        return "bad_target"
    cur = db.q1("SELECT * FROM courtship WHERE target=?", target)
    if cur and cur["suitor"] == suitor:
        return "already"
    price = (cur["price"] + 1) if cur else 1
    if not db.spend_hearts(suitor, price):
        return "no_hearts"
    db.add_hearts(target, price)  # the courted player receives the hearts
    db.x("INSERT OR REPLACE INTO courtship(target,suitor,price,ts,seen) VALUES(?,?,?,?,0)", target, suitor, price, int(time.time()))
    return price


def decline_court(uid: int) -> bool:
    """The courted player turns the current suitor away (the hearts they already received stay); the price starts again from 1."""
    return db.x("DELETE FROM courtship WHERE target=?", uid).rowcount == 1


def tag_task(uid: int) -> dict:
    """State of the 'rate 10 players' task plus the next player to rate."""
    done = db.q1("SELECT COUNT(*) c FROM tag_votes WHERE voter=?", uid)["c"]
    paid = "tagtask" in db.claimed(db.get_user(uid))
    nxt = None
    if not paid:
        # a random starting id + an index walk (ORDER BY RANDOM() would sort every user: ~90 ms at 1M users)
        span = db.q1("SELECT MIN(id) lo, MAX(id) hi FROM users")
        q = """SELECT id,name,photo FROM users WHERE id>=? AND id!=? AND age>0 AND id NOT IN (SELECT target FROM tag_votes WHERE voter=?)
               ORDER BY id LIMIT 1"""
        r = db.q1(q, random.randint(span["lo"], span["hi"]), uid, uid) or db.q1(q, span["lo"], uid, uid)
        nxt = dict(r) if r else None
    return {"done": done, "need": TAG_TASK_NEED, "reward": TAG_TASK_REWARD, "paid": paid, "next": nxt}


def tag_vote(uid: int, target: int, tag: str) -> str:
    if tag not in TAGS or target == uid or not db.get_user(target):
        return "bad"
    cur = db.x("INSERT OR IGNORE INTO tag_votes VALUES(?,?,?,?)", uid, target, tag, int(time.time()))
    if cur.rowcount != 1:
        return "already"
    done = db.q1("SELECT COUNT(*) c FROM tag_votes WHERE voter=?", uid)["c"]
    if done >= TAG_TASK_NEED and "tagtask" not in db.claimed(db.get_user(uid)):
        db.add_claimed(uid, "tagtask")
        db.add_hearts(uid, TAG_TASK_REWARD)
        return "reward"
    return "ok"


COMPLIMENT_COST = 1


def send_compliment(sender: int, target: int, text: str) -> int | str:
    """Costs the sender 1 heart. Returns the compliment id or an error code."""
    text = (text or "").strip()[:200]
    if not text or sender == target or not db.get_user(target):
        return "bad"
    now = int(time.time())
    if db.q1("SELECT 1 FROM compliments WHERE sender=? AND target=? AND ts>?", sender, target, now - 300):
        return "too_fast"
    if db.q1("SELECT COUNT(*) c FROM compliments WHERE sender=? AND ts>?", sender, now - 86400)["c"] >= 20:
        return "limit"
    if not db.spend_hearts(sender, COMPLIMENT_COST):
        return "no_hearts"
    return db.x("INSERT INTO compliments(sender,target,text,ts) VALUES(?,?,?,?)", sender, target, text, now).lastrowid


def unread_compliments(uid: int) -> list[dict]:
    rows = db.q("""SELECT c.id, c.text, c.ts, u.id AS from_id, u.name, u.photo, u.gender FROM compliments c
                   JOIN users u ON u.id=c.sender WHERE c.target=? AND c.read=0 ORDER BY c.id LIMIT 20""", uid)
    return [dict(r) for r in rows]


def collect_vip_smiles(uid: int) -> bool:
    """A VIP can collect smiles once a day (shown in the VIP dialog)."""
    u = db.get_user(uid)
    key = "vipsmile:" + db.today()
    if not db.is_vip(u) or key in db.claimed(u):
        return False
    db.add_claimed(uid, key)
    db.x("UPDATE users SET smiles=smiles+? WHERE id=?", VIP_SMILES, uid)
    return True


def read_compliment(uid: int, cid: int) -> bool:
    """Receiver opens a compliment: +1 heart, once."""
    cur = db.x("UPDATE compliments SET read=1 WHERE id=? AND target=? AND read=0", cid, uid)
    if cur.rowcount != 1:
        return False
    db.add_hearts(uid, COMPLIMENT_COST)
    db.x("UPDATE users SET smiles=smiles+1 WHERE id=?", uid)
    return True


def age_from_birth(birth: str) -> int:
    try:
        b = date.fromisoformat(birth)
    except ValueError:
        return 0
    t = date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


_TOP: dict[str, tuple[float, list]] = {}
TOP_TTL = 20  # seconds the shared top-20 lists are cached


PERIOD_DAYS = {"day": 1, "week": 7, "month": 30}
_TOPP: dict[tuple, tuple[float, object]] = {}


def _top_period(field: str, uid: int, period: str, limit: int) -> dict:
    """Day / week / month list from the per-day counters (stats_daily); shared lists are cached for TOP_TTL seconds."""
    col = {"kisses": "kisses", "gifts": "gifts", "tracks": "tracks"}[field]
    since = (date.today() - timedelta(days=PERIOD_DAYS[period] - 1)).isoformat()
    hit = _TOPP.get((field, period))
    if hit and time.time() - hit[0] < TOP_TTL and hit[1][0] == since:
        rows = hit[1][1]
    else:
        rows = [{"id": r["id"], "name": r["name"], "photo": r["photo"], "vip_until": r["vip_until"], "v": r["v"]} for r in db.q(
            f"""SELECT u.id,u.name,u.photo,u.vip_until,SUM(s.{col}) AS v FROM stats_daily s JOIN users u ON u.id=s.uid
                WHERE s.day>=? GROUP BY s.uid HAVING v>0 ORDER BY v DESC, s.uid LIMIT ?""", since, limit)]
        _TOPP[(field, period)] = (time.time(), (since, rows))
    me = db.q1(f"SELECT COALESCE(SUM({col}),0) AS v FROM stats_daily WHERE uid=? AND day>=?", uid, since)["v"]
    rank = db.q1(f"SELECT COUNT(*)+1 AS r FROM (SELECT uid FROM stats_daily WHERE day>=? GROUP BY uid HAVING SUM({col})>?)", since, me)["r"] if me else 0
    return {"rows": [{"id": r["id"], "name": r["name"], "photo": r["photo"], "vip": r["vip_until"] > time.time(), "v": r["v"]} for r in rows],
            "rank": rank, "mine": me, "period": period}


def top(field: str, uid: int, limit: int = 20, period: str = "all") -> dict:
    if field == "court":  # biggest courtship price received
        rows = db.q("""SELECT u.id,u.name,u.photo,u.vip_until,c.price AS v FROM courtship c JOIN users u ON u.id=c.target
                       ORDER BY c.price DESC, u.id LIMIT ?""", limit)
        mine = db.q1("SELECT price FROM courtship WHERE target=?", uid)
        rank = db.q1("SELECT COUNT(*)+1 AS r FROM courtship WHERE price > ?", mine["price"] if mine else 0)["r"]
        return {"rows": [{"id": r["id"], "name": r["name"], "photo": r["photo"], "vip": r["vip_until"] > time.time(), "v": r["v"]} for r in rows],
                "rank": rank, "mine": mine["price"] if mine else 0}
    if period in PERIOD_DAYS and field in ("kisses", "gifts", "tracks"):
        return _top_period(field, uid, period, limit)
    col = {"kisses": "kisses", "gifts": "gifts_received", "hearts": "hearts", "tracks": "tracks"}[field]
    hit = _TOP.get(field)
    if hit and time.time() - hit[0] < TOP_TTL:   # the top list is shared by everybody: compute it at most once per TTL
        rows = hit[1]
    else:
        rows = [{"id": r["id"], "name": r["name"], "photo": r["photo"], "vip_until": r["vip_until"], "v": r["v"]} for r in
                db.q(f"SELECT id,name,photo,vip_until,{col} AS v FROM users ORDER BY {col} DESC, id LIMIT ?", limit)]
        _TOP[field] = (time.time(), rows)
    mine = db.get_user(uid)[col]
    rank = db.q1(f"SELECT COUNT(*)+1 AS r FROM users WHERE {col} > ?", mine)["r"]
    return {
        "rows": [{"id": r["id"], "name": r["name"], "photo": r["photo"], "vip": r["vip_until"] > time.time(), "v": r["v"]} for r in rows],
        "rank": rank, "mine": mine,
    }

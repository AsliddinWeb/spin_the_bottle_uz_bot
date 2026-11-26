"""Hearts economy: profile payload, daily bonus, wheel, shop, purchases."""
import bisect
import random
import time
from datetime import date, timedelta

from . import config, db, events, league, medals
from .catalog import (CHANCE_PACKS, CHANCE_PRICE, DAILY, ITEMS, PACKS, TAG_TASK_NEED, TAG_TASK_REWARD, TAGS, rank_of, VIP_DAYS, VIP_SMILES, WHEEL, dj_level)


def daily_info(u) -> dict:
    today = date.today()
    last = u["last_daily"]
    yesterday = (today - timedelta(days=1)).isoformat()
    available = last != today.isoformat()
    streak = u["streak"] if last in (today.isoformat(), yesterday) else 0
    day = streak % len(DAILY) if available else (streak - 1) % len(DAILY)
    return {"available": available, "day": day, "streak": streak}


def daily_tasks_info(uid: int) -> list:
    """Today's 3 tasks (same for the whole day, different per player): progress comes from stats_daily, claims from daily_tasks."""
    day = db.today()
    ids = random.Random(f"{uid}:{day}").sample(config.DAILY_TASKS, 3)
    row = db.q1("SELECT * FROM stats_daily WHERE day=? AND uid=?", day, uid)
    got = {r["task"] for r in db.q("SELECT task FROM daily_tasks WHERE day=? AND uid=?", day, uid)}
    return [{"id": i, "goal": g, "n": min(g, (row[col] or 0) if row else 0), "reward": r, "claimed": i in got} for i, col, g, r in ids]


def claim_daily_task(uid: int, key: str) -> bool:
    t = next((x for x in daily_tasks_info(uid) if x["id"] == key), None)
    if not t or t["claimed"] or t["n"] < t["goal"]:
        return False
    db.x("INSERT OR IGNORE INTO daily_tasks(day,uid,task,ts) VALUES(?,?,?,?)", db.today(), uid, key, int(time.time()))
    db.add_hearts(uid, t["reward"])
    return True


def check_referral(uid: int) -> dict | None:
    """Pays the inviter (and the friend) once the invited player has REF_KISSES kisses with at least REF_MIN_PARTNERS different people.
    Idempotent (paid flag), capped per inviter per day. Returns the payout or None."""
    r = db.q1("SELECT inviter FROM referrals WHERE invited=? AND paid=0", uid)
    if not r:
        return None
    u = db.get_user(uid)
    if not u or u["kisses"] < config.REF_KISSES:
        return None
    partners = db.q1("SELECT COUNT(*) c FROM (SELECT hi AS p FROM pair_kisses WHERE lo=? UNION SELECT lo FROM pair_kisses WHERE hi=?)", uid, uid)["c"]
    if partners < config.REF_MIN_PARTNERS:
        return None
    inviter = r["inviter"]
    midnight = int(time.mktime(date.today().timetuple()))
    if db.q1("SELECT COUNT(*) c FROM referrals WHERE inviter=? AND paid=1 AND ts>=?", inviter, midnight)["c"] >= config.REF_DAILY_CAP:
        return None
    if db.x("UPDATE referrals SET paid=1, ts=? WHERE invited=? AND paid=0", int(time.time()), uid).rowcount != 1:
        return None
    hearts = config.REF_REWARD_PREMIUM if u["premium"] else config.REF_REWARD
    db.add_hearts(inviter, hearts)
    db.add_hearts(uid, config.REF_FRIEND_BONUS)
    from . import moderation
    moderation.audit(0, "ref_paid", inviter, f"friend #{uid} +{hearts} (premium={bool(u['premium'])})")
    return {"inviter": inviter, "friend": uid, "name": u["name"], "hearts": hearts, "friend_bonus": config.REF_FRIEND_BONUS}


def starter_info(u) -> list:
    """First-session tasks (spin, kiss, gift): done when the stat is >= 1; the list disappears once everything is claimed."""
    cl = db.claimed(u)
    items = [{"id": k, "done": u[stat] >= 1, "claimed": k in cl, "reward": r} for k, stat, r in config.STARTER]
    return [] if all(i["claimed"] for i in items) else items


def claim_starter(uid: int, key: str) -> bool:
    u = db.get_user(uid)
    row = next((x for x in config.STARTER if x[0] == key), None)
    if not row or key in db.claimed(u) or u[row[1]] < 1:
        return False
    db.add_claimed(uid, key)
    db.add_hearts(uid, row[2])
    return True


def me_payload(uid: int) -> dict:
    u = db.get_user(uid)
    return {
        "id": uid, "name": u["name"], "age": u["age"], "birth": u["birth"], "gender": u["gender"], "photo": u["photo"],
        "lang": u["lang"], "hearts": u["hearts"], "smiles": u["smiles"], "chances": u["chances"], "kisses": u["kisses"],
        "gifts_sent": u["gifts_sent"], "gifts_received": u["gifts_received"], "spins": u["spins"],
        "msgs": u["msgs"], "streak": u["streak"], "vip": db.is_vip(u), "top": uid in top10_ids(), "rank": rank_of(u["kisses"]), "vip_until": u["vip_until"],
        "frame": u["frame"], "bottle": u["bottle"], "inv": db.inv(uid),
        "daily": daily_info(u), "starter": starter_info(u), "dtasks": daily_tasks_info(uid), "league": league.info(uid), "medals": medals.progress(uid, u), "event": events.public(u["lang"]), "claimed": db.claimed(u), "notify": bool(u["notify"]),
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
    medals.inc(uid, "wheel")
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
    if it["kind"] not in ("booster", "choice", "league") and have and have["qty"] > 0:
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
    if cur.rowcount == 1:
        medals.inc(uid, "boosters")
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
    stats = rating_values(uid, u)
    gifts = [{"emoji": r["emoji"], "n": r["c"]} for r in db.q(
        "SELECT emoji, COUNT(*) c FROM gifts_log WHERE target=? GROUP BY emoji ORDER BY c DESC, MAX(id) DESC LIMIT 40", uid)]
    recent = [{"emoji": r["emoji"], "name": r["name"], "photo": r["photo"]} for r in db.q(
        """SELECT g.emoji, s.name, s.photo FROM gifts_log g JOIN users s ON s.id=g.sender
           WHERE g.target=? ORDER BY g.id DESC LIMIT 6""", uid)]
    return {
        "id": uid, "name": u["name"], "age": u["age"], "gender": u["gender"], "photo": u["photo"],
        "gifts": gifts, "recent": recent, "gifts_sent": u["gifts_sent"],
        "vip": db.is_vip(u), "top": uid in top10_ids(), "rank": rank_of(u["kisses"]), "frame": u["frame"], "kisses": u["kisses"], "tracks": u["tracks"], "dj": dj_level(u["tracks"]),
        "gifts_received": u["gifts_received"],
        "trophies": {str(r["place"]): r["c"] for r in db.q("SELECT place, COUNT(*) c FROM weekly_awards WHERE uid=? AND place>0 GROUP BY place", uid)},
        "ach": [r["ach"] for r in db.q("SELECT ach FROM achievements WHERE user_id=?", uid)],
        "suitor": dict(id=court["suitor"], name=court["name"], photo=court["photo"], price=court["price"]) if court else None,
        "stats": stats, "ranks": {k: rating_rank(k, v) for k, v in stats.items()},
        "court_next": stats["dear"] + 1,   # what it costs to take over (or, for the courted player, to refuse)
    }


def court(suitor: int, target: int) -> str | int:
    """Pay to become target's suitor (price = current + 1). The hearts are burnt: nobody receives them, so courting cannot be used
    to move hearts between accounts. Returns the new price or an error code."""
    if suitor == target or not db.get_user(target):
        return "bad_target"
    cur = db.q1("SELECT * FROM courtship WHERE target=?", target)
    if cur and cur["suitor"] == suitor:
        return "already"
    price = (cur["price"] + 1) if cur else 1
    if not db.spend_hearts(suitor, price):
        return "no_hearts"
    db.x("INSERT OR REPLACE INTO courtship(target,suitor,price,ts,seen) VALUES(?,?,?,?,0)", target, suitor, price, int(time.time()))
    courtship_changed()
    return price


def decline_court(uid: int) -> int | str:
    """The courted player turns the suitor away by paying one heart more than the suitor did (as on the original). The paid hearts are
    burnt, the player's price becomes that amount and the next courtship costs one more. Returns the amount paid or an error code."""
    cur = db.q1("SELECT * FROM courtship WHERE target=? AND suitor>0", uid)
    if not cur:
        return "no_suitor"
    cost = cur["price"] + 1
    if not db.spend_hearts(uid, cost):
        return "no_hearts"
    db.x("UPDATE courtship SET suitor=0, price=?, ts=?, seen=1 WHERE target=?", cost, int(time.time()), uid)
    courtship_changed()
    return cost


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
    medals.inc(uid, "tags")
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


# ---------------------------------------------------------------- ratings (the original's five)
RATINGS = ("kisses", "dj", "dear", "influence", "emotion")
USER_COL = {"kisses": "kisses", "dj": "dj", "emotion": "emo"}          # ratings kept in a column of `users` (and per day)
PERIOD_DAYS = {"day": 1, "week": 7, "month": 30}                       # only the column ratings have periods
TOP_TTL = 20  # seconds the shared top-20 lists are cached
RANK_TTL = 300
_TOP: dict[str, tuple[float, list]] = {}
_TOPP: dict[tuple, tuple[float, object]] = {}
_TOP10: tuple[float, frozenset] = (0.0, frozenset())
_RANK: dict[tuple, tuple[float, int]] = {}
_INFL: tuple[float, list] = (0.0, [])


def courtship_changed() -> None:
    """Courting is rare and costs hearts: the two courtship lists show it at once instead of waiting for the cache."""
    global _INFL
    _TOP.pop("dear", None); _TOP.pop("influence", None); _INFL = (0.0, [])
    for k in [k for k in _RANK if k[0] in ("dear", "influence")]:
        del _RANK[k]


def _people(rows) -> list[dict]:
    return [{"id": r["id"], "name": r["name"], "photo": r["photo"], "vip": r["vip_until"] > time.time(), "v": r["v"]} for r in rows]


def _influence() -> list[int]:
    """Every suitor's sum of running courtships, largest first (shared, refreshed once a minute; negated for bisect)."""
    global _INFL
    if time.time() - _INFL[0] > RANK_TTL:
        _INFL = (time.time(), sorted(-r["v"] for r in db.q("SELECT SUM(price) AS v FROM courtship WHERE suitor>0 GROUP BY suitor")))
    return _INFL[1]


def rating_values(uid: int, u=None) -> dict:
    u = u or db.get_user(uid)
    dear = db.q1("SELECT price FROM courtship WHERE target=?", uid)
    infl = db.q1("SELECT COALESCE(SUM(price),0) AS v FROM courtship WHERE suitor=?", uid)
    return {"kisses": u["kisses"], "dj": u["dj"], "dear": dear["price"] if dear else 0, "influence": infl["v"], "emotion": u["emo"]}


def rating_rank(kind: str, value: int) -> int:
    """All-time place for a number of points (0 = no points, no place). Cached per (rating, points) for RANK_TTL seconds."""
    if value <= 0:
        return 0
    hit = _RANK.get((kind, value))
    if hit and time.time() - hit[0] < RANK_TTL:
        return hit[1]
    if kind == "dear":
        rank = db.q1("SELECT COUNT(*)+1 AS r FROM courtship WHERE price>?", value)["r"]
    elif kind == "influence":
        rank = bisect.bisect_left(_influence(), -value) + 1
    else:
        col = USER_COL[kind]
        rank = db.q1(f"SELECT COUNT(*)+1 AS r FROM users WHERE {col}>?", value)["r"]
    if len(_RANK) > 20000:
        _RANK.clear()
    _RANK[(kind, value)] = (time.time(), rank)
    return rank


def _top_all(kind: str, limit: int = 20) -> list[dict]:
    hit = _TOP.get(kind)
    if hit and time.time() - hit[0] < TOP_TTL:   # the list is shared by everybody: computed at most once per TTL
        return hit[1]
    if kind == "dear":
        rows = db.q("""SELECT u.id,u.name,u.photo,u.vip_until,c.price AS v FROM courtship c JOIN users u ON u.id=c.target
                       ORDER BY c.price DESC, c.target LIMIT ?""", limit)
    elif kind == "influence":
        rows = db.q("""SELECT u.id,u.name,u.photo,u.vip_until,t.v FROM (SELECT suitor, SUM(price) AS v FROM courtship WHERE suitor>0
                       GROUP BY suitor ORDER BY v DESC, suitor LIMIT ?) t JOIN users u ON u.id=t.suitor ORDER BY t.v DESC, u.id""", limit)
    else:
        col = USER_COL[kind]
        rows = db.q(f"SELECT id,name,photo,vip_until,{col} AS v FROM users WHERE {col}>0 ORDER BY {col} DESC, id LIMIT ?", limit)
    out = _people(rows)
    _TOP[kind] = (time.time(), out)
    return out


def top10_ids() -> frozenset:
    """Players in the all-time top 10 of ANY rating: they wear the TOP ribbon instead of VIP (as on the original). Cached."""
    global _TOP10
    if time.time() - _TOP10[0] > TOP_TTL * 3:
        _TOP10 = (time.time(), frozenset(r["id"] for kind in RATINGS for r in _top_all(kind)[:10]))
    return _TOP10[1]


def _top_period(kind: str, uid: int, period: str, limit: int) -> dict:
    """Day / week / month list from the per-day counters (stats_daily)."""
    col = USER_COL[kind]
    since = (date.today() - timedelta(days=PERIOD_DAYS[period] - 1)).isoformat()
    hit = _TOPP.get((kind, period))
    if hit and time.time() - hit[0] < TOP_TTL and hit[1][0] == since:
        rows = hit[1][1]
    else:
        rows = _people(db.q(f"""SELECT u.id,u.name,u.photo,u.vip_until,SUM(s.{col}) AS v FROM stats_daily s JOIN users u ON u.id=s.uid
                                WHERE s.day>=? GROUP BY s.uid HAVING v>0 ORDER BY v DESC, s.uid LIMIT ?""", since, limit))
        _TOPP[(kind, period)] = (time.time(), (since, rows))
    me = db.q1(f"SELECT COALESCE(SUM({col}),0) AS v FROM stats_daily WHERE uid=? AND day>=?", uid, since)["v"]
    rank = db.q1(f"SELECT COUNT(*)+1 AS r FROM (SELECT uid FROM stats_daily WHERE day>=? GROUP BY uid HAVING SUM({col})>?)", since, me)["r"] if me else 0
    return {"rows": rows, "rank": rank, "mine": me, "period": period}


def top(kind: str, uid: int, limit: int = 20, period: str = "all") -> dict:
    if period in PERIOD_DAYS and kind in USER_COL:
        return _top_period(kind, uid, period, limit)
    mine = rating_values(uid)[kind]
    return {"rows": _top_all(kind, limit), "rank": rating_rank(kind, mine), "mine": mine}



"""Themed medals (the original has ~111 medals x 3 stars with specific conditions, e.g. "receive 50 gifts while a track plays").
Each medal watches one counter (a column of `users` or a row of `counters`) and has 3 tiers. Reaching a tier pays hearts once (medal_tiers)."""
import time

from . import db

db._db.execute("CREATE TABLE IF NOT EXISTS counters(uid INTEGER, key TEXT, n INTEGER DEFAULT 0, PRIMARY KEY(uid, key))")
db._db.execute("CREATE TABLE IF NOT EXISTS medal_tiers(uid INTEGER, medal TEXT, tier INTEGER, ts INTEGER, PRIMARY KEY(uid, medal, tier))")

USER_STATS = {"kisses", "spins", "gifts_sent", "gifts_received", "msgs", "streak", "tracks"}
REWARDS = (1, 2, 3)   # hearts for tier 1 / 2 / 3 (the original pays ❤1 for the first tier)

# id, counter or users column, three thresholds, emoji, own gift art id ("" = emoji)
MEDALS = [
    ("hit", "hit", (10, 50, 200), "🔊", ""),
    ("coffee", "coffee", (5, 25, 100), "☕", "coffee"),
    ("romantic", "flowers_s", (3, 15, 60), "🌹", "rose"),
    ("dj", "tracks", (3, 15, 60), "🎧", ""),
    ("talker", "msgs", (50, 300, 1500), "💬", ""),
    ("kisser", "kisses", (10, 100, 500), "💋", "lips"),
    ("generous", "gifts_sent", (10, 50, 250), "🎁", ""),
    ("favorite", "gifts_received", (10, 50, 250), "🌟", ""),
    ("nope", "declines", (5, 25, 100), "🙅", ""),
    ("spinner", "spins", (20, 100, 500), "🍾", ""),
    ("streak", "streak", (3, 7, 30), "🔥", ""),
    ("target", "bad_r", (3, 15, 50), "🎯", "tomato"),
    ("joker", "bad_s", (3, 15, 50), "🤡", "joker"),
    ("lucky", "wheel", (3, 20, 100), "🎰", ""),
    ("boosted", "boosters", (1, 10, 50), "⚡", ""),
    ("leaguer", "league_pts", (10, 60, 300), "🏆", "trophy"),
    ("traveler", "joins", (5, 25, 100), "🧭", ""),
    ("critic", "tags", (10, 50, 200), "📝", ""),
    ("fashion", "head_r", (3, 15, 50), "🎩", "tophat"),
    ("bartender", "drinks_s", (10, 50, 200), "🍸", "martini"),
    ("sweet", "sweets_r", (5, 25, 100), "🍰", "cake"),
    ("bomber", "bomb_s", (1, 5, 20), "💣", "bomb"),
    ("zoo", "animals_r", (3, 15, 50), "🐸", "frog"),
    ("royal", "royal_r", (1, 5, 20), "👑", "crown1"),
    ("matchmaker", "ring_s", (1, 5, 20), "💍", "ring"),
]
KEYS = {m[1] for m in MEDALS}

# gift groups for the counters
DRINKS = {"milk", "tea", "coffee", "cola", "wine", "whisky", "cocktail", "martini", "champagne", "smoothie"}
FLOWERS = {"rose", "tulip", "bouquet", "blackrose"}
SWEETS = {"cake", "candy", "icecream", "strawberry"}
ANIMALS = {"frog", "duck", "pig", "penguin"}
ROYAL = {"crown1", "crown2", "king", "queen", "batcrown"}
RINGS = {"ring", "diamondring"}
COFFEE = {"tea", "coffee"}


def inc(uid: int, key: str, n: int = 1) -> None:
    if n > 0 and key in KEYS:
        db.x("INSERT INTO counters(uid,key,n) VALUES(?,?,?) ON CONFLICT(uid,key) DO UPDATE SET n=n+?", uid, key, n, n)


def gift_sent(uid: int, gift: str, kind: str) -> None:
    if gift in DRINKS: inc(uid, "drinks_s")
    if gift in FLOWERS: inc(uid, "flowers_s")
    if gift in RINGS: inc(uid, "ring_s")
    if gift == "bomb": inc(uid, "bomb_s")
    if kind == "bad": inc(uid, "bad_s")


def gift_received(uid: int, gift: str, kind: str, head: bool, music_playing: bool) -> None:
    if gift in COFFEE: inc(uid, "coffee")
    if gift in SWEETS: inc(uid, "sweets_r")
    if gift in ANIMALS: inc(uid, "animals_r")
    if gift in ROYAL: inc(uid, "royal_r")
    if head: inc(uid, "head_r")
    if kind == "bad": inc(uid, "bad_r")
    if music_playing: inc(uid, "hit")


def values(uid: int, u=None) -> dict:
    u = u or db.get_user(uid)
    c = {r["key"]: r["n"] for r in db.q("SELECT key, n FROM counters WHERE uid=?", uid)}
    return {key: (u[key] if key in USER_STATS else c.get(key, 0)) for key in {m[1] for m in MEDALS}}


def tier_of(value: int, tiers: tuple) -> int:
    return sum(1 for t in tiers if value >= t)


def progress(uid: int, u=None) -> dict:
    """{medal id: [value, tiers reached]} for the player's window."""
    v = values(uid, u)
    return {mid: [v[key], tier_of(v[key], tiers)] for mid, key, tiers, _, _ in MEDALS}


def check(uid: int) -> list[dict]:
    """Pay and return medal tiers reached since the last check."""
    v = values(uid)
    have = {(r["medal"], r["tier"]) for r in db.q("SELECT medal, tier FROM medal_tiers WHERE uid=?", uid)}
    out = []
    for mid, key, tiers, _, _ in MEDALS:
        for t in range(1, tier_of(v[key], tiers) + 1):
            if (mid, t) in have:
                continue
            if db.x("INSERT OR IGNORE INTO medal_tiers(uid,medal,tier,ts) VALUES(?,?,?,?)", uid, mid, t, int(time.time())).rowcount != 1:
                continue
            db.add_hearts(uid, REWARDS[t - 1])
            out.append({"id": mid, "tier": t, "reward": REWARDS[t - 1]})
    return out


def public() -> list[dict]:
    return [{"id": mid, "key": key, "tiers": list(tiers), "emoji": emoji, "art": art, "rewards": list(REWARDS)} for mid, key, tiers, emoji, art in MEDALS]

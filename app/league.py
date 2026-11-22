"""Leagues ("Лиги"): a weekly competition. Every kiss you receive is worth league points, but only up to a weekly limit
(the original calls it «лимит на входящие поцелуи»). Boosters: x2 points for 5 minutes, +10 to the limit, +5 points that ignore the limit.
Top 3 at the end of the week get booster prizes. Everything is idempotent / restart-safe (points and awards live in SQLite)."""
import time
from datetime import date, timedelta

from . import config, db, medals, moderation

db._db.execute("CREATE TABLE IF NOT EXISTS league_points(week TEXT, uid INTEGER, pts INTEGER DEFAULT 0, PRIMARY KEY(week, uid))")
db._db.execute("CREATE INDEX IF NOT EXISTS league_points_top ON league_points(week, pts DESC)")
db._db.execute("CREATE TABLE IF NOT EXISTS league_state(uid INTEGER PRIMARY KEY, week TEXT, x2_until INTEGER DEFAULT 0, extra INTEGER DEFAULT 0)")
db._db.execute("CREATE TABLE IF NOT EXISTS league_awards(week TEXT, place INTEGER, uid INTEGER, prize TEXT, ts INTEGER, PRIMARY KEY(week, place))")

BOOSTERS = ("league_x2", "league_limit", "league_plus5")


def week_key(d: date | None = None) -> str:
    d = d or date.today()
    return (d - timedelta(days=d.weekday())).isoformat()


def week_end(d: date | None = None) -> int:
    """Unix time of the next Monday 00:00 (server local time)."""
    d = d or date.today()
    nxt = d - timedelta(days=d.weekday()) + timedelta(days=7)
    return int(time.mktime(nxt.timetuple()))


def _state(uid: int, week: str) -> dict:
    r = db.q1("SELECT * FROM league_state WHERE uid=?", uid)
    if not r or r["week"] != week:   # the limit bonus belongs to one week; x2 may carry over a midnight
        return {"x2_until": r["x2_until"] if r else 0, "extra": 0}
    return {"x2_until": r["x2_until"], "extra": r["extra"]}


def _save(uid: int, week: str, x2_until: int, extra: int) -> None:
    db.x("INSERT INTO league_state(uid,week,x2_until,extra) VALUES(?,?,?,?) ON CONFLICT(uid) DO UPDATE SET week=?, x2_until=?, extra=?", uid, week, x2_until, extra, week, x2_until, extra)


def points(uid: int, week: str | None = None) -> int:
    r = db.q1("SELECT pts FROM league_points WHERE week=? AND uid=?", week or week_key(), uid)
    return r["pts"] if r else 0


def limit(uid: int) -> int:
    return config.LEAGUE_LIMIT + _state(uid, week_key())["extra"]


def add_points(uid: int, n: int = 1, *, boost: bool = True, ignore_limit: bool = False) -> int:
    """Adds league points; returns what was actually added (the weekly limit caps the sum, x2 doubles `n` while active)."""
    if n <= 0:
        return 0
    week = week_key(); st = _state(uid, week); have = points(uid, week)
    if boost and st["x2_until"] > time.time():
        n *= 2
    if not ignore_limit:
        n = max(0, min(n, config.LEAGUE_LIMIT + st["extra"] - have))
    if n:
        db.x("INSERT INTO league_points(week,uid,pts) VALUES(?,?,?) ON CONFLICT(week,uid) DO UPDATE SET pts=pts+?", week, uid, n, n)
        medals.inc(uid, "league_pts", n)
    return n


def use(uid: int, item: str) -> bool:
    """Spend one league booster from the inventory."""
    if item not in BOOSTERS:
        return False
    if db.x("UPDATE inventory SET qty=qty-1 WHERE user_id=? AND item=? AND qty>0", uid, item).rowcount != 1:
        return False
    medals.inc(uid, "boosters")
    week = week_key(); st = _state(uid, week)
    if item == "league_x2":
        _save(uid, week, max(int(time.time()), st["x2_until"]) + config.LEAGUE_X2_SEC, st["extra"])
    elif item == "league_limit":
        _save(uid, week, st["x2_until"], st["extra"] + config.LEAGUE_LIMIT_PLUS)
    else:
        add_points(uid, config.LEAGUE_PLUS_PTS, boost=False, ignore_limit=True)
    return True


def info(uid: int) -> dict:
    week = week_key(); st = _state(uid, week); pts = points(uid, week)
    rank = 0
    if pts:
        rank = db.q1("SELECT COUNT(*) AS c FROM league_points WHERE week=? AND pts>?", week, pts)["c"] + 1
    return {"pts": pts, "limit": config.LEAGUE_LIMIT + st["extra"], "rank": rank, "x2_left": max(0, int(st["x2_until"] - time.time())), "ends": week_end()}


def top(n: int = 20) -> list[dict]:
    rows = db.q("""SELECT p.uid, p.pts, u.name, u.photo FROM league_points p JOIN users u ON u.id=p.uid
                   WHERE p.week=? AND p.pts>0 ORDER BY p.pts DESC, p.uid LIMIT ?""", week_key(), n)
    return [{"uid": r["uid"], "name": r["name"], "photo": r["photo"], "pts": r["pts"]} for r in rows]


def award_last_week(today: date | None = None) -> list[dict]:
    """Booster prizes for the top 3 of the previous week; paid once per week/place."""
    today = today or date.today()
    week = week_key(today - timedelta(days=7))
    if db.q1("SELECT 1 FROM league_awards WHERE week=? LIMIT 1", week):
        return []
    rows = db.q("SELECT uid, pts FROM league_points WHERE week=? AND pts>=? ORDER BY pts DESC, uid LIMIT 3", week, config.LEAGUE_MIN)
    out = []
    for place, r in enumerate(rows, 1):
        prize = config.LEAGUE_PRIZES[place]
        if db.x("INSERT OR IGNORE INTO league_awards(week,place,uid,prize,ts) VALUES(?,?,?,?,?)", week, place, r["uid"], ",".join(f"{k}:{v}" for k, v in prize.items()), int(time.time())).rowcount != 1:
            continue
        for item, qty in prize.items():
            db.inv_add(r["uid"], item, qty)
        moderation.audit(0, "league_award", r["uid"], f"{week} #{place} {prize}")
        out.append({"week": week, "place": place, "uid": r["uid"], "pts": r["pts"], "prize": prize})
    if not out:
        db.x("INSERT OR IGNORE INTO league_awards(week,place,uid,prize,ts) VALUES(?,0,0,'',?)", week, int(time.time()))
    return out

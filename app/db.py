import json
import sqlite3
import time
from datetime import date

from . import config
from .catalog import ACHIEVEMENTS, DEFAULT_BOTTLE

_db = sqlite3.connect(config.DB_PATH, check_same_thread=False, isolation_level=None)
_db.row_factory = sqlite3.Row
_db.execute("PRAGMA journal_mode=WAL")

_db.executescript(
    """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT, age INTEGER DEFAULT 0, gender TEXT DEFAULT '',
  photo TEXT DEFAULT '', lang TEXT DEFAULT 'uz', hearts INTEGER DEFAULT 0,
  chances INTEGER DEFAULT 0, kisses INTEGER DEFAULT 0, gifts_sent INTEGER DEFAULT 0,
  gifts_received INTEGER DEFAULT 0, spins INTEGER DEFAULT 0, msgs INTEGER DEFAULT 0,
  streak INTEGER DEFAULT 0, last_daily TEXT DEFAULT '', vip_until INTEGER DEFAULT 0,
  frame TEXT DEFAULT '', bottle TEXT DEFAULT 'bottle_green', ref_by INTEGER DEFAULT 0,
  claimed TEXT DEFAULT '[]', created INTEGER
);
CREATE TABLE IF NOT EXISTS inventory(
  user_id INTEGER, item TEXT, qty INTEGER DEFAULT 0, armed INTEGER DEFAULT 0,
  PRIMARY KEY(user_id, item)
);
CREATE TABLE IF NOT EXISTS achievements(user_id INTEGER, ach TEXT, ts INTEGER, PRIMARY KEY(user_id, ach));
CREATE TABLE IF NOT EXISTS recent_tables(user_id INTEGER, table_id INTEGER, ts INTEGER, PRIMARY KEY(user_id, table_id));
CREATE TABLE IF NOT EXISTS payments(charge_id TEXT PRIMARY KEY, user_id INTEGER, payload TEXT, stars INTEGER, ts INTEGER);
CREATE TABLE IF NOT EXISTS wheel_log(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, kind TEXT, amount INTEGER, ts INTEGER);
CREATE TABLE IF NOT EXISTS referrals(inviter INTEGER, invited INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS courtship(target INTEGER PRIMARY KEY, suitor INTEGER, price INTEGER, ts INTEGER, seen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, reporter INTEGER, target INTEGER, ts INTEGER);
"""
)


for _col in ("tracks INTEGER DEFAULT 0", "bot_started INTEGER DEFAULT 0", "notify INTEGER DEFAULT 1",
             "last_seen INTEGER DEFAULT 0", "last_reminder TEXT DEFAULT ''"):
    try:  # migrations for DBs created before these columns existed
        _db.execute(f"ALTER TABLE users ADD COLUMN {_col}")
    except sqlite3.OperationalError:
        pass
_db.executescript("""
CREATE TABLE IF NOT EXISTS gifts_log(id INTEGER PRIMARY KEY AUTOINCREMENT, sender INTEGER, target INTEGER, gift TEXT, emoji TEXT, ts INTEGER);
CREATE INDEX IF NOT EXISTS gifts_log_target ON gifts_log(target, id);
CREATE TABLE IF NOT EXISTS worn(user_id INTEGER, slot TEXT, emoji TEXT, ts INTEGER, PRIMARY KEY(user_id, slot));
""")
_db.execute("CREATE TABLE IF NOT EXISTS tracks_log(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, vid TEXT, title TEXT, ts INTEGER)")
_db.execute("CREATE INDEX IF NOT EXISTS tracks_log_vid ON tracks_log(vid)")
for _col in ("birth TEXT DEFAULT ''", "smiles INTEGER DEFAULT 3", "role TEXT DEFAULT ''", "username TEXT DEFAULT ''", "warns INTEGER DEFAULT 0", "kick_free_ts INTEGER DEFAULT 0"):
    try:
        _db.execute(f"ALTER TABLE users ADD COLUMN {_col}")
    except sqlite3.OperationalError:
        pass
_db.execute("CREATE TABLE IF NOT EXISTS tag_votes(voter INTEGER, target INTEGER, tag TEXT, ts INTEGER, PRIMARY KEY(voter, target))")
_db.executescript("""
CREATE TABLE IF NOT EXISTS sanctions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT, until INTEGER,
  reason TEXT, by_id INTEGER, ts INTEGER, active INTEGER DEFAULT 1);
CREATE INDEX IF NOT EXISTS sanctions_user ON sanctions(user_id, kind, active);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, actor INTEGER, action TEXT, target INTEGER, detail TEXT);
CREATE INDEX IF NOT EXISTS audit_target ON audit(target, id);
""")
for _col in ("reason TEXT DEFAULT ''", "status TEXT DEFAULT 'new'", "handler INTEGER DEFAULT 0", "outcome TEXT DEFAULT ''",
             "handled_ts INTEGER DEFAULT 0", "snapshot TEXT DEFAULT ''"):
    try:
        _db.execute(f"ALTER TABLE reports ADD COLUMN {_col}")
    except sqlite3.OperationalError:
        pass
_db.execute("""CREATE TABLE IF NOT EXISTS compliments(
  id INTEGER PRIMARY KEY AUTOINCREMENT, sender INTEGER, target INTEGER, text TEXT, ts INTEGER, read INTEGER DEFAULT 0)""")


from .catalog import OLD_ACH_IDS  # noqa: E402

for _old, _new in OLD_ACH_IDS.items():  # keep already unlocked achievements under their new ids
    _db.execute("UPDATE OR IGNORE achievements SET ach=? WHERE ach=?", (_new, _old))
    _db.execute("DELETE FROM achievements WHERE ach=?", (_old,))


def q(sql: str, *args) -> list[sqlite3.Row]:
    return _db.execute(sql, args).fetchall()


def q1(sql: str, *args):
    return _db.execute(sql, args).fetchone()


def x(sql: str, *args) -> sqlite3.Cursor:
    return _db.execute(sql, args)


def touch_seen(uid: int) -> None:
    x("UPDATE users SET last_seen=? WHERE id=?", int(time.time()), uid)


def get_user(uid: int):
    return q1("SELECT * FROM users WHERE id=?", uid)


def ensure_user(uid: int, name: str, photo: str = "", lang: str = "uz", ref_by: int = 0, username: str = ""):
    """Create the user if new. Returns (row, created)."""
    u = get_user(uid)
    if u:
        if username and username != u["username"]:
            x("UPDATE users SET username=? WHERE id=?", username, uid)
        if photo and photo != u["photo"] and not u["photo"].startswith("/uploads/"):  # keep a custom upload
            x("UPDATE users SET photo=? WHERE id=?", photo, uid)
        return get_user(uid), False
    x(
        "INSERT INTO users(id,name,photo,lang,hearts,bottle,created,username) VALUES(?,?,?,?,?,?,?,?)",
        uid, name[:24] or "Player", photo, lang, config.START_HEARTS, DEFAULT_BOTTLE, int(time.time()), username,
    )
    x("INSERT OR IGNORE INTO inventory(user_id,item,qty) VALUES(?,?,1)", uid, DEFAULT_BOTTLE)
    return get_user(uid), True


def add_hearts(uid: int, n: int) -> None:
    x("UPDATE users SET hearts=MAX(0,hearts+?) WHERE id=?", n, uid)


def spend_hearts(uid: int, n: int) -> bool:
    """Atomic: returns False if not enough hearts."""
    cur = x("UPDATE users SET hearts=hearts-? WHERE id=? AND hearts>=?", n, uid, n)
    return cur.rowcount == 1


def inc(uid: int, field: str, n: int = 1) -> None:
    assert field in {"kisses", "gifts_sent", "gifts_received", "spins", "msgs", "chances", "streak", "tracks"}
    x(f"UPDATE users SET {field}={field}+? WHERE id=?", n, uid)


def is_vip(u) -> bool:
    return u["vip_until"] > time.time()


def inv(uid: int) -> dict:
    return {r["item"]: {"qty": r["qty"], "armed": r["armed"]} for r in q("SELECT * FROM inventory WHERE user_id=?", uid)}


def inv_add(uid: int, item: str, qty: int = 1) -> None:
    x(
        "INSERT INTO inventory(user_id,item,qty) VALUES(?,?,?) "
        "ON CONFLICT(user_id,item) DO UPDATE SET qty=qty+?",
        uid, item, qty, qty,
    )


def consume_armed(uid: int, item: str) -> bool:
    cur = x("UPDATE inventory SET armed=armed-1 WHERE user_id=? AND item=? AND armed>0", uid, item)
    return cur.rowcount == 1


def check_achievements(uid: int) -> list[str]:
    """Unlock any newly reached achievements, grant hearts, return new ids."""
    u = get_user(uid)
    have = {r["ach"] for r in q("SELECT ach FROM achievements WHERE user_id=?", uid)}
    new = []
    for aid, stat, need, reward in ACHIEVEMENTS:
        if aid in have or u[stat] < need:
            continue
        x("INSERT OR IGNORE INTO achievements VALUES(?,?,?)", uid, aid, int(time.time()))
        add_hearts(uid, reward)
        new.append(aid)
    return new


def today() -> str:
    return date.today().isoformat()


def claimed(u) -> list:
    return json.loads(u["claimed"] or "[]")


def add_claimed(uid: int, key: str) -> None:
    u = get_user(uid)
    c = claimed(u)
    if key not in c:
        c.append(key)
        x("UPDATE users SET claimed=? WHERE id=?", json.dumps(c), uid)


def touch_recent(uid: int, table_id: int) -> None:
    x("INSERT OR REPLACE INTO recent_tables VALUES(?,?,?)", uid, table_id, int(time.time()))

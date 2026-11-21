"""Roles, sanctions (ban / mute), audit log, manual balance changes, report handling.

Hierarchy: owner (ids in ADMIN_IDS) > admin > mod > player. Nobody can act on someone of equal or higher rank.
Moderators: warn, mute, kick, rename/unphoto, review reports. Admins add: ban, give/take, role "mod".
Only the owner can make admins. Every action is written to the audit table.
"""
import json
import re
import time

from . import config, db

RANK = {"": 0, "mod": 1, "admin": 2, "owner": 3}
DUR_RE = re.compile(r"^(\d+)([mhd])$")
REASONS = ["abuse", "spam", "nsfw", "fraud", "age"]
AUTO_MUTE_REPORTERS = 5   # distinct reporters within 24h trigger a 1h mute and an alert to staff
AUTO_MUTE_SECONDS = 3600


def role_of(uid: int) -> str:
    if uid in config.ADMIN_IDS:
        return "owner"
    u = db.get_user(uid)
    return (u["role"] if u else "") or ""


def rank(uid: int) -> int:
    return RANK.get(role_of(uid), 0)


def staff_ids(min_role: str = "mod") -> list[int]:
    ids = set(config.ADMIN_IDS)
    roles = ("mod", "admin") if min_role == "mod" else ("admin",)
    ids.update(r["id"] for r in db.q(f"SELECT id FROM users WHERE role IN ({','.join('?' * len(roles))})", *roles))
    return sorted(ids)


def parse_duration(tok: str) -> int | None:
    """'30m' / '2h' / '7d' -> seconds, 'perm' -> 0, anything else -> None (invalid)."""
    tok = tok.lower()
    if tok in ("perm", "forever", "0"):
        return 0
    m = DUR_RE.match(tok)
    if not m:
        return None
    return int(m.group(1)) * {"m": 60, "h": 3600, "d": 86400}[m.group(2)]


def human_until(until: int) -> str:
    return "∞" if not until else time.strftime("%Y-%m-%d %H:%M", time.localtime(until))


def find_user(token: str):
    """id, @username or username -> user row (or None)."""
    token = token.strip()
    if token.lstrip("-").isdigit():
        return db.get_user(int(token))
    return db.q1("SELECT * FROM users WHERE lower(username)=?", token.lstrip("@").lower())


# ---------------------------------------------------------------- audit
def audit(actor: int, action: str, target: int = 0, detail: str = "") -> None:
    db.x("INSERT INTO audit(ts,actor,action,target,detail) VALUES(?,?,?,?,?)", int(time.time()), actor, action, target, detail[:500])


def audit_rows(target: int = 0, limit: int = 15) -> list:
    if target:
        return db.q("SELECT * FROM audit WHERE target=? OR actor=? ORDER BY id DESC LIMIT ?", target, target, limit)
    return db.q("SELECT * FROM audit ORDER BY id DESC LIMIT ?", limit)


# ---------------------------------------------------------------- sanctions
def active(uid: int, kind: str):
    """Latest still-running sanction of this kind, expired ones are switched off on the way."""
    now = int(time.time())
    db.x("UPDATE sanctions SET active=0 WHERE active=1 AND until>0 AND until<=?", now)
    return db.q1("SELECT * FROM sanctions WHERE user_id=? AND kind=? AND active=1 ORDER BY id DESC LIMIT 1", uid, kind)


def can_act(actor: int, target: int) -> str | None:
    """None if allowed, otherwise an error code."""
    if actor == target:
        return "self"
    if rank(actor) <= rank(target):
        return "rank"
    return None


def sanction(actor: int, target: int, kind: str, seconds: int, reason: str) -> str | int:
    """kind: ban | mute. seconds==0 -> permanent. Returns sanction id or an error code."""
    if kind == "ban" and rank(actor) < RANK["admin"] and actor != 0:
        return "need_admin"
    if kind == "mute" and rank(actor) < RANK["mod"] and actor != 0:
        return "need_mod"
    if not db.get_user(target):
        return "no_user"
    if actor and (err := can_act(actor, target)):
        return err
    until = int(time.time()) + seconds if seconds else 0
    db.x("UPDATE sanctions SET active=0 WHERE user_id=? AND kind=? AND active=1", target, kind)  # replace the previous one
    sid = db.x("INSERT INTO sanctions(user_id,kind,until,reason,by_id,ts) VALUES(?,?,?,?,?,?)",
               target, kind, until, reason[:200], actor, int(time.time())).lastrowid
    audit(actor, kind, target, f"{human_until(until)} | {reason}")
    return sid


def lift(actor: int, target: int, kind: str) -> str | int:
    if rank(actor) < (RANK["admin"] if kind == "ban" else RANK["mod"]):
        return "need_admin" if kind == "ban" else "need_mod"
    n = db.x("UPDATE sanctions SET active=0 WHERE user_id=? AND kind=? AND active=1", target, kind).rowcount
    if n:
        audit(actor, "un" + kind, target)
    return n


def warn(actor: int, target: int, text: str) -> str | None:
    if rank(actor) < RANK["mod"]:
        return "need_mod"
    if not db.get_user(target):
        return "no_user"
    if err := can_act(actor, target):
        return err
    db.x("UPDATE users SET warns=warns+1 WHERE id=?", target)
    audit(actor, "warn", target, text)
    return None


# ---------------------------------------------------------------- balance (admin+, no limits by design)
GIVE_FIELDS = {"hearts": "hearts", "smiles": "smiles", "chances": "chances"}


def give(actor: int, target: int, what: str, n: int, reason: str) -> str | int:
    if rank(actor) < RANK["admin"]:
        return "need_admin"
    u = db.get_user(target)
    if not u:
        return "no_user"
    if what == "vip":  # n = days, negative shortens, never below now
        new = max(u["vip_until"], int(time.time())) + n * 86400 if n > 0 else max(0, u["vip_until"] + n * 86400)
        db.x("UPDATE users SET vip_until=? WHERE id=?", new, target)
    elif what in GIVE_FIELDS:
        col = GIVE_FIELDS[what]
        db.x(f"UPDATE users SET {col}=MAX(0,{col}+?) WHERE id=?", n, target)
    else:
        return "bad_what"
    audit(actor, "give", target, f"{what} {n:+d} | {reason}")
    return 0


def set_role(actor: int, target: int, role: str) -> str | None:
    if rank(actor) < RANK["owner"]:
        return "need_owner"
    if role not in ("", "mod", "admin"):
        return "bad_role"
    if target in config.ADMIN_IDS:
        return "is_owner"
    if not db.get_user(target):
        return "no_user"
    db.x("UPDATE users SET role=? WHERE id=?", role, target)
    audit(actor, "role", target, role or "none")
    return None


def rename(actor: int, target: int, name: str) -> str | None:
    if rank(actor) < RANK["mod"]:
        return "need_mod"
    if err := can_act(actor, target):
        return err
    db.x("UPDATE users SET name=? WHERE id=?", name.strip()[:24], target)
    audit(actor, "rename", target, name)
    return None


def remove_photo(actor: int, target: int) -> str | None:
    from pathlib import Path
    if rank(actor) < RANK["mod"]:
        return "need_mod"
    if err := can_act(actor, target):
        return err
    u = db.get_user(target)
    if u and u["photo"].startswith("/uploads/"):
        (config.ROOT / "uploads" / u["photo"].rsplit("/", 1)[1]).unlink(missing_ok=True)
    db.x("UPDATE users SET photo='' WHERE id=?", target)
    audit(actor, "unphoto", target)
    return None


# ---------------------------------------------------------------- reports
def add_report(reporter: int, target: int, reason: str, snapshot: dict) -> str:
    """Returns 'ok' | 'dup' | 'bad'. 'auto' means this report tripped the auto-mute."""
    if reason not in REASONS or reporter == target or not db.get_user(target):
        return "bad"
    now = int(time.time())
    if db.q1("SELECT 1 FROM reports WHERE reporter=? AND target=? AND ts>?", reporter, target, now - 86400):
        return "dup"
    db.x("INSERT INTO reports(reporter,target,ts,reason,snapshot) VALUES(?,?,?,?,?)",
         reporter, target, now, reason, json.dumps(snapshot, ensure_ascii=False)[:2000])
    n = db.q1("SELECT COUNT(DISTINCT reporter) c FROM reports WHERE target=? AND ts>? AND status!='dismissed'", target, now - 86400)["c"]
    if n >= AUTO_MUTE_REPORTERS and rank(target) == 0 and not active(target, "mute"):
        sanction(0, target, "mute", AUTO_MUTE_SECONDS, f"auto: {n} reports in 24h")
        return "auto"
    return "ok"


def next_report(after: int = 0):
    return db.q1("SELECT * FROM reports WHERE status='new' AND id>? ORDER BY id LIMIT 1", after) or \
        db.q1("SELECT * FROM reports WHERE status='new' ORDER BY id LIMIT 1")


def resolve_report(rid: int, actor: int, outcome: str) -> None:
    db.x("UPDATE reports SET status=?, handler=?, outcome=?, handled_ts=? WHERE id=?",
         "dismissed" if outcome == "dismiss" else "done", actor, outcome, int(time.time()), rid)
    audit(actor, "report_" + outcome, (db.q1("SELECT target FROM reports WHERE id=?", rid) or {"target": 0})["target"], f"#{rid}")


def user_summary(u) -> dict:
    uid = u["id"]
    ban, mute = active(uid, "ban"), active(uid, "mute")
    rep = db.q1("SELECT COUNT(*) c, COUNT(DISTINCT reporter) d FROM reports WHERE target=?", uid)
    return {
        "ban": ban, "mute": mute, "reports": rep["c"], "reporters": rep["d"],
        "warns": u["warns"], "role": role_of(uid),
    }

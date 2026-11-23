"""Taklif mukofoti: do'st 50 o'pishga (kamida 3 xil odam bilan) yetganda to'lanadi. Modul darajasida, vaqtinchalik baza."""
import os, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "ref.db"); sys.path.insert(0, ROOT)
from app import config, db, economy  # noqa: E402
fails = []; passed = 0


def ok(name, cond, info=""):
    global passed
    if cond: passed += 1
    else: fails.append(f"{name} {info}")


def user(uid, kisses=0, premium=0, hearts=0):
    db.x("INSERT INTO users(id,name,created,hearts,kisses,premium) VALUES(?,?,0,?,?,?)", uid, f"U{uid}", hearts, kisses, premium)


def partners(uid, n):
    for i in range(n):
        p = 9000 + uid * 10 + i
        db.x("INSERT OR IGNORE INTO pair_kisses(day,lo,hi,n) VALUES('2026-01-01',?,?,1)", min(uid, p), max(uid, p))


def refer(inviter, friend):
    db.x("INSERT INTO referrals(inviter,invited,paid,ts) VALUES(?,?,0,0)", inviter, friend)


user(1)
user(2, kisses=49); refer(1, 2); partners(2, 5)
ok("49 o'pish: to'lanmaydi", economy.check_referral(2) is None)
db.x("UPDATE users SET kisses=50 WHERE id=2")
db.x("DELETE FROM pair_kisses WHERE lo=2 OR hi=2"); partners(2, 2)
ok("faqat 2 xil odam: to'lanmaydi", economy.check_referral(2) is None)
partners(2, 3)
r = economy.check_referral(2)
ok("50 o'pish + 3 odam: to'lanadi", r and r["hearts"] == config.REF_REWARD and r["inviter"] == 1, r)
ok("taklif qiluvchiga ❤20", db.get_user(1)["hearts"] == 20)
ok("do'stga ❤20 bonus", db.get_user(2)["hearts"] == 20)
ok("ikkinchi marta to'lanmaydi", economy.check_referral(2) is None and db.get_user(1)["hearts"] == 20)
ok("ro'yxatsiz o'yinchi: None", economy.check_referral(1) is None)

user(3, kisses=60, premium=1); refer(1, 3); partners(3, 4)
r = economy.check_referral(3)
ok("Premium do'st: ❤50", r and r["hearts"] == config.REF_REWARD_PREMIUM and db.get_user(1)["hearts"] == 70, (r, db.get_user(1)["hearts"]))

# kunlik chegara: 10 ta to'langan, 11-chisi ertaga
db.x("DELETE FROM referrals"); db.x("UPDATE users SET hearts=0 WHERE id=1")
for i in range(config.REF_DAILY_CAP + 1):
    f = 100 + i; user(f, kisses=50); partners(f, 3); refer(1, f)
paid = [economy.check_referral(100 + i) for i in range(config.REF_DAILY_CAP + 1)]
ok("kuniga 10 ta to'lanadi", sum(1 for p in paid if p) == config.REF_DAILY_CAP, [bool(p) for p in paid])
ok("11-chisi kutadi", paid[-1] is None and db.q1("SELECT paid FROM referrals WHERE invited=?", 100 + config.REF_DAILY_CAP)["paid"] == 0)
db.x("UPDATE referrals SET ts=? WHERE paid=1", int(time.time()) - 2 * 86400)
r = economy.check_referral(100 + config.REF_DAILY_CAP)
ok("ertasi kuni to'lanadi", r and r["hearts"] == config.REF_REWARD, r)

# o'zini o'zi taklif qilish /start da rad etiladi (bot.py), bu yerda esa DB darajasida bir do'st ikki marta yozilmaydi
try:
    refer(1, 100); ok("bir do'st ikki marta yozilmaydi", False)
except Exception:
    ok("bir do'st ikki marta yozilmaydi", True)
print(f"{passed}/{passed + len(fails)} passed")
for f in fails: print("FAIL", f)

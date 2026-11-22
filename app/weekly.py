"""Weekly top: every Monday the three best kissers of the previous week (Mon-Sun) receive hearts.

award_last_week() is idempotent (one row per week/place in weekly_awards), so a restart or a second worker cannot pay twice.
"""
import asyncio
import time
from datetime import date, timedelta

from . import config, db, moderation


def last_week(today: date | None = None) -> tuple[str, str, str]:
    """(week id = Monday, first day, last day) of the previous calendar week."""
    today = today or date.today()
    mon = today - timedelta(days=today.weekday()) - timedelta(days=7)
    return mon.isoformat(), mon.isoformat(), (mon + timedelta(days=6)).isoformat()


def award_last_week(today: date | None = None) -> list[dict]:
    week, d0, d1 = last_week(today)
    if db.q1("SELECT 1 FROM weekly_awards WHERE week=? LIMIT 1", week):
        return []
    rows = db.q("""SELECT uid, SUM(kisses) AS v FROM stats_daily WHERE day>=? AND day<=? GROUP BY uid HAVING v>=?
                   ORDER BY v DESC, uid LIMIT ?""", d0, d1, config.WEEKLY_MIN, len(config.WEEKLY_REWARDS))
    out = []
    for place, r in enumerate(rows, 1):
        hearts = config.WEEKLY_REWARDS[place - 1]
        if db.x("INSERT OR IGNORE INTO weekly_awards(week,place,uid,hearts,kisses,ts) VALUES(?,?,?,?,?,?)", week, place, r["uid"], hearts, r["v"], int(time.time())).rowcount != 1:
            continue
        db.add_hearts(r["uid"], hearts)
        moderation.audit(0, "weekly_award", r["uid"], f"{week} #{place} +{hearts} ({r['v']} kisses)")
        out.append({"week": week, "place": place, "uid": r["uid"], "hearts": hearts, "kisses": r["v"]})
    if not out:   # nobody qualified: remember that the week is closed
        db.x("INSERT OR IGNORE INTO weekly_awards(week,place,uid,hearts,kisses,ts) VALUES(?,0,0,0,0,?)", week, int(time.time()))
    return out


MSG = {
    "uz": "🏆 Haftalik top: siz {p}-o'rindasiz! Mukofot: ❤{h} ({k} ta o'pish).",
    "ru": "🏆 Топ недели: вы на {p}-м месте! Награда: ❤{h} ({k} поцелуев).",
    "en": "🏆 Weekly top: you finished #{p}! Reward: ❤{h} ({k} kisses).",
}


async def notify(awards: list[dict]) -> None:
    from . import bot as botmod
    from .game import hub
    for a in awards:
        u = db.get_user(a["uid"])
        if not u:
            continue
        lang = u["lang"] if u["lang"] in MSG else "en"
        await hub.push_me(a["uid"])
        c = hub.clients.get(a["uid"])
        if c:
            await c.send({"t": "weekly", "place": a["place"], "hearts": a["hearts"], "kisses": a["kisses"]})
        if botmod.bot and u["bot_started"] and u["notify"]:
            try:
                await botmod.bot.send_message(a["uid"], MSG[lang].format(p=a["place"], h=a["hearts"], k=a["kisses"]))
            except Exception:
                pass


async def weekly_loop() -> None:
    await asyncio.sleep(20)
    while True:
        try:
            awards = await asyncio.to_thread(award_last_week)
            if awards:
                print("weekly awards:", awards)
                await notify(awards)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print("weekly awards failed:", e)
        await asyncio.sleep(3600)

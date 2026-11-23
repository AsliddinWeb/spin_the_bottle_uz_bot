import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
# Public https URL of this server (Telegram requires https for Mini Apps)
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000").rstrip("/")
# Channel users can subscribe to for free hearts, e.g. @spinbottle_uz
CHANNEL = os.getenv("CHANNEL", "").strip()
SUPPORT = os.getenv("SUPPORT", "").strip()  # e.g. @your_support
# Dev mode lets the Mini App run in a normal browser without Telegram
DEV_MODE = os.getenv("DEV_MODE", "1" if not BOT_TOKEN else "0") == "1"
DB_PATH = os.getenv("DB_PATH", str(ROOT / "spin.db"))
PORT = int(os.getenv("PORT", "8000"))

# Telegram ids allowed to use /broadcast, e.g. ADMIN_IDS=123456,789012
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "10"))  # local server hour for the daily-bonus reminder

# Payments: "manual" = the player places an order, an admin takes the money outside the bot and confirms it.
# "stars" = Telegram Stars invoices (code kept, off by default).
PAYMENTS = os.getenv("PAYMENTS", "manual")
PAY_INFO = os.getenv("PAY_INFO", "").strip()          # shown in the order dialog, e.g. card number / instructions
PRICE_CUR = os.getenv("PRICE_CUR", "so'm")
# e.g. PRICES=p50=5000,p250=20000,p500=38000,p1000=70000,p2500=160000,p5000=300000,vip=60000 (any may be missing)
PRICES = {k.strip(): v.strip() for k, _, v in (x.partition("=") for x in os.getenv("PRICES", "").split(",")) if k.strip() and v.strip()}

START_HEARTS = 30
MAX_SEATS = 12
TABLE_COUNT = 300

# "Kick & Rescue": a player can kick another one from the table; the kicked player leaves after KICK_DELAY seconds
# unless somebody rescues them, and cannot come back to that table for KICK_BAN_MIN minutes.
KICK_DELAY = int(os.getenv("KICK_DELAY", "30"))          # seconds until the kick takes effect
KICK_BAN_MIN = int(os.getenv("KICK_BAN_MIN", "15"))      # minutes the kicked player cannot rejoin that table
KICK_FREE_EVERY = int(os.getenv("KICK_FREE_EVERY", "1800"))  # one free kick per this many seconds
KICK_PRICE = 10          # hearts for a kick when the free one is not ready
RESCUE_PRICE = 3         # hearts the rescuer pays
KICK_MIN_PLAYERS = 3     # nobody can be kicked from a table with fewer players

# Weekly top: the best kissers of the last calendar week (Mon-Sun) get hearts. Kisses count at most PAIR_DAILY_CAP times
# per pair per day in the day/week/month lists, so two accounts cannot farm the top by kissing each other.
WEEKLY_REWARDS = [100, 50, 25]
WEEKLY_MIN = 5
REF_KISSES = 50            # the invited friend must reach this many kisses
REF_REWARD = 20            # hearts for the inviter
REF_REWARD_PREMIUM = 50    # ... if the friend has Telegram Premium
REF_FRIEND_BONUS = 20      # hearts for the friend at the same moment
REF_MIN_PARTNERS = 3       # kisses with at least this many different people (a pair of fake accounts cannot farm it)
REF_DAILY_CAP = 10         # rewards one inviter can collect per day (the rest waits for the next day)
LEAGUE_LIMIT = 30          # league points per week that incoming kisses can bring ("лимит на входящие поцелуи")
LEAGUE_X2_SEC = 300        # x2 booster lasts 5 minutes
LEAGUE_LIMIT_PLUS = 10     # "Расширение лимита": +10 to this week's limit
LEAGUE_PLUS_PTS = 5        # "+5 очков": instant, ignores the limit
LEAGUE_MIN = 5             # minimum points to win a weekly prize
LEAGUE_PRIZES = {1: {"kiss_fire": 3, "slap": 3, "league_x2": 2, "league_plus5": 1}, 2: {"kiss_fire": 2, "slap": 2, "league_x2": 1}, 3: {"kiss_fire": 1, "slap": 1, "league_x2": 1}}
DAILY_TASKS = [("kiss3", "kisses", 3, 4), ("msg5", "msgs", 5, 2), ("gift1", "gifts_sent", 1, 3), ("music1", "tracks", 1, 5), ("spin3", "spins", 3, 3)]  # 3 random ones per day
STARTER = [("st_spin", "spins", 3), ("st_kiss", "kisses", 3), ("st_gift", "gifts_sent", 3)]  # (claim key, user stat, reward hearts)
PAIR_DAILY_CAP = 3

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

import hashlib
import hmac
import json
import time
import zlib
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from . import config, db


def validate_init_data(init_data: str) -> dict | None:
    """Verify Telegram WebApp initData; return the user dict or None."""
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        got = pairs.pop("hash", "")
        check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, got):
            return None
        if time.time() - int(pairs.get("auth_date", 0)) > 86400:
            return None
        return json.loads(pairs["user"])
    except Exception:
        return None


def authenticate(init_data: str):
    """Return the DB user row for a valid initData (or dev token), else None."""
    if config.DEV_MODE and init_data.startswith("dev:"):
        raw = init_data[4:]
        uid = int(raw) if raw.isdigit() else zlib.crc32(raw.encode())
        row, _ = db.ensure_user(uid, f"Dev{uid % 1000}", lang="uz")
        return row
    if not config.BOT_TOKEN:
        return None
    tg = validate_init_data(init_data)
    if not tg:
        return None
    name = (tg.get("first_name") or "") or tg.get("username") or "Player"
    row, _ = db.ensure_user(tg["id"], name, tg.get("photo_url", ""), _lang(tg.get("language_code")), username=tg.get("username") or "", premium=bool(tg.get("is_premium")))
    return row


def _lang(code: str | None) -> str:
    code = (code or "").lower()
    return code if code in ("uz", "ru", "en") else ("ru" if code.startswith("ru") else "uz")


def ban_info(uid: int) -> dict | None:
    from . import moderation
    b = moderation.active(uid, "ban")
    return {"code": "banned", "reason": b["reason"], "until": b["until"]} if b else None


async def current_user(x_init_data: str = Header(default="")):
    u = authenticate(x_init_data)
    if not u:
        raise HTTPException(401, "unauthorized")
    if info := ban_info(u["id"]):
        raise HTTPException(403, info)
    return u

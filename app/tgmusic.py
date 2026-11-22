"""Music from the player's Telegram profile (Bot API getUserProfileAudios). The audio file is fetched through the bot and served
from a small on-disk cache so every client at the table can stream it (with Range support) without seeing the bot token."""
import hashlib
import time
from pathlib import Path

import httpx

from . import bot as botmod, config

CACHE_DIR = Path(config.DB_PATH).resolve().parent / "tgaudio"
MAX_FILES = 60
_LISTS: dict[int, tuple[float, list]] = {}


def _title(a) -> str:
    t = (a.title or a.file_name or "Audio").strip()
    return f"{a.performer.strip()} \u2014 {t}" if getattr(a, "performer", None) else t


async def profile_list(uid: int) -> list[dict]:
    """The player's profile audios (cached 2 min): [{fid, title, artist, dur}]."""
    hit = _LISTS.get(uid)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    out: list[dict] = []
    if botmod.bot:
        try:
            r = await botmod.bot.get_user_profile_audios(uid, limit=50)
            out = [{"fid": a.file_id, "title": (a.title or a.file_name or "Audio"), "artist": a.performer or "", "dur": a.duration or 0, "full": _title(a)} for a in r.audios if (a.file_size or 0) <= 19_000_000]
        except Exception:
            out = []
    _LISTS[uid] = (time.time(), out)
    return out


async def lookup(uid: int, fid: str) -> dict | None:
    return next((x for x in await profile_list(uid) if x["fid"] == fid), None)


async def fetch(fid: str) -> Path | None:
    """Download the file once (<= 20 MB, the Bot API limit) and keep it in the cache directory."""
    if not botmod.bot:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / (hashlib.sha1(fid.encode()).hexdigest() + ".audio")
    if p.exists():
        p.touch()
        return p
    try:
        f = await botmod.bot.get_file(fid)
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{f.file_path}")
        if r.status_code != 200:
            return None
        p.write_bytes(r.content)
    except Exception:
        return None
    files = sorted(CACHE_DIR.glob("*.audio"), key=lambda x: x.stat().st_mtime)
    for old in files[:-MAX_FILES]:
        old.unlink(missing_ok=True)
    return p

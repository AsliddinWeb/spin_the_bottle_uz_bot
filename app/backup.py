"""Backups: one .tar.gz = consistent snapshot of the SQLite DB + the uploads/ folder.

The DB snapshot uses SQLite's online backup API, so it is safe while the game is running (plain file copy of a WAL
database is not). The snapshot is integrity-checked before it is archived. Old archives are rotated.
"""
import asyncio
import os
import sqlite3
import tarfile
import tempfile
import time
from pathlib import Path

from . import config

DIR = Path(os.getenv("BACKUP_DIR", str(config.ROOT / "backups")))
KEEP = int(os.getenv("BACKUP_KEEP", "14"))
EVERY = int(os.getenv("BACKUP_EVERY_HOURS", "24")) * 3600
PREFIX = "spinbot-"


def list_backups() -> list[Path]:
    DIR.mkdir(parents=True, exist_ok=True)
    return sorted(DIR.glob(PREFIX + "*.tar.gz"))


def make_backup() -> Path:
    """Create a new archive, rotate old ones, return its path. Raises on a corrupt snapshot."""
    DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = DIR / f"{PREFIX}{stamp}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / "spin.db"
        src = sqlite3.connect(config.DB_PATH)
        dst = sqlite3.connect(snap)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        chk = sqlite3.connect(snap)
        try:
            ok = chk.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            chk.close()
        if ok != "ok":
            raise RuntimeError(f"snapshot failed integrity check: {ok}")
        part = out.with_suffix(".part")
        with tarfile.open(part, "w:gz") as tar:
            tar.add(snap, arcname="spin.db")
            up = config.ROOT / "uploads"
            if up.exists():
                tar.add(up, arcname="uploads")
        part.rename(out)  # only a finished archive ever has the final name
    for old in list_backups()[:-KEEP]:
        old.unlink(missing_ok=True)
    return out


def latest_age() -> float | None:
    b = list_backups()
    return time.time() - b[-1].stat().st_mtime if b else None


def human_size(p: Path) -> str:
    n = p.stat().st_size
    return f"{n / 1024:.0f} KB" if n < 1_048_576 else f"{n / 1_048_576:.1f} MB"


async def backup_loop() -> None:
    """Checks hourly; takes a backup when the newest one is older than BACKUP_EVERY_HOURS (or none exists)."""
    await asyncio.sleep(30)
    while True:
        try:
            age = latest_age()
            if age is None or age >= EVERY:
                p = await asyncio.to_thread(make_backup)
                print(f"backup ok: {p.name} ({human_size(p)})")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print("backup failed:", e)
        await asyncio.sleep(3600)

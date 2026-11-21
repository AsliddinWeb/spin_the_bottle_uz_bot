"""Restore a backup. STOP the server first.

    .venv/bin/python restore_backup.py                 # list backups
    .venv/bin/python restore_backup.py <archive|latest>  # restore (current DB/uploads are kept as *.before-restore)
"""
import shutil
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from app import backup, config


def main() -> None:
    bs = backup.list_backups()
    if len(sys.argv) < 2:
        for b in bs:
            print(f"{b.name}  {backup.human_size(b)}  {time.strftime('%Y-%m-%d %H:%M', time.localtime(b.stat().st_mtime))}")
        print("\nRestore with: restore_backup.py <name|latest>" if bs else "no backups yet")
        return
    arg = sys.argv[1]
    arc = bs[-1] if arg == "latest" and bs else (backup.DIR / arg)
    if not arc.exists():
        sys.exit(f"not found: {arc}")
    if input(f"Restore {arc.name}? The server must be stopped. Type 'yes': ").strip() != "yes":
        sys.exit("cancelled")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    db, up = Path(config.DB_PATH), config.ROOT / "uploads"
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(arc) as tar:
            tar.extractall(tmp, filter="data")  # "data" filter: refuses absolute paths / path tricks
        for ext in ("", "-wal", "-shm"):
            f = Path(str(db) + ext)
            if f.exists():
                f.rename(f.with_name(f.name + f".before-restore-{stamp}"))
        shutil.copy2(Path(tmp) / "spin.db", db)
        if up.exists():
            up.rename(up.with_name(f"uploads.before-restore-{stamp}"))
        if (Path(tmp) / "uploads").exists():
            shutil.copytree(Path(tmp) / "uploads", up)
        else:
            up.mkdir()
    print("restored. Start the server again.")


if __name__ == "__main__":
    main()

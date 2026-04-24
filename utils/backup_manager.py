"""
Automatic backup manager for PlywoodPro.
- Auto-backup on startup if no backup exists for today
- Keeps last 30 daily backups, deletes older ones
- Manual backup via UI also supported
- Backup location: backups/ folder next to plywoodpro.db
"""
import os
import shutil
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plywoodpro.db')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
MAX_BACKUPS = 30


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def auto_backup_on_startup() -> str | None:
    """
    Creates a daily backup on app startup.
    Returns backup path if backup was created, None if today's backup already exists.
    """
    _ensure_backup_dir()

    if not os.path.exists(DB_PATH):
        return None

    today_str = date.today().strftime("%Y%m%d")
    today_backup = os.path.join(BACKUP_DIR, f"plywoodpro_{today_str}.db")

    if os.path.exists(today_backup):
        return None

    try:
        shutil.copy2(DB_PATH, today_backup)
        _cleanup_old_backups()
        print(f"[Backup] Auto-backup created: {today_backup}")
        return today_backup
    except Exception as e:
        print(f"[Backup] Auto-backup failed: {e}")
        return None


def manual_backup() -> tuple[bool, str]:
    """
    Creates a timestamped manual backup.
    Returns (success, message).
    """
    _ensure_backup_dir()

    if not os.path.exists(DB_PATH):
        return False, "Database file not found."

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"plywoodpro_manual_{ts}.db")

    try:
        shutil.copy2(DB_PATH, backup_path)
        size_kb = os.path.getsize(backup_path) // 1024
        return True, f"Backup saved:\n{backup_path}\n({size_kb} KB)"
    except Exception as e:
        return False, f"Backup failed: {str(e)}"


def list_backups() -> list[dict]:
    """Returns list of existing backups with metadata."""
    _ensure_backup_dir()
    backups = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if f.endswith('.db'):
            path = os.path.join(BACKUP_DIR, f)
            stat = os.stat(path)
            backups.append({
                'filename': f,
                'path': path,
                'size_kb': stat.st_size // 1024,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
            })
    return backups


def _cleanup_old_backups():
    """Delete backups beyond MAX_BACKUPS to save disk space."""
    try:
        all_backups = sorted([
            f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')
        ])
        if len(all_backups) > MAX_BACKUPS:
            for old in all_backups[:-MAX_BACKUPS]:
                os.remove(os.path.join(BACKUP_DIR, old))
    except Exception as e:
        print(f"[Backup] Cleanup error: {e}")

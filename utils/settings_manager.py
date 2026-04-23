"""
Settings Manager for PlywoodPro.
Provides get_setting() and set_setting() for reading/writing
the settings table (key-value pairs).
"""

import sqlite3
import traceback
from db.connection import get_connection


def get_setting(key: str, default=None) -> str | None:
    """
    Read a setting value from the settings table.
    Returns the value string or default if not found.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row['value'] if row else default
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error reading setting '{key}': {e}")
        return default
    finally:
        conn.close()


def set_setting(key: str, value: str) -> bool:
    """
    Write a setting to the settings table.
    Uses INSERT OR REPLACE for upsert behavior.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error saving setting '{key}': {e}")
        traceback.print_exc()
        return False
    finally:
        conn.close()


def get_all_settings() -> dict:
    """Return all settings as a dict."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r['key']: r['value'] for r in rows}
    except sqlite3.Error:
        return {}
    finally:
        conn.close()

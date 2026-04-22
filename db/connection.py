"""
Database connection module for PlywoodPro.
Provides a single function to get a configured SQLite connection
with WAL mode, foreign keys, and row factory enabled.
"""

import sqlite3
import os
import sys

if getattr(sys, 'frozen', False):
    # PyInstaller: put database next to the executable
    DB_PATH = os.path.join(os.path.dirname(sys.executable), 'plywoodpro.db')
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plywoodpro.db')


def get_connection() -> sqlite3.Connection:
    """
    Returns a configured SQLite3 connection to the PlywoodPro database.

    Configuration applied on every connection:
    - Row factory set to sqlite3.Row for column-name access
    - WAL journal mode for concurrent read performance
    - Foreign keys enforced
    - Synchronous set to NORMAL for balance of safety and speed
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row        # access columns by name
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

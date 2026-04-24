"""
Database migration runner for PlywoodPro.
Call run_migrations(conn) on every app startup.
Reads migration files from db/migrations/ in order.
Safe to call repeatedly - skips already-applied migrations.
"""
import os
import sqlite3

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')


def run_migrations(conn: sqlite3.Connection):
    """Apply any pending migrations to the database."""
    current_version = conn.execute('PRAGMA user_version').fetchone()[0]

    if not os.path.exists(MIGRATIONS_DIR):
        os.makedirs(MIGRATIONS_DIR)
        return

    migration_files = sorted([
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith('.sql') and f[0].isdigit()
    ])

    applied = 0
    for filename in migration_files:
        try:
            version = int(filename.split('_')[0])
        except ValueError:
            continue

        if version <= current_version:
            continue

        print(f"[Migration] Applying {filename}...")
        try:
            filepath = os.path.join(MIGRATIONS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()
            conn.executescript(sql)
            conn.execute(f'PRAGMA user_version = {version}')
            conn.commit()
            applied += 1
            print(f"[Migration] {filename} applied successfully.")
        except Exception as e:
            print(f"[Migration] ERROR applying {filename}: {e}")
            raise

    if applied == 0:
        print(f"[Migration] Database is up to date (version {current_version}).")
    else:
        new_version = conn.execute('PRAGMA user_version').fetchone()[0]
        print(f"[Migration] {applied} migration(s) applied. Version: {current_version} -> {new_version}")

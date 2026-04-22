"""
Database initializer for PlywoodPro.
Reads schema.sql to create all tables, then inserts seed data
(default godown, system accounts, voucher sequences, default admin user)
if the tables are empty. Runs on first launch and is safe to re-run.
"""

import os
import sys
import hashlib
import sqlite3
from db.connection import get_connection


def _get_base_path():
    """Return the base path — handles both source and PyInstaller frozen mode."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


SCHEMA_PATH = os.path.join(_get_base_path(), 'db', 'schema.sql') if getattr(sys, 'frozen', False) else os.path.join(os.path.dirname(__file__), 'schema.sql')


def _hash_password(password: str) -> str:
    """Return SHA-256 hex digest of the given plain-text password."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_database():
    """
    Create all tables from schema.sql if they don't exist,
    then seed default data into empty tables.
    """
    conn = get_connection()
    try:
        # ── Create Tables ──────────────────────────────────────────
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)

        # ── Seed Data (only if tables are empty) ───────────────────

        # Default Godown
        row = conn.execute("SELECT COUNT(*) FROM godowns").fetchone()
        if row[0] == 0:
            conn.execute(
                "INSERT OR IGNORE INTO godowns (id, name) VALUES (1, 'Main Godown')"
            )

        # Default System Accounts
        row = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()
        if row[0] == 0:
            system_accounts = [
                ('Cash',            'Cash-in-Hand',      1),
                ('Bank',            'Bank Accounts',     1),
                ('Sales',           'Sales Accounts',    1),
                ('Purchase',        'Purchase Accounts', 1),
                ('CGST Payable',    'Duties & Taxes',    1),
                ('SGST Payable',    'Duties & Taxes',    1),
                ('IGST Payable',    'Duties & Taxes',    1),
                ('CGST Input',      'Duties & Taxes',    1),
                ('SGST Input',      'Duties & Taxes',    1),
                ('IGST Input',      'Duties & Taxes',    1),
                ('Discount Given',  'Indirect Expenses', 1),
                ('Freight Charges', 'Indirect Expenses', 1),
                ('Capital Account', 'Capital Account',   1),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO accounts (name, group_name, is_system) VALUES (?, ?, ?)",
                system_accounts,
            )

        # Default Voucher Sequences
        row = conn.execute("SELECT COUNT(*) FROM voucher_sequences").fetchone()
        if row[0] == 0:
            sequences = [
                ('Sales Invoice',    'SI',  0, '2024-25'),
                ('Purchase Invoice', 'PI',  0, '2024-25'),
                ('Sales Order',      'SO',  0, '2024-25'),
                ('Purchase Order',   'PO',  0, '2024-25'),
                ('Delivery Challan', 'DC',  0, '2024-25'),
                ('GRN',              'GRN', 0, '2024-25'),
                ('Receipt',          'RCP', 0, '2024-25'),
                ('Payment',          'PMT', 0, '2024-25'),
                ('Journal',          'JV',  0, '2024-25'),
                ('Credit Note',      'CN',  0, '2024-25'),
                ('Debit Note',       'DN',  0, '2024-25'),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO voucher_sequences (voucher_type, prefix, last_number, financial_year) "
                "VALUES (?, ?, ?, ?)",
                sequences,
            )

        # Default Admin User (password: admin123)
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        if row[0] == 0:
            admin_hash = _hash_password('admin123')
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password, full_name, role) "
                "VALUES (?, ?, ?, ?)",
                ('admin', admin_hash, 'Administrator', 'Admin'),
            )

        conn.commit()
        print("[PlywoodPro] Database initialized successfully.")

    except sqlite3.Error as e:
        print(f"[PlywoodPro] Database initialization error: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    init_database()

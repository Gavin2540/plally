"""
Masters module for PlywoodPro.
CRUD operations for Party, Item, Godown, and Account master records.
Also includes the voucher number generator used across all transaction modules.
All database operations use parameterized queries and proper error handling.
"""

import sqlite3
import traceback
from db.connection import get_connection


# ═══════════════════════════════════════════════════════════════════════
# VOUCHER NUMBER GENERATION
# ═══════════════════════════════════════════════════════════════════════

def generate_voucher_no(conn: sqlite3.Connection, voucher_type: str, date: str) -> str:
    """
    Generates next voucher number for the given type.
    Format: PREFIX-YY-NNNN  e.g. SI-25-0001
    Uses voucher_sequences table. Increments last_number atomically.
    """
    year_suffix = date[2:4]  # from 'YYYY-MM-DD'
    row = conn.execute(
        "SELECT prefix, last_number FROM voucher_sequences WHERE voucher_type=?",
        (voucher_type,)
    ).fetchone()
    new_num = row[1] + 1
    conn.execute(
        "UPDATE voucher_sequences SET last_number=? WHERE voucher_type=?",
        (new_num, voucher_type)
    )
    return f"{row[0]}-{year_suffix}-{new_num:04d}"


# ═══════════════════════════════════════════════════════════════════════
# PARTY CRUD
# ═══════════════════════════════════════════════════════════════════════

def get_all_parties(search: str = '', party_type: str = '') -> list:
    """
    Fetch all active parties, optionally filtered by search term and type.
    Search checks against name, GSTIN, city, and phone.
    """
    conn = get_connection()
    try:
        query = "SELECT * FROM parties WHERE is_active = 1"
        params = []

        if party_type and party_type != 'All':
            query += " AND (type = ? OR type = 'both')"
            params.append(party_type.lower())

        if search:
            query += (
                " AND (name LIKE ? OR gstin LIKE ? OR city LIKE ? OR phone LIKE ?)"
            )
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term, search_term])

        query += " ORDER BY name ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching parties: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


def get_party_by_id(party_id: int) -> dict | None:
    """Fetch a single party by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM parties WHERE id = ?", (party_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching party {party_id}: {e}")
        traceback.print_exc()
        return None
    finally:
        conn.close()


def create_party(data: dict) -> tuple[bool, str]:
    """
    Insert a new party record.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO parties
            (name, type, gstin, pan, address_line1, address_line2, city, state,
             state_code, pincode, phone, email, credit_limit, credit_days,
             opening_balance, balance_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data['name'], data['type'], data.get('gstin', ''),
                data.get('pan', ''), data.get('address_line1', ''),
                data.get('address_line2', ''), data.get('city', ''),
                data.get('state', ''), data.get('state_code', ''),
                data.get('pincode', ''), data.get('phone', ''),
                data.get('email', ''), data.get('credit_limit', 0),
                data.get('credit_days', 0), data.get('opening_balance', 0),
                data.get('balance_type', 'Dr'),
            ),
        )
        conn.commit()
        return True, f"Party '{data['name']}' created successfully."
    except sqlite3.IntegrityError as e:
        return False, f"Integrity error: {e}"
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error creating party: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def update_party(party_id: int, data: dict) -> tuple[bool, str]:
    """
    Update an existing party record by ID.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE parties SET
            name=?, type=?, gstin=?, pan=?, address_line1=?, address_line2=?,
            city=?, state=?, state_code=?, pincode=?, phone=?, email=?,
            credit_limit=?, credit_days=?, opening_balance=?, balance_type=?
            WHERE id=?""",
            (
                data['name'], data['type'], data.get('gstin', ''),
                data.get('pan', ''), data.get('address_line1', ''),
                data.get('address_line2', ''), data.get('city', ''),
                data.get('state', ''), data.get('state_code', ''),
                data.get('pincode', ''), data.get('phone', ''),
                data.get('email', ''), data.get('credit_limit', 0),
                data.get('credit_days', 0), data.get('opening_balance', 0),
                data.get('balance_type', 'Dr'), party_id,
            ),
        )
        conn.commit()
        return True, f"Party '{data['name']}' updated successfully."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error updating party {party_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def delete_party(party_id: int) -> tuple[bool, str]:
    """
    Soft-delete a party by setting is_active to 0.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute("UPDATE parties SET is_active = 0 WHERE id = ?", (party_id,))
        conn.commit()
        return True, "Party deactivated successfully."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error deleting party {party_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
# ITEM CRUD
# ═══════════════════════════════════════════════════════════════════════

def get_all_items(search: str = '', category: str = '') -> list:
    """
    Fetch all active items, optionally filtered by search and category.
    Search checks against name, hsn_code, and category.
    """
    conn = get_connection()
    try:
        query = "SELECT * FROM items WHERE is_active = 1"
        params = []

        if category and category != 'All':
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (name LIKE ? OR hsn_code LIKE ? OR category LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])

        query += " ORDER BY name ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching items: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


def get_item_by_id(item_id: int) -> dict | None:
    """Fetch a single item by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching item {item_id}: {e}")
        traceback.print_exc()
        return None
    finally:
        conn.close()


def create_item(data: dict) -> tuple[bool, str]:
    """
    Insert a new item record.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO items
            (name, category, hsn_code, unit, thickness, size, gst_rate,
             purchase_rate, sale_rate, reorder_level, opening_stock, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data['name'], data.get('category', ''), data['hsn_code'],
                data['unit'], data.get('thickness', ''), data.get('size', ''),
                data.get('gst_rate', 18.0), data.get('purchase_rate', 0),
                data.get('sale_rate', 0), data.get('reorder_level', 0),
                data.get('opening_stock', 0), data.get('description', ''),
            ),
        )
        conn.commit()
        return True, f"Item '{data['name']}' created successfully."
    except sqlite3.IntegrityError as e:
        return False, f"Integrity error: {e}"
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error creating item: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def update_item(item_id: int, data: dict) -> tuple[bool, str]:
    """
    Update an existing item record by ID.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE items SET
            name=?, category=?, hsn_code=?, unit=?, thickness=?, size=?,
            gst_rate=?, purchase_rate=?, sale_rate=?, reorder_level=?,
            opening_stock=?, description=?
            WHERE id=?""",
            (
                data['name'], data.get('category', ''), data['hsn_code'],
                data['unit'], data.get('thickness', ''), data.get('size', ''),
                data.get('gst_rate', 18.0), data.get('purchase_rate', 0),
                data.get('sale_rate', 0), data.get('reorder_level', 0),
                data.get('opening_stock', 0), data.get('description', ''),
                item_id,
            ),
        )
        conn.commit()
        return True, f"Item '{data['name']}' updated successfully."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error updating item {item_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def delete_item(item_id: int) -> tuple[bool, str]:
    """
    Soft-delete an item by setting is_active to 0.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute("UPDATE items SET is_active = 0 WHERE id = ?", (item_id,))
        conn.commit()
        return True, "Item deactivated successfully."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error deleting item {item_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
# GODOWN CRUD
# ═══════════════════════════════════════════════════════════════════════

def get_all_godowns(search: str = '') -> list:
    """Fetch all active godowns, optionally filtered by name search."""
    conn = get_connection()
    try:
        query = "SELECT * FROM godowns WHERE is_active = 1"
        params = []

        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")

        query += " ORDER BY name ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching godowns: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


def get_godown_by_id(godown_id: int) -> dict | None:
    """Fetch a single godown by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM godowns WHERE id = ?", (godown_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching godown {godown_id}: {e}")
        traceback.print_exc()
        return None
    finally:
        conn.close()


def create_godown(data: dict) -> tuple[bool, str]:
    """
    Insert a new godown record.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO godowns (name, address) VALUES (?, ?)",
            (data['name'], data.get('address', '')),
        )
        conn.commit()
        return True, f"Godown '{data['name']}' created successfully."
    except sqlite3.IntegrityError:
        return False, f"Godown '{data['name']}' already exists."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error creating godown: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def update_godown(godown_id: int, data: dict) -> tuple[bool, str]:
    """
    Update an existing godown record by ID.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE godowns SET name=?, address=? WHERE id=?",
            (data['name'], data.get('address', ''), godown_id),
        )
        conn.commit()
        return True, f"Godown '{data['name']}' updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Godown '{data['name']}' already exists."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error updating godown {godown_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def delete_godown(godown_id: int) -> tuple[bool, str]:
    """
    Soft-delete a godown by setting is_active to 0.
    Cannot delete the default 'Main Godown' (id=1).
    Returns (success: bool, message: str).
    """
    if godown_id == 1:
        return False, "Cannot delete the Main Godown."
    conn = get_connection()
    try:
        conn.execute("UPDATE godowns SET is_active = 0 WHERE id = ?", (godown_id,))
        conn.commit()
        return True, "Godown deactivated successfully."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error deleting godown {godown_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
# ACCOUNT CRUD
# ═══════════════════════════════════════════════════════════════════════

# Valid account groups (matching the CHECK constraint in schema)
ACCOUNT_GROUPS = [
    'Capital Account', 'Loans (Liability)', 'Current Liabilities',
    'Fixed Assets', 'Current Assets', 'Stock-in-Hand',
    'Sales Accounts', 'Purchase Accounts',
    'Direct Income', 'Indirect Income',
    'Direct Expenses', 'Indirect Expenses',
    'Bank Accounts', 'Cash-in-Hand', 'Sundry Debtors', 'Sundry Creditors',
    'Duties & Taxes',
]


def get_all_accounts(search: str = '', group_name: str = '') -> list:
    """Fetch all active accounts, optionally filtered by search and group."""
    conn = get_connection()
    try:
        query = "SELECT * FROM accounts WHERE is_active = 1"
        params = []

        if group_name and group_name != 'All':
            query += " AND group_name = ?"
            params.append(group_name)

        if search:
            query += " AND (name LIKE ? OR group_name LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        query += " ORDER BY group_name ASC, name ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching accounts: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


def get_account_by_id(account_id: int) -> dict | None:
    """Fetch a single account by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching account {account_id}: {e}")
        traceback.print_exc()
        return None
    finally:
        conn.close()


def create_account(data: dict) -> tuple[bool, str]:
    """
    Insert a new account record.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO accounts (name, group_name, opening_balance, balance_type)
            VALUES (?, ?, ?, ?)""",
            (
                data['name'], data['group_name'],
                data.get('opening_balance', 0),
                data.get('balance_type', 'Dr'),
            ),
        )
        conn.commit()
        return True, f"Account '{data['name']}' created successfully."
    except sqlite3.IntegrityError:
        return False, f"Account '{data['name']}' already exists."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error creating account: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def update_account(account_id: int, data: dict) -> tuple[bool, str]:
    """
    Update an existing account record by ID.
    System accounts (is_system=1) can only have their opening_balance updated.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT is_system FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()

        if existing and existing[0] == 1:
            # System account — only allow balance update
            conn.execute(
                "UPDATE accounts SET opening_balance=?, balance_type=? WHERE id=?",
                (data.get('opening_balance', 0), data.get('balance_type', 'Dr'), account_id),
            )
        else:
            conn.execute(
                """UPDATE accounts SET name=?, group_name=?,
                opening_balance=?, balance_type=? WHERE id=?""",
                (
                    data['name'], data['group_name'],
                    data.get('opening_balance', 0),
                    data.get('balance_type', 'Dr'), account_id,
                ),
            )
        conn.commit()
        return True, f"Account updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Account '{data.get('name', '')}' already exists."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error updating account {account_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def delete_account(account_id: int) -> tuple[bool, str]:
    """
    Soft-delete an account by setting is_active to 0.
    System accounts (is_system=1) cannot be deleted.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT is_system FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()

        if existing and existing[0] == 1:
            return False, "System accounts cannot be deleted."

        conn.execute("UPDATE accounts SET is_active = 0 WHERE id = ?", (account_id,))
        conn.commit()
        return True, "Account deactivated successfully."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error deleting account {account_id}: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
# COMPANY (single-row settings)
# ═══════════════════════════════════════════════════════════════════════

def get_company() -> dict | None:
    """Fetch the single company record (id=1)."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM company WHERE id = 1").fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching company: {e}")
        traceback.print_exc()
        return None
    finally:
        conn.close()


def save_company(data: dict) -> tuple[bool, str]:
    """
    Insert or update the company record (upsert to id=1).
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM company WHERE id = 1").fetchone()
        if existing:
            conn.execute(
                """UPDATE company SET
                name=?, address_line1=?, address_line2=?, city=?, state=?,
                state_code=?, pincode=?, gstin=?, pan=?, phone=?, email=?,
                bank_name=?, bank_account=?, bank_ifsc=?, fy_start_month=?, logo_path=?
                WHERE id=1""",
                (
                    data['name'], data.get('address_line1', ''),
                    data.get('address_line2', ''), data.get('city', ''),
                    data['state'], data['state_code'],
                    data.get('pincode', ''), data.get('gstin', ''),
                    data.get('pan', ''), data.get('phone', ''),
                    data.get('email', ''), data.get('bank_name', ''),
                    data.get('bank_account', ''), data.get('bank_ifsc', ''),
                    data.get('fy_start_month', 4), data.get('logo_path', ''),
                ),
            )
        else:
            conn.execute(
                """INSERT INTO company
                (id, name, address_line1, address_line2, city, state, state_code,
                 pincode, gstin, pan, phone, email, bank_name, bank_account,
                 bank_ifsc, fy_start_month, logo_path)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data['name'], data.get('address_line1', ''),
                    data.get('address_line2', ''), data.get('city', ''),
                    data['state'], data['state_code'],
                    data.get('pincode', ''), data.get('gstin', ''),
                    data.get('pan', ''), data.get('phone', ''),
                    data.get('email', ''), data.get('bank_name', ''),
                    data.get('bank_account', ''), data.get('bank_ifsc', ''),
                    data.get('fy_start_month', 4), data.get('logo_path', ''),
                ),
            )
        conn.commit()
        return True, "Company details saved successfully."
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error saving company: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()

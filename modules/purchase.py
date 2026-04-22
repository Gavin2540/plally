"""
Purchase module for PlywoodPro.
Business logic for Purchase Invoices: create draft, confirm (with ITC journal
entries and stock IN movements), fetch, and cancel.
All monetary math uses Decimal.
"""

import sqlite3
import traceback
from decimal import Decimal, ROUND_HALF_UP
from db.connection import get_connection
from modules.masters import generate_voucher_no


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _d(val) -> Decimal:
    """Convert any numeric value to Decimal safely."""
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _r2(val: Decimal) -> float:
    """Round Decimal to 2 places and return as float for DB storage."""
    return float(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _get_account_id(conn, name: str) -> int:
    """Fetch account ID by name. Returns 0 if not found."""
    row = conn.execute(
        "SELECT id FROM accounts WHERE name = ? AND is_active = 1", (name,)
    ).fetchone()
    return row[0] if row else 0


def _ensure_party_account(conn, party_id: int, party_type: str) -> int:
    """
    Ensure a ledger account exists for the party under
    Sundry Debtors (customer) or Sundry Creditors (supplier).
    Returns the account_id.
    """
    party = conn.execute("SELECT name FROM parties WHERE id = ?", (party_id,)).fetchone()
    if not party:
        return 0
    party_name = party['name']
    group = 'Sundry Debtors' if party_type == 'customer' else 'Sundry Creditors'

    existing = conn.execute(
        "SELECT id FROM accounts WHERE name = ? AND group_name = ?",
        (party_name, group)
    ).fetchone()
    if existing:
        return existing['id']

    cursor = conn.execute(
        "INSERT INTO accounts (name, group_name, is_system, is_active) VALUES (?, ?, 0, 1)",
        (party_name, group)
    )
    return cursor.lastrowid


def _update_stock(conn, item_id: int, godown_id: int, qty_change: Decimal):
    """Update the stock table. qty_change is positive for IN, negative for OUT."""
    existing = conn.execute(
        "SELECT id, qty FROM stock WHERE item_id = ? AND godown_id = ?",
        (item_id, godown_id)
    ).fetchone()

    if existing:
        new_qty = _d(existing['qty']) + qty_change
        conn.execute(
            "UPDATE stock SET qty = ?, last_updated = datetime('now','localtime') WHERE id = ?",
            (_r2(new_qty), existing['id'])
        )
    else:
        conn.execute(
            "INSERT INTO stock (item_id, godown_id, qty) VALUES (?, ?, ?)",
            (item_id, godown_id, _r2(qty_change))
        )


# ═══════════════════════════════════════════════════════════════════════
#  PURCHASE INVOICE — CREATE DRAFT
# ═══════════════════════════════════════════════════════════════════════

def create_purchase_invoice(header: dict, line_items: list) -> tuple[bool, str, int]:
    """
    Create a Purchase Invoice in Draft status.
    header keys: party_id, date, due_date, reference_no, narration, godown_id
    line_items: list of dicts with item_id, description, hsn_code, qty, unit,
                rate, discount_pct, gst_rate, cgst_rate/amount, sgst_rate/amount,
                igst_rate/amount, taxable_amount, total_amount
    Returns (success, message, voucher_id).
    """
    conn = get_connection()
    try:
        date_str = header.get('date', '')
        voucher_no = generate_voucher_no(conn, 'Purchase Invoice', date_str)

        total_amount = Decimal("0")
        tax_amount = Decimal("0")
        discount_amount = Decimal("0")
        grand_total = Decimal("0")

        for item in line_items:
            total_amount += _d(item.get('taxable_amount', 0))
            tax_amount += (_d(item.get('cgst_amount', 0)) +
                           _d(item.get('sgst_amount', 0)) +
                           _d(item.get('igst_amount', 0)))
            discount_amount += _d(item.get('discount_amount', 0))
            grand_total += _d(item.get('total_amount', 0))

        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, party_id, date, due_date, reference_no,
             narration, total_amount, tax_amount, discount_amount, grand_total,
             balance_due, status, godown_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                voucher_no, 'Purchase Invoice', header['party_id'],
                date_str, header.get('due_date', ''),
                header.get('reference_no', ''), header.get('narration', ''),
                _r2(total_amount), _r2(tax_amount), _r2(discount_amount),
                _r2(grand_total), _r2(grand_total), 'Draft',
                header.get('godown_id', 1),
            ),
        )
        voucher_id = cursor.lastrowid

        for item in line_items:
            disc_amt = _d(item.get('qty', 0)) * _d(item.get('rate', 0)) * _d(item.get('discount_pct', 0)) / Decimal("100")
            conn.execute(
                """INSERT INTO voucher_items
                (voucher_id, item_id, description, hsn_code, qty, unit, rate,
                 discount_pct, discount_amount, taxable_amount, gst_rate,
                 cgst_rate, cgst_amount, sgst_rate, sgst_amount,
                 igst_rate, igst_amount, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    voucher_id, item['item_id'], item.get('description', ''),
                    item.get('hsn_code', ''), item['qty'], item.get('unit', ''),
                    item['rate'], item.get('discount_pct', 0), _r2(disc_amt),
                    _r2(_d(item.get('taxable_amount', 0))),
                    item.get('gst_rate', 0),
                    item.get('cgst_rate', 0), _r2(_d(item.get('cgst_amount', 0))),
                    item.get('sgst_rate', 0), _r2(_d(item.get('sgst_amount', 0))),
                    item.get('igst_rate', 0), _r2(_d(item.get('igst_amount', 0))),
                    _r2(_d(item.get('total_amount', 0))),
                ),
            )

        conn.commit()
        return True, f"Purchase Invoice {voucher_no} saved as Draft.", voucher_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error creating purchase invoice: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}", 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  PURCHASE INVOICE — CONFIRM (ITC journal entries + stock IN)
# ═══════════════════════════════════════════════════════════════════════

def confirm_purchase_invoice(voucher_id: int) -> tuple[bool, str]:
    """
    Confirm a draft Purchase Invoice:
    1. Update status to 'Confirmed'
    2. Insert ITC journal entries (debit CGST/SGST/IGST Input, credit supplier)
    3. Insert stock movements (IN)
    """
    conn = get_connection()
    try:
        v = conn.execute(
            "SELECT * FROM vouchers WHERE id = ? AND voucher_type = 'Purchase Invoice'",
            (voucher_id,)
        ).fetchone()
        if not v:
            return False, "Purchase Invoice not found."
        if v['status'] != 'Draft':
            return False, f"Invoice is already {v['status']}."

        conn.execute(
            "UPDATE vouchers SET status = 'Confirmed' WHERE id = ?",
            (voucher_id,),
        )

        items = conn.execute(
            "SELECT * FROM voucher_items WHERE voucher_id = ?", (voucher_id,)
        ).fetchall()

        date_str = v['date']
        narration = f"Purchase Invoice {v['voucher_no']}"
        grand_total = _d(v['grand_total'])
        total_taxable = Decimal("0")
        total_cgst = Decimal("0")
        total_sgst = Decimal("0")
        total_igst = Decimal("0")

        for item in items:
            total_taxable += _d(item['taxable_amount'])
            total_cgst += _d(item['cgst_amount'])
            total_sgst += _d(item['sgst_amount'])
            total_igst += _d(item['igst_amount'])

        # ── ITC Journal Entries ────────────────────────────────
        # Dr: Purchase Account → taxable total
        # Dr: CGST Input → cgst total (ITC)
        # Dr: SGST Input → sgst total (ITC)
        # Dr: IGST Input → igst total (ITC)
        # Cr: Supplier (Sundry Creditors) → grand total

        party_account_id = _ensure_party_account(conn, v['party_id'], 'supplier')
        purchase_id = _get_account_id(conn, 'Purchase')
        cgst_in_id = _get_account_id(conn, 'CGST Input')
        sgst_in_id = _get_account_id(conn, 'SGST Input')
        igst_in_id = _get_account_id(conn, 'IGST Input')

        # Dr: Purchase
        conn.execute(
            """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
            VALUES (?, ?, ?, ?, 0, ?)""",
            (voucher_id, purchase_id, date_str, _r2(total_taxable), narration),
        )
        # Dr: ITC accounts
        if total_cgst > 0:
            conn.execute(
                """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
                VALUES (?, ?, ?, ?, 0, ?)""",
                (voucher_id, cgst_in_id, date_str, _r2(total_cgst), narration),
            )
        if total_sgst > 0:
            conn.execute(
                """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
                VALUES (?, ?, ?, ?, 0, ?)""",
                (voucher_id, sgst_in_id, date_str, _r2(total_sgst), narration),
            )
        if total_igst > 0:
            conn.execute(
                """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
                VALUES (?, ?, ?, ?, 0, ?)""",
                (voucher_id, igst_in_id, date_str, _r2(total_igst), narration),
            )
        # Cr: Supplier
        conn.execute(
            """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
            VALUES (?, ?, ?, 0, ?, ?)""",
            (voucher_id, party_account_id, date_str, _r2(grand_total), narration),
        )

        # ── Stock Movements (IN) ──────────────────────────────
        godown_id = v['godown_id'] or 1
        for item in items:
            conn.execute(
                """INSERT INTO stock_movements
                (item_id, godown_id, voucher_id, movement_type, qty, rate, date, narration)
                VALUES (?, ?, ?, 'IN', ?, ?, ?, ?)""",
                (item['item_id'], godown_id, voucher_id,
                 item['qty'], item['rate'], date_str, narration),
            )
            _update_stock(conn, item['item_id'], godown_id, _d(item['qty']))

        conn.commit()
        return True, f"Purchase Invoice {v['voucher_no']} confirmed. Stock updated."

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error confirming purchase invoice: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  FETCH PURCHASE INVOICES
# ═══════════════════════════════════════════════════════════════════════

def get_purchase_invoices(status: str = '', search: str = '') -> list:
    """Fetch all purchase invoices, optionally filtered."""
    conn = get_connection()
    try:
        query = """
            SELECT v.*, p.name as party_name
            FROM vouchers v
            LEFT JOIN parties p ON v.party_id = p.id
            WHERE v.voucher_type = 'Purchase Invoice'
        """
        params = []
        if status and status != 'All':
            query += " AND v.status = ?"
            params.append(status)
        if search:
            query += " AND (v.voucher_no LIKE ? OR p.name LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s])
        query += " ORDER BY v.date DESC, v.id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching purchase invoices: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


def cancel_purchase_invoice(voucher_id: int) -> tuple[bool, str]:
    """Cancel a purchase invoice (only if Draft)."""
    conn = get_connection()
    try:
        v = conn.execute(
            "SELECT status, voucher_no FROM vouchers WHERE id = ?", (voucher_id,)
        ).fetchone()
        if not v:
            return False, "Invoice not found."
        if v['status'] != 'Draft':
            return False, f"Cannot cancel — invoice is {v['status']}."
        conn.execute(
            "UPDATE vouchers SET status = 'Cancelled' WHERE id = ?", (voucher_id,)
        )
        conn.commit()
        return True, f"Invoice {v['voucher_no']} cancelled."
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error cancelling purchase invoice: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()

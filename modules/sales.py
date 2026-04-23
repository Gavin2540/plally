"""
Sales module for PlywoodPro.
Business logic for Sales Invoices: create draft, confirm (with journal entries
and stock movements), fetch, and cancel. All monetary math uses Decimal.
"""

import sqlite3
import traceback
from decimal import Decimal, ROUND_HALF_UP
from db.connection import get_connection
from modules.masters import generate_voucher_no, get_company


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


# ═══════════════════════════════════════════════════════════════════════
#  SALES INVOICE — CREATE DRAFT
# ═══════════════════════════════════════════════════════════════════════

def create_sales_invoice(header: dict, line_items: list) -> tuple[bool, str, int]:
    """
    Create a Sales Invoice in Draft status.
    header keys: party_id, date, due_date, reference_no, narration, godown_id,
                 transport_name, vehicle_no
    line_items: list of dicts with keys: item_id, description, hsn_code, qty,
                unit, rate, discount_pct, gst_rate, cgst_rate, cgst_amount,
                sgst_rate, sgst_amount, igst_rate, igst_amount,
                taxable_amount, total_amount
    Returns (success, message, voucher_id).
    """
    conn = get_connection()
    try:
        # Generate voucher number
        date_str = header.get('date', '')
        voucher_no = generate_voucher_no(conn, 'Sales Invoice', date_str)

        # Calculate totals from line items using Decimal
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

        # Insert voucher header
        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, party_id, date, due_date, reference_no,
             narration, total_amount, tax_amount, discount_amount, grand_total,
             balance_due, status, godown_id, transport_name, vehicle_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                voucher_no, 'Sales Invoice', header['party_id'],
                date_str, header.get('due_date', ''),
                header.get('reference_no', ''), header.get('narration', ''),
                _r2(total_amount), _r2(tax_amount), _r2(discount_amount),
                _r2(grand_total), _r2(grand_total), 'Draft',
                header.get('godown_id', 1),
                header.get('transport_name', ''), header.get('vehicle_no', ''),
            ),
        )
        voucher_id = cursor.lastrowid

        # Insert line items
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
        return True, f"Sales Invoice {voucher_no} saved as Draft.", voucher_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error creating sales invoice: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}", 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  SALES INVOICE — CONFIRM (creates journal entries + stock movements)
# ═══════════════════════════════════════════════════════════════════════

def confirm_sales_invoice(voucher_id: int) -> tuple[bool, str]:
    """
    Confirm a draft Sales Invoice:
    1. Update status to 'Confirmed'
    2. Insert journal entries (double-entry)
    3. Insert stock movements (OUT)
    """
    conn = get_connection()
    try:
        # Fetch voucher
        v = conn.execute(
            "SELECT * FROM vouchers WHERE id = ? AND voucher_type = 'Sales Invoice'",
            (voucher_id,)
        ).fetchone()
        if not v:
            return False, "Sales Invoice not found."
        if v['status'] != 'Draft':
            return False, f"Invoice is already {v['status']}."

        # Update status
        conn.execute(
            "UPDATE vouchers SET status = 'Confirmed' WHERE id = ?",
            (voucher_id,),
        )

        # Fetch line items
        items = conn.execute(
            "SELECT * FROM voucher_items WHERE voucher_id = ?", (voucher_id,)
        ).fetchall()

        date_str = v['date']
        narration = f"Sales Invoice {v['voucher_no']}"
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

        # ── Journal Entries ────────────────────────────────────
        # Dr: Party (Sundry Debtors) → grand_total
        # Cr: Sales Account → taxable total
        # Cr: CGST Payable → cgst total
        # Cr: SGST Payable → sgst total
        # Cr: IGST Payable → igst total

        # Get/create party ledger account
        party_account_id = _ensure_party_account(conn, v['party_id'], 'customer')
        sales_id = _get_account_id(conn, 'Sales')
        cgst_pay_id = _get_account_id(conn, 'CGST Payable')
        sgst_pay_id = _get_account_id(conn, 'SGST Payable')
        igst_pay_id = _get_account_id(conn, 'IGST Payable')

        # Dr: Party
        conn.execute(
            """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
            VALUES (?, ?, ?, ?, 0, ?)""",
            (voucher_id, party_account_id, date_str, _r2(grand_total), narration),
        )
        # Cr: Sales
        conn.execute(
            """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
            VALUES (?, ?, ?, 0, ?, ?)""",
            (voucher_id, sales_id, date_str, _r2(total_taxable), narration),
        )
        # Cr: Tax accounts
        if total_cgst > 0:
            conn.execute(
                """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
                VALUES (?, ?, ?, 0, ?, ?)""",
                (voucher_id, cgst_pay_id, date_str, _r2(total_cgst), narration),
            )
        if total_sgst > 0:
            conn.execute(
                """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
                VALUES (?, ?, ?, 0, ?, ?)""",
                (voucher_id, sgst_pay_id, date_str, _r2(total_sgst), narration),
            )
        if total_igst > 0:
            conn.execute(
                """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
                VALUES (?, ?, ?, 0, ?, ?)""",
                (voucher_id, igst_pay_id, date_str, _r2(total_igst), narration),
            )

        # ── Stock Movements (OUT) ──────────────────────────────
        godown_id = v['godown_id'] or 1
        for item in items:
            # Record stock OUT
            conn.execute(
                """INSERT INTO stock_movements
                (item_id, godown_id, voucher_id, movement_type, qty, rate, date, narration)
                VALUES (?, ?, ?, 'OUT', ?, ?, ?, ?)""",
                (item['item_id'], godown_id, voucher_id,
                 item['qty'], item['rate'], date_str, narration),
            )
            # Update stock table
            _update_stock(conn, item['item_id'], godown_id, -_d(item['qty']))

        conn.commit()
        return True, f"Sales Invoice {v['voucher_no']} confirmed."

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error confirming sales invoice: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  FETCH INVOICES
# ═══════════════════════════════════════════════════════════════════════

def get_sales_invoices(status: str = '', search: str = '') -> list:
    """Fetch all sales invoices, optionally filtered by status or search."""
    conn = get_connection()
    try:
        query = """
            SELECT v.*, p.name as party_name
            FROM vouchers v
            LEFT JOIN parties p ON v.party_id = p.id
            WHERE v.voucher_type = 'Sales Invoice'
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
        print(f"[PlywoodPro] Error fetching sales invoices: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


def get_voucher_with_items(voucher_id: int) -> tuple[dict | None, list]:
    """Fetch a voucher header and its line items."""
    conn = get_connection()
    try:
        v = conn.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,)).fetchone()
        items = conn.execute(
            "SELECT * FROM voucher_items WHERE voucher_id = ?", (voucher_id,)
        ).fetchall()
        return (dict(v) if v else None, [dict(i) for i in items])
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching voucher {voucher_id}: {e}")
        traceback.print_exc()
        return None, []
    finally:
        conn.close()


def cancel_sales_invoice(voucher_id: int) -> tuple[bool, str]:
    """Cancel a sales invoice (only if Draft)."""
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
        print(f"[PlywoodPro] Error cancelling invoice: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════

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

    # Auto-create
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
#  SALES ORDER — CREATE / CONFIRM / CONVERT
# ═══════════════════════════════════════════════════════════════════════

def create_sales_order(header: dict, line_items: list) -> tuple[bool, str, int]:
    """
    Create a Sales Order in Draft status.
    Orders have no GST columns — only Subtotal, Discount, Grand Total.
    """
    conn = get_connection()
    try:
        date_str = header.get('date', '')
        voucher_no = generate_voucher_no(conn, 'Sales Order', date_str)

        total_amount = Decimal("0")
        discount_amount = Decimal("0")
        grand_total = Decimal("0")

        for item in line_items:
            qty = _d(item.get('qty', 0))
            rate = _d(item.get('rate', 0))
            disc_pct = _d(item.get('discount_pct', 0))
            gross = qty * rate
            disc = gross * disc_pct / Decimal("100")
            line_total = gross - disc
            total_amount += gross
            discount_amount += disc
            grand_total += line_total

        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, party_id, date, due_date, reference_no,
             narration, total_amount, discount_amount, grand_total,
             balance_due, status, godown_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                voucher_no, 'Sales Order', header['party_id'],
                date_str, header.get('due_date', ''),
                header.get('reference_no', ''), header.get('narration', ''),
                _r2(total_amount), _r2(discount_amount),
                _r2(grand_total), _r2(grand_total), 'Draft',
                header.get('godown_id', 1),
            ),
        )
        voucher_id = cursor.lastrowid

        for item in line_items:
            qty = _d(item.get('qty', 0))
            rate = _d(item.get('rate', 0))
            disc_pct = _d(item.get('discount_pct', 0))
            gross = qty * rate
            disc_amt = gross * disc_pct / Decimal("100")
            line_total = gross - disc_amt

            conn.execute(
                """INSERT INTO voucher_items
                (voucher_id, item_id, description, hsn_code, qty, unit, rate,
                 discount_pct, discount_amount, taxable_amount,
                 gst_rate, cgst_rate, cgst_amount, sgst_rate, sgst_amount,
                 igst_rate, igst_amount, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, ?)""",
                (
                    voucher_id, item['item_id'], item.get('description', ''),
                    item.get('hsn_code', ''), float(qty), item.get('unit', ''),
                    float(rate), float(disc_pct), _r2(disc_amt),
                    _r2(line_total), _r2(line_total),
                ),
            )

        conn.commit()
        return True, f"Sales Order {voucher_no} saved as Draft.", voucher_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error creating sales order: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}", 0
    finally:
        conn.close()


def confirm_sales_order(voucher_id: int) -> tuple[bool, str]:
    """Confirm a draft Sales Order."""
    conn = get_connection()
    try:
        v = conn.execute(
            "SELECT * FROM vouchers WHERE id = ? AND voucher_type = 'Sales Order'",
            (voucher_id,)
        ).fetchone()
        if not v:
            return False, "Sales Order not found."
        if v['status'] != 'Draft':
            return False, f"Order is already {v['status']}."
        conn.execute(
            "UPDATE vouchers SET status = 'Confirmed' WHERE id = ?",
            (voucher_id,),
        )
        conn.commit()
        return True, f"Sales Order {v['voucher_no']} confirmed."
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error confirming sales order: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def get_sales_orders(status: str = '', search: str = '') -> list:
    """Fetch all sales orders, optionally filtered."""
    conn = get_connection()
    try:
        query = """
            SELECT v.*, p.name as party_name
            FROM vouchers v LEFT JOIN parties p ON v.party_id = p.id
            WHERE v.voucher_type = 'Sales Order'
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
        print(f"[PlywoodPro] Error fetching sales orders: {e}")
        return []
    finally:
        conn.close()


def convert_so_to_invoice(so_id: int) -> tuple[bool, str, int]:
    """
    Convert a confirmed Sales Order to a Sales Invoice.
    Copies header + line items, marks SO as 'Converted'.
    Returns (success, message, new_invoice_id).
    """
    conn = get_connection()
    try:
        so = conn.execute(
            "SELECT * FROM vouchers WHERE id = ? AND voucher_type = 'Sales Order'",
            (so_id,)
        ).fetchone()
        if not so:
            return False, "Sales Order not found.", 0
        if so['status'] not in ('Confirmed', 'Draft'):
            return False, f"Cannot convert — order is {so['status']}.", 0

        items = conn.execute(
            "SELECT * FROM voucher_items WHERE voucher_id = ?", (so_id,)
        ).fetchall()

        date_str = so['date']
        inv_no = generate_voucher_no(conn, 'Sales Invoice', date_str)

        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, party_id, date, due_date, reference_no,
             narration, total_amount, tax_amount, discount_amount, grand_total,
             balance_due, status, godown_id)
            VALUES (?, 'Sales Invoice', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Draft', ?)""",
            (
                inv_no, so['party_id'], date_str, so['due_date'] or '',
                so['voucher_no'], so['narration'] or '',
                so['total_amount'], so['tax_amount'] or 0,
                so['discount_amount'], so['grand_total'],
                so['grand_total'], so['godown_id'] or 1,
            ),
        )
        inv_id = cursor.lastrowid

        for item in items:
            conn.execute(
                """INSERT INTO voucher_items
                (voucher_id, item_id, description, hsn_code, qty, unit, rate,
                 discount_pct, discount_amount, taxable_amount, gst_rate,
                 cgst_rate, cgst_amount, sgst_rate, sgst_amount,
                 igst_rate, igst_amount, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    inv_id, item['item_id'], item['description'],
                    item['hsn_code'], item['qty'], item['unit'], item['rate'],
                    item['discount_pct'], item['discount_amount'],
                    item['taxable_amount'], item['gst_rate'],
                    item['cgst_rate'], item['cgst_amount'],
                    item['sgst_rate'], item['sgst_amount'],
                    item['igst_rate'], item['igst_amount'],
                    item['total_amount'],
                ),
            )

        # Mark SO as Converted
        conn.execute(
            "UPDATE vouchers SET status = 'Converted' WHERE id = ?", (so_id,)
        )

        conn.commit()
        return True, f"Converted to Sales Invoice {inv_no}.", inv_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error converting SO to invoice: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}", 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  RECEIPTS (money received from customers)
# ═══════════════════════════════════════════════════════════════════════

def get_outstanding_invoices(party_id: int, voucher_type: str = 'Sales Invoice') -> list:
    """
    Fetch outstanding (unpaid/partial) invoices for a party.
    Returns list of dicts with voucher_no, date, grand_total, paid_amount, balance_due.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, voucher_no, date, grand_total, paid_amount, balance_due
            FROM vouchers
            WHERE party_id = ? AND voucher_type = ?
              AND status IN ('Confirmed', 'Partial')
              AND balance_due > 0
            ORDER BY date ASC""",
            (party_id, voucher_type),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching outstanding invoices: {e}")
        return []
    finally:
        conn.close()


def create_receipt(party_id: int, invoice_id: int, amount: float,
                   mode: str, reference_no: str, date_str: str,
                   narration: str = '') -> tuple[bool, str, int]:
    """
    Create a Receipt: money received from a customer.
    - Dr: Cash/Bank
    - Cr: Party (Sundry Debtors)
    - Updates invoice paid_amount and balance_due
    Returns (success, message, receipt_voucher_id).
    """
    conn = get_connection()
    try:
        # Validate invoice
        inv = conn.execute(
            "SELECT * FROM vouchers WHERE id = ? AND voucher_type = 'Sales Invoice'",
            (invoice_id,)
        ).fetchone()
        if not inv:
            return False, "Invoice not found.", 0
        if _d(amount) > _d(inv['balance_due']):
            return False, f"Amount ₹{amount} exceeds balance due ₹{inv['balance_due']}.", 0
        if _d(amount) <= 0:
            return False, "Amount must be greater than zero.", 0

        voucher_no = generate_voucher_no(conn, 'Receipt', date_str)

        # Create receipt voucher
        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, party_id, date, reference_no, narration,
             grand_total, paid_amount, status)
            VALUES (?, 'Receipt', ?, ?, ?, ?, ?, ?, 'Confirmed')""",
            (voucher_no, party_id, date_str, reference_no,
             narration or f"Receipt against {inv['voucher_no']}",
             amount, amount),
        )
        rcp_id = cursor.lastrowid

        # Record in payments table
        cash_id = _get_account_id(conn, 'Cash')
        conn.execute(
            """INSERT INTO payments
            (voucher_id, party_id, payment_type, mode, amount, date, reference_no, narration)
            VALUES (?, ?, 'Receipt', ?, ?, ?, ?, ?)""",
            (rcp_id, party_id, mode, amount, date_str, reference_no,
             narration or f"Receipt against {inv['voucher_no']}"),
        )

        # Update invoice balance
        new_paid = _r2(_d(inv['paid_amount']) + _d(amount))
        new_balance = _r2(_d(inv['grand_total']) - _d(new_paid))
        new_status = 'Paid' if new_balance <= 0.01 else 'Partial'
        conn.execute(
            """UPDATE vouchers SET paid_amount = ?, balance_due = ?, status = ?
            WHERE id = ?""",
            (new_paid, max(new_balance, 0), new_status, invoice_id),
        )

        # Journal entries: Dr Cash, Cr Debtor
        party_account_id = _ensure_party_account(conn, party_id, 'customer')
        je_narration = f"Receipt {voucher_no} against {inv['voucher_no']}"

        conn.execute(
            """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
            VALUES (?, ?, ?, ?, 0, ?)""",
            (rcp_id, cash_id, date_str, amount, je_narration),
        )
        conn.execute(
            """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
            VALUES (?, ?, ?, 0, ?, ?)""",
            (rcp_id, party_account_id, date_str, amount, je_narration),
        )

        conn.commit()
        return True, f"Receipt {voucher_no} created for ₹{amount}.", rcp_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error creating receipt: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}", 0
    finally:
        conn.close()


def get_receipts(date_from: str = '', date_to: str = '') -> list:
    """Fetch all receipts."""
    conn = get_connection()
    try:
        query = """
            SELECT v.id, v.voucher_no, v.date, p.name as party_name,
                   v.grand_total as amount, pm.mode, pm.reference_no
            FROM vouchers v
            LEFT JOIN parties p ON v.party_id = p.id
            LEFT JOIN payments pm ON pm.voucher_id = v.id
            WHERE v.voucher_type = 'Receipt'
        """
        params = []
        if date_from:
            query += " AND v.date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND v.date <= ?"
            params.append(date_to)
        query += " ORDER BY v.date DESC, v.id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching receipts: {e}")
        return []
    finally:
        conn.close()

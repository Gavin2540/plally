"""
Inventory module for PlywoodPro.
Business logic for GRN, stock view, stock adjustments, godown transfers,
movement reports, and low stock detection.
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


def _update_stock(conn, item_id: int, godown_id: int, qty_change: Decimal):
    """
    Update the stock table atomically.
    qty_change is positive for additions, negative for reductions.
    Creates the row if it doesn't exist.
    """
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
#  GRN — GOODS RECEIPT NOTE
# ═══════════════════════════════════════════════════════════════════════

def create_grn(header: dict, line_items: list) -> tuple[bool, str, int]:
    """
    Create and confirm a Goods Receipt Note.
    Standalone or linked to a Purchase Order via reference_no.

    header keys: party_id, date, reference_no, narration, godown_id
    line_items: list of dicts with item_id, description, hsn_code,
                qty, unit, rate

    On confirm: inserts into vouchers, voucher_items, stock_movements,
    and updates the stock table.

    Returns (success, message, voucher_id).
    """
    conn = get_connection()
    try:
        date_str = header.get('date', '')
        voucher_no = generate_voucher_no(conn, 'GRN', date_str)
        godown_id = header.get('godown_id', 1)

        # Calculate totals
        total_amount = Decimal("0")
        for item in line_items:
            line_total = _d(item.get('qty', 0)) * _d(item.get('rate', 0))
            total_amount += line_total

        # Insert voucher header
        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, party_id, date, reference_no,
             narration, total_amount, grand_total, status, godown_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                voucher_no, 'GRN', header.get('party_id'),
                date_str, header.get('reference_no', ''),
                header.get('narration', ''),
                _r2(total_amount), _r2(total_amount),
                'Confirmed', godown_id,
            ),
        )
        voucher_id = cursor.lastrowid

        # Insert line items + stock movements + update stock
        for item in line_items:
            qty = _d(item.get('qty', 0))
            rate = _d(item.get('rate', 0))
            line_total = qty * rate

            conn.execute(
                """INSERT INTO voucher_items
                (voucher_id, item_id, description, hsn_code, qty, unit,
                 rate, taxable_amount, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    voucher_id, item['item_id'],
                    item.get('description', ''), item.get('hsn_code', ''),
                    float(qty), item.get('unit', ''),
                    float(rate), _r2(line_total), _r2(line_total),
                ),
            )

            # Stock movement IN
            conn.execute(
                """INSERT INTO stock_movements
                (item_id, godown_id, voucher_id, movement_type, qty, rate, date, narration)
                VALUES (?, ?, ?, 'IN', ?, ?, ?, ?)""",
                (
                    item['item_id'], godown_id, voucher_id,
                    float(qty), float(rate), date_str,
                    f"GRN {voucher_no}",
                ),
            )

            # Update stock table
            _update_stock(conn, item['item_id'], godown_id, qty)

        conn.commit()
        return True, f"GRN {voucher_no} confirmed. Stock updated.", voucher_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error creating GRN: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}", 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  STOCK VIEW / SUMMARY
# ═══════════════════════════════════════════════════════════════════════

def get_stock_summary(godown_id: int = 0, category: str = '') -> list:
    """
    Get current stock per item per godown with reorder flag.
    If godown_id is 0, returns all godowns.
    Returns list of dicts with: item_id, item_name, category, hsn_code,
    unit, godown_id, godown_name, qty, reorder_level, is_low_stock.
    """
    conn = get_connection()
    try:
        query = """
            SELECT
                s.item_id, i.name AS item_name, i.category, i.hsn_code,
                i.unit, i.thickness, i.size,
                s.godown_id, g.name AS godown_name,
                s.qty, i.reorder_level,
                CASE WHEN s.qty <= i.reorder_level THEN 1 ELSE 0 END AS is_low_stock
            FROM stock s
            JOIN items i ON s.item_id = i.id AND i.is_active = 1
            JOIN godowns g ON s.godown_id = g.id AND g.is_active = 1
            WHERE 1=1
        """
        params = []

        if godown_id > 0:
            query += " AND s.godown_id = ?"
            params.append(godown_id)

        if category and category != 'All':
            query += " AND i.category = ?"
            params.append(category)

        query += " ORDER BY i.name ASC, g.name ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching stock summary: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  STOCK ADJUSTMENT
# ═══════════════════════════════════════════════════════════════════════

ADJUSTMENT_REASONS = ['Damage', 'Breakage', 'Theft', 'Moisture Damage', 'Other']


def create_stock_adjustment(
    item_id: int, godown_id: int, adj_type: str,
    qty: float, reason: str, narration: str = ''
) -> tuple[bool, str]:
    """
    Create a stock adjustment.
    adj_type: 'Add' or 'Reduce'
    reason: one of ADJUSTMENT_REASONS
    qty: always positive — direction determined by adj_type.

    Inserts into vouchers (type='Stock Adjustment'), stock_movements,
    and updates the stock table.
    """
    if qty <= 0:
        return False, "Quantity must be greater than 0."
    if reason not in ADJUSTMENT_REASONS:
        return False, f"Invalid reason. Must be one of: {', '.join(ADJUSTMENT_REASONS)}"

    conn = get_connection()
    try:
        date_str = conn.execute(
            "SELECT date('now','localtime')"
        ).fetchone()[0]

        # Check current stock if reducing
        if adj_type == 'Reduce':
            current = conn.execute(
                "SELECT qty FROM stock WHERE item_id = ? AND godown_id = ?",
                (item_id, godown_id)
            ).fetchone()
            current_qty = _d(current['qty']) if current else Decimal("0")
            if current_qty < _d(qty):
                return False, f"Insufficient stock. Current: {_r2(current_qty)}, requested: {qty}"

        # Create voucher for audit trail
        voucher_no = generate_voucher_no(conn, 'Stock Adjustment', date_str)
        full_narration = f"{adj_type}: {reason}" + (f" - {narration}" if narration else "")

        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, date, narration, status, godown_id)
            VALUES (?, 'Stock Adjustment', ?, ?, 'Confirmed', ?)""",
            (voucher_no, date_str, full_narration, godown_id),
        )
        voucher_id = cursor.lastrowid

        # Determine qty direction
        qty_decimal = _d(qty)
        if adj_type == 'Reduce':
            stock_change = -qty_decimal
            movement_qty = float(qty)  # always positive in stock_movements
        else:
            stock_change = qty_decimal
            movement_qty = float(qty)

        # Stock movement
        conn.execute(
            """INSERT INTO stock_movements
            (item_id, godown_id, voucher_id, movement_type, qty, date, narration)
            VALUES (?, ?, ?, 'ADJUSTMENT', ?, ?, ?)""",
            (item_id, godown_id, voucher_id, movement_qty, date_str, full_narration),
        )

        # Update stock
        _update_stock(conn, item_id, godown_id, stock_change)

        conn.commit()
        action = "added to" if adj_type == 'Add' else "reduced from"
        return True, f"Stock adjustment {voucher_no}: {qty} units {action} stock. Reason: {reason}"

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error creating stock adjustment: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  GODOWN TRANSFER
# ═══════════════════════════════════════════════════════════════════════

def create_godown_transfer(
    item_id: int, from_godown_id: int, to_godown_id: int,
    qty: float, narration: str = ''
) -> tuple[bool, str]:
    """
    Transfer stock from one godown to another.
    Creates two stock_movements (OUT from source, IN to destination)
    and updates both stock rows.
    """
    if qty <= 0:
        return False, "Quantity must be greater than 0."
    if from_godown_id == to_godown_id:
        return False, "Source and destination godown must be different."

    conn = get_connection()
    try:
        # Check source stock
        source = conn.execute(
            "SELECT qty FROM stock WHERE item_id = ? AND godown_id = ?",
            (item_id, from_godown_id)
        ).fetchone()
        source_qty = _d(source['qty']) if source else Decimal("0")

        if source_qty < _d(qty):
            return False, f"Insufficient stock in source. Available: {_r2(source_qty)}, requested: {qty}"

        date_str = conn.execute(
            "SELECT date('now','localtime')"
        ).fetchone()[0]

        # Get godown names for narration
        from_name = conn.execute(
            "SELECT name FROM godowns WHERE id = ?", (from_godown_id,)
        ).fetchone()
        to_name = conn.execute(
            "SELECT name FROM godowns WHERE id = ?", (to_godown_id,)
        ).fetchone()
        from_label = from_name['name'] if from_name else str(from_godown_id)
        to_label = to_name['name'] if to_name else str(to_godown_id)

        transfer_narr = f"Transfer: {from_label} -> {to_label}"
        if narration:
            transfer_narr += f" ({narration})"

        # We don't have a 'Transfer' voucher type in voucher_sequences,
        # so we use the Stock Adjustment sequence for tracking
        voucher_no = generate_voucher_no(conn, 'Stock Adjustment', date_str)

        cursor = conn.execute(
            """INSERT INTO vouchers
            (voucher_no, voucher_type, date, narration, status, godown_id)
            VALUES (?, 'Stock Adjustment', ?, ?, 'Confirmed', ?)""",
            (voucher_no, date_str, transfer_narr, from_godown_id),
        )
        voucher_id = cursor.lastrowid

        qty_decimal = _d(qty)

        # OUT from source godown
        conn.execute(
            """INSERT INTO stock_movements
            (item_id, godown_id, voucher_id, movement_type, qty, date, narration)
            VALUES (?, ?, ?, 'TRANSFER', ?, ?, ?)""",
            (item_id, from_godown_id, voucher_id, float(qty), date_str,
             f"Transfer OUT to {to_label}"),
        )
        _update_stock(conn, item_id, from_godown_id, -qty_decimal)

        # IN to destination godown
        conn.execute(
            """INSERT INTO stock_movements
            (item_id, godown_id, voucher_id, movement_type, qty, date, narration)
            VALUES (?, ?, ?, 'TRANSFER', ?, ?, ?)""",
            (item_id, to_godown_id, voucher_id, float(qty), date_str,
             f"Transfer IN from {from_label}"),
        )
        _update_stock(conn, item_id, to_godown_id, qty_decimal)

        conn.commit()
        return True, f"Transfer {voucher_no}: {qty} units moved from {from_label} to {to_label}."

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error creating godown transfer: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}"
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  STOCK MOVEMENT REPORT
# ═══════════════════════════════════════════════════════════════════════

def get_stock_movement_report(
    item_id: int = 0, godown_id: int = 0,
    date_from: str = '', date_to: str = '',
    movement_type: str = ''
) -> list:
    """
    Full audit trail of stock movements, filterable by item, godown,
    date range, and movement type.
    Returns list of dicts.
    """
    conn = get_connection()
    try:
        query = """
            SELECT
                sm.id, sm.item_id, i.name AS item_name,
                sm.godown_id, g.name AS godown_name,
                sm.voucher_id, v.voucher_no,
                sm.movement_type, sm.qty, sm.rate,
                sm.date, sm.narration, sm.created_at
            FROM stock_movements sm
            JOIN items i ON sm.item_id = i.id
            JOIN godowns g ON sm.godown_id = g.id
            LEFT JOIN vouchers v ON sm.voucher_id = v.id
            WHERE 1=1
        """
        params = []

        if item_id > 0:
            query += " AND sm.item_id = ?"
            params.append(item_id)
        if godown_id > 0:
            query += " AND sm.godown_id = ?"
            params.append(godown_id)
        if date_from:
            query += " AND sm.date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND sm.date <= ?"
            params.append(date_to)
        if movement_type and movement_type != 'All':
            query += " AND sm.movement_type = ?"
            params.append(movement_type)

        query += " ORDER BY sm.date DESC, sm.id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching movement report: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  LOW STOCK ITEMS
# ═══════════════════════════════════════════════════════════════════════

def get_low_stock_items() -> list:
    """
    Get items where current stock <= reorder_level.
    Only includes items with reorder_level > 0.
    Returns list of dicts with item info, stock qty, and deficit.
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                i.id AS item_id, i.name AS item_name, i.category,
                i.unit, i.reorder_level,
                COALESCE(SUM(s.qty), 0) AS total_qty,
                g.name AS godown_name
            FROM items i
            LEFT JOIN stock s ON i.id = s.item_id
            LEFT JOIN godowns g ON s.godown_id = g.id
            WHERE i.is_active = 1
              AND i.reorder_level > 0
            GROUP BY i.id
            HAVING total_qty <= i.reorder_level
            ORDER BY (i.reorder_level - total_qty) DESC
        """).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching low stock items: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()

"""
Reports module for PlywoodPro.
Dashboard stats, Sales/Purchase registers, Party outstanding,
Item profit, Stock valuation.
"""
import sqlite3, traceback
from decimal import Decimal, ROUND_HALF_UP
from db.connection import get_connection

def _d(v):
    if v is None: return Decimal("0")
    return Decimal(str(v))
def _r2(v): return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_dashboard_stats() -> dict:
    conn = get_connection()
    try:
        today = conn.execute("SELECT date('now','localtime')").fetchone()[0]

        sales = conn.execute(
            "SELECT COALESCE(SUM(grand_total),0) FROM vouchers WHERE voucher_type='Sales Invoice' AND status='Confirmed' AND date=?",
            (today,)).fetchone()[0]

        receivables = conn.execute(
            "SELECT COALESCE(SUM(balance_due),0) FROM vouchers WHERE voucher_type='Sales Invoice' AND status='Confirmed' AND balance_due>0"
        ).fetchone()[0]

        payables = conn.execute(
            "SELECT COALESCE(SUM(balance_due),0) FROM vouchers WHERE voucher_type='Purchase Invoice' AND status='Confirmed' AND balance_due>0"
        ).fetchone()[0]

        low_stock = conn.execute(
            """SELECT COUNT(*) FROM items i
               JOIN stock s ON i.id=s.item_id
               WHERE i.is_active=1 AND i.reorder_level>0 AND s.qty<=i.reorder_level"""
        ).fetchone()[0]

        pending_dc = conn.execute(
            "SELECT COUNT(*) FROM vouchers WHERE voucher_type='Delivery Challan' AND status='Draft'"
        ).fetchone()[0]

        recent = conn.execute(
            """SELECT v.voucher_no, v.date, p.name AS party_name, v.grand_total, v.status
               FROM vouchers v LEFT JOIN parties p ON v.party_id=p.id
               WHERE v.voucher_type='Sales Invoice' ORDER BY v.id DESC LIMIT 5"""
        ).fetchall()

        return {
            'today_sales': float(sales or 0),
            'receivables': float(receivables or 0),
            'payables': float(payables or 0),
            'low_stock_count': int(low_stock or 0),
            'pending_challans': int(pending_dc or 0),
            'recent_invoices': [dict(r) for r in recent],
            'today': today,
        }
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Dashboard error: {e}"); traceback.print_exc()
        return {'today_sales':0,'receivables':0,'payables':0,'low_stock_count':0,'pending_challans':0,'recent_invoices':[],'today':''}
    finally:
        conn.close()


def get_sales_register(date_from='', date_to='') -> list:
    conn = get_connection()
    try:
        q = """SELECT v.date, v.voucher_no, p.name AS party_name,
                      v.total_amount AS taxable_amount, v.tax_amount,
                      v.grand_total, v.status,
                      COALESCE(SUM(vi.cgst_amount),0) AS cgst,
                      COALESCE(SUM(vi.sgst_amount),0) AS sgst,
                      COALESCE(SUM(vi.igst_amount),0) AS igst
               FROM vouchers v
               LEFT JOIN parties p ON v.party_id=p.id
               LEFT JOIN voucher_items vi ON v.id=vi.voucher_id
               WHERE v.voucher_type='Sales Invoice' AND v.status='Confirmed'"""
        params = []
        if date_from: q += " AND v.date >= ?"; params.append(date_from)
        if date_to: q += " AND v.date <= ?"; params.append(date_to)
        q += " GROUP BY v.id ORDER BY v.date DESC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Sales register error: {e}"); return []
    finally: conn.close()


def get_purchase_register(date_from='', date_to='') -> list:
    conn = get_connection()
    try:
        q = """SELECT v.date, v.voucher_no, p.name AS party_name,
                      v.total_amount AS taxable_amount, v.tax_amount,
                      v.grand_total, v.status,
                      COALESCE(SUM(vi.cgst_amount),0) AS cgst,
                      COALESCE(SUM(vi.sgst_amount),0) AS sgst,
                      COALESCE(SUM(vi.igst_amount),0) AS igst
               FROM vouchers v
               LEFT JOIN parties p ON v.party_id=p.id
               LEFT JOIN voucher_items vi ON v.id=vi.voucher_id
               WHERE v.voucher_type='Purchase Invoice' AND v.status='Confirmed'"""
        params = []
        if date_from: q += " AND v.date >= ?"; params.append(date_from)
        if date_to: q += " AND v.date <= ?"; params.append(date_to)
        q += " GROUP BY v.id ORDER BY v.date DESC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Purchase register error: {e}"); return []
    finally: conn.close()


def get_party_outstanding(party_type='both') -> list:
    conn = get_connection()
    try:
        q = """SELECT p.name AS party_name, p.type,
                      COALESCE(SUM(v.grand_total),0) AS total_invoiced,
                      COALESCE(SUM(v.paid_amount),0) AS total_paid,
                      COALESCE(SUM(v.balance_due),0) AS balance,
                      MIN(v.date) AS oldest_invoice_date
               FROM parties p
               JOIN vouchers v ON v.party_id=p.id AND v.status='Confirmed'
               WHERE 1=1"""
        params = []
        if party_type == 'customer':
            q += " AND v.voucher_type='Sales Invoice'"
        elif party_type == 'supplier':
            q += " AND v.voucher_type='Purchase Invoice'"
        else:
            q += " AND v.voucher_type IN ('Sales Invoice','Purchase Invoice')"
        q += " GROUP BY p.id ORDER BY balance DESC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Party outstanding error: {e}"); return []
    finally: conn.close()


def get_item_profit_report() -> list:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT i.name AS item_name, i.hsn_code,
                   COALESCE(pu.total_qty,0) AS purchased_qty,
                   COALESCE(pu.avg_rate,0) AS avg_purchase_rate,
                   COALESCE(sa.total_qty,0) AS sold_qty,
                   COALESCE(sa.avg_rate,0) AS avg_sale_rate
            FROM items i
            LEFT JOIN (
                SELECT vi.item_id, SUM(vi.qty) AS total_qty, AVG(vi.rate) AS avg_rate
                FROM voucher_items vi JOIN vouchers v ON vi.voucher_id=v.id
                WHERE v.voucher_type='Purchase Invoice' AND v.status='Confirmed'
                GROUP BY vi.item_id
            ) pu ON i.id=pu.item_id
            LEFT JOIN (
                SELECT vi.item_id, SUM(vi.qty) AS total_qty, AVG(vi.rate) AS avg_rate
                FROM voucher_items vi JOIN vouchers v ON vi.voucher_id=v.id
                WHERE v.voucher_type='Sales Invoice' AND v.status='Confirmed'
                GROUP BY vi.item_id
            ) sa ON i.id=sa.item_id
            WHERE i.is_active=1 AND (pu.total_qty>0 OR sa.total_qty>0)
            ORDER BY i.name
        """).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            buy = _d(d['avg_purchase_rate']); sell = _d(d['avg_sale_rate'])
            sold_qty = _d(d['sold_qty'])
            gross = (sell - buy) * sold_qty
            margin = (_r2((sell - buy) / sell * 100)) if sell > 0 else 0
            d['gross_profit'] = _r2(gross)
            d['margin_pct'] = margin
            result.append(d)
        return result
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Item profit error: {e}"); return []
    finally: conn.close()


def get_stock_valuation_report() -> list:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT i.name AS item_name, i.hsn_code, i.unit,
                   g.name AS godown_name, s.qty,
                   COALESCE(
                       (SELECT AVG(vi.rate) FROM voucher_items vi
                        JOIN vouchers v ON vi.voucher_id=v.id
                        WHERE vi.item_id=i.id AND v.voucher_type='Purchase Invoice'
                        AND v.status='Confirmed'), 0
                   ) AS avg_rate
            FROM stock s
            JOIN items i ON s.item_id=i.id AND i.is_active=1
            JOIN godowns g ON s.godown_id=g.id
            WHERE s.qty > 0
            ORDER BY i.name, g.name
        """).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['stock_value'] = _r2(_d(d['qty']) * _d(d['avg_rate']))
            result.append(d)
        return result
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Stock valuation error: {e}"); return []
    finally: conn.close()

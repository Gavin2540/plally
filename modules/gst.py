"""
GST Reporting module for PlywoodPro.
GSTR-1 (B2B, B2C, CDNR, HSN Summary), GSTR-3B, ITC Register,
Monthly GST Summary.
"""

import sqlite3
import traceback
from decimal import Decimal, ROUND_HALF_UP
from db.connection import get_connection


def _d(val) -> Decimal:
    if val is None: return Decimal("0")
    return Decimal(str(val))

def _r2(val: Decimal) -> float:
    return float(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ═══════════════════════════════════════════════════════════════════════
#  GSTR-1 B2B — Sales to GST-registered parties
# ═══════════════════════════════════════════════════════════════════════

def get_gstr1_b2b(month: int, year: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.gstin, p.name AS party_name, v.voucher_no, v.date,
                   vi.taxable_amount, vi.cgst_amount, vi.sgst_amount,
                   vi.igst_amount, vi.total_amount, vi.gst_rate
            FROM vouchers v
            JOIN parties p ON v.party_id = p.id
            JOIN voucher_items vi ON v.id = vi.voucher_id
            WHERE v.voucher_type = 'Sales Invoice'
              AND v.status = 'Confirmed'
              AND p.gstin IS NOT NULL AND p.gstin != ''
              AND CAST(strftime('%m', v.date) AS INTEGER) = ?
              AND CAST(strftime('%Y', v.date) AS INTEGER) = ?
            ORDER BY p.gstin, v.date
        """, (month, year)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] GSTR-1 B2B error: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  GSTR-1 B2C — Sales to unregistered parties
# ═══════════════════════════════════════════════════════════════════════

def get_gstr1_b2c(month: int, year: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.state, vi.gst_rate,
                   SUM(vi.taxable_amount) AS taxable_value,
                   SUM(vi.cgst_amount) AS cgst, SUM(vi.sgst_amount) AS sgst,
                   SUM(vi.igst_amount) AS igst, SUM(vi.total_amount) AS total
            FROM vouchers v
            JOIN parties p ON v.party_id = p.id
            JOIN voucher_items vi ON v.id = vi.voucher_id
            WHERE v.voucher_type = 'Sales Invoice'
              AND v.status = 'Confirmed'
              AND (p.gstin IS NULL OR p.gstin = '')
              AND CAST(strftime('%m', v.date) AS INTEGER) = ?
              AND CAST(strftime('%Y', v.date) AS INTEGER) = ?
            GROUP BY p.state, vi.gst_rate
            ORDER BY p.state
        """, (month, year)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] GSTR-1 B2C error: {e}")
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  GSTR-1 CDNR — Credit Notes to registered parties
# ═══════════════════════════════════════════════════════════════════════

def get_gstr1_cdnr(month: int, year: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.gstin, p.name AS party_name, v.voucher_no, v.date,
                   v.reference_no, vi.taxable_amount,
                   vi.cgst_amount, vi.sgst_amount, vi.igst_amount, vi.total_amount
            FROM vouchers v
            JOIN parties p ON v.party_id = p.id
            JOIN voucher_items vi ON v.id = vi.voucher_id
            WHERE v.voucher_type = 'Credit Note'
              AND v.status = 'Confirmed'
              AND p.gstin IS NOT NULL AND p.gstin != ''
              AND CAST(strftime('%m', v.date) AS INTEGER) = ?
              AND CAST(strftime('%Y', v.date) AS INTEGER) = ?
            ORDER BY p.gstin, v.date
        """, (month, year)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] GSTR-1 CDNR error: {e}")
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  GSTR-1 HSN SUMMARY
# ═══════════════════════════════════════════════════════════════════════

def get_gstr1_hsn_summary(month: int, year: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT vi.hsn_code, vi.description, vi.unit,
                   SUM(vi.qty) AS total_qty,
                   SUM(vi.total_amount) AS total_value,
                   SUM(vi.taxable_amount) AS total_taxable,
                   SUM(vi.cgst_amount) AS cgst, SUM(vi.sgst_amount) AS sgst,
                   SUM(vi.igst_amount) AS igst
            FROM vouchers v
            JOIN voucher_items vi ON v.id = vi.voucher_id
            WHERE v.voucher_type = 'Sales Invoice'
              AND v.status = 'Confirmed'
              AND CAST(strftime('%m', v.date) AS INTEGER) = ?
              AND CAST(strftime('%Y', v.date) AS INTEGER) = ?
            GROUP BY vi.hsn_code
            ORDER BY vi.hsn_code
        """, (month, year)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] HSN Summary error: {e}")
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  GSTR-3B SUMMARY
# ═══════════════════════════════════════════════════════════════════════

def get_gstr3b_summary(month: int, year: int) -> dict:
    conn = get_connection()
    try:
        # Outward supplies (sales)
        sales = conn.execute("""
            SELECT COALESCE(SUM(vi.taxable_amount),0) AS taxable,
                   COALESCE(SUM(vi.cgst_amount),0) AS cgst,
                   COALESCE(SUM(vi.sgst_amount),0) AS sgst,
                   COALESCE(SUM(vi.igst_amount),0) AS igst
            FROM vouchers v
            JOIN voucher_items vi ON v.id = vi.voucher_id
            WHERE v.voucher_type = 'Sales Invoice' AND v.status = 'Confirmed'
              AND CAST(strftime('%m', v.date) AS INTEGER) = ?
              AND CAST(strftime('%Y', v.date) AS INTEGER) = ?
        """, (month, year)).fetchone()

        # Inward supplies (purchases — ITC)
        purchases = conn.execute("""
            SELECT COALESCE(SUM(vi.taxable_amount),0) AS taxable,
                   COALESCE(SUM(vi.cgst_amount),0) AS cgst,
                   COALESCE(SUM(vi.sgst_amount),0) AS sgst,
                   COALESCE(SUM(vi.igst_amount),0) AS igst
            FROM vouchers v
            JOIN voucher_items vi ON v.id = vi.voucher_id
            WHERE v.voucher_type = 'Purchase Invoice' AND v.status = 'Confirmed'
              AND CAST(strftime('%m', v.date) AS INTEGER) = ?
              AND CAST(strftime('%Y', v.date) AS INTEGER) = ?
        """, (month, year)).fetchone()

        s_cgst = _d(sales['cgst']); s_sgst = _d(sales['sgst']); s_igst = _d(sales['igst'])
        p_cgst = _d(purchases['cgst']); p_sgst = _d(purchases['sgst']); p_igst = _d(purchases['igst'])

        return {
            'outward': {
                'taxable': _r2(_d(sales['taxable'])),
                'cgst': _r2(s_cgst), 'sgst': _r2(s_sgst), 'igst': _r2(s_igst),
            },
            'itc': {
                'taxable': _r2(_d(purchases['taxable'])),
                'cgst': _r2(p_cgst), 'sgst': _r2(p_sgst), 'igst': _r2(p_igst),
            },
            'net_payable': {
                'cgst': _r2(s_cgst - p_cgst),
                'sgst': _r2(s_sgst - p_sgst),
                'igst': _r2(s_igst - p_igst),
                'total': _r2((s_cgst - p_cgst) + (s_sgst - p_sgst) + (s_igst - p_igst)),
            },
        }
    except sqlite3.Error as e:
        print(f"[PlywoodPro] GSTR-3B error: {e}")
        return {'outward':{}, 'itc':{}, 'net_payable':{}}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  ITC REGISTER
# ═══════════════════════════════════════════════════════════════════════

def get_itc_register(date_from: str = '', date_to: str = '') -> dict:
    conn = get_connection()
    try:
        query = """
            SELECT v.voucher_no, v.date, p.name AS party_name, p.gstin,
                   vi.description, vi.hsn_code,
                   vi.taxable_amount, vi.cgst_amount, vi.sgst_amount,
                   vi.igst_amount, vi.total_amount,
                   v.narration
            FROM vouchers v
            JOIN parties p ON v.party_id = p.id
            JOIN voucher_items vi ON v.id = vi.voucher_id
            WHERE v.voucher_type = 'Purchase Invoice'
              AND v.status = 'Confirmed'
        """
        params = []
        if date_from:
            query += " AND v.date >= ?"; params.append(date_from)
        if date_to:
            query += " AND v.date <= ?"; params.append(date_to)
        query += " ORDER BY v.date, v.id"

        rows = conn.execute(query, params).fetchall()
        entries = []
        total_cgst = total_sgst = total_igst = Decimal("0")

        for r in rows:
            d = dict(r)
            # Eligibility check
            narr = (d.get('narration') or '').lower()
            desc = (d.get('description') or '').lower()
            ineligible = 'personal' in narr or 'personal' in desc
            d['eligible'] = not ineligible
            d['status'] = 'Ineligible' if ineligible else 'Eligible'

            if not ineligible:
                total_cgst += _d(d.get('cgst_amount', 0))
                total_sgst += _d(d.get('sgst_amount', 0))
                total_igst += _d(d.get('igst_amount', 0))
            entries.append(d)

        return {
            'entries': entries,
            'total_eligible_cgst': _r2(total_cgst),
            'total_eligible_sgst': _r2(total_sgst),
            'total_eligible_igst': _r2(total_igst),
            'total_eligible_itc': _r2(total_cgst + total_sgst + total_igst),
        }
    except sqlite3.Error as e:
        print(f"[PlywoodPro] ITC Register error: {e}")
        return {'entries':[], 'total_eligible_cgst':0, 'total_eligible_sgst':0,
                'total_eligible_igst':0, 'total_eligible_itc':0}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  MONTHLY GST SUMMARY
# ═══════════════════════════════════════════════════════════════════════

def get_gst_summary_monthly(year_start: int = 2024) -> list:
    """Month-wise GST for financial year (Apr-Mar)."""
    results = []
    for m in range(4, 13):
        s = get_gstr3b_summary(m, year_start)
        results.append({'month': m, 'year': year_start, **s})
    for m in range(1, 4):
        s = get_gstr3b_summary(m, year_start + 1)
        results.append({'month': m, 'year': year_start + 1, **s})
    return results

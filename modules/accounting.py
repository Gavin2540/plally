"""
Accounting module for PlywoodPro.
Ledger, Trial Balance, P&L, Balance Sheet, Journal Voucher,
Cash Book, Bank Book, Day Book.
All monetary math uses Decimal.
"""

import sqlite3
import traceback
from decimal import Decimal, ROUND_HALF_UP
from db.connection import get_connection
from modules.masters import generate_voucher_no


def _d(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))

def _r2(val: Decimal) -> float:
    return float(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ═══════════════════════════════════════════════════════════════════════
#  LEDGER
# ═══════════════════════════════════════════════════════════════════════

def get_ledger(account_id: int, date_from: str = '', date_to: str = '') -> list:
    """
    All journal entries for a given account, with running balance.
    Returns list of dicts: date, voucher_no, voucher_type, narration,
    debit, credit, running_balance.
    """
    conn = get_connection()
    try:
        query = """
            SELECT je.date, v.voucher_no, v.voucher_type, je.narration,
                   je.debit, je.credit
            FROM journal_entries je
            LEFT JOIN vouchers v ON je.voucher_id = v.id
            WHERE je.account_id = ?
        """
        params = [account_id]
        if date_from:
            query += " AND je.date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND je.date <= ?"
            params.append(date_to)
        query += " ORDER BY je.date ASC, je.id ASC"

        rows = conn.execute(query, params).fetchall()
        result = []
        balance = Decimal("0")
        for r in rows:
            dr = _d(r['debit'])
            cr = _d(r['credit'])
            balance += dr - cr
            result.append({
                'date': r['date'],
                'voucher_no': r['voucher_no'] or '',
                'voucher_type': r['voucher_type'] or '',
                'narration': r['narration'] or '',
                'debit': _r2(dr),
                'credit': _r2(cr),
                'running_balance': _r2(balance),
            })
        return result
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching ledger: {e}")
        traceback.print_exc()
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  TRIAL BALANCE
# ═══════════════════════════════════════════════════════════════════════

def get_trial_balance(date_from: str = '', date_to: str = '') -> dict:
    """
    All accounts with total debits, credits, closing balance.
    Grouped by account group_name.
    Returns {'rows': [...], 'total_debit': float, 'total_credit': float, 'balanced': bool}
    """
    conn = get_connection()
    try:
        query = """
            SELECT a.id, a.name, a.group_name,
                   COALESCE(SUM(je.debit), 0) AS total_debit,
                   COALESCE(SUM(je.credit), 0) AS total_credit
            FROM accounts a
            LEFT JOIN journal_entries je ON a.id = je.account_id
        """
        params = []
        if date_from or date_to:
            conditions = []
            if date_from:
                conditions.append("je.date >= ?")
                params.append(date_from)
            if date_to:
                conditions.append("je.date <= ?")
                params.append(date_to)
            # Include accounts with no entries too
            query += " AND (" + " AND ".join(conditions) + " OR je.id IS NULL)"

        query += " GROUP BY a.id ORDER BY a.group_name, a.name"
        rows = conn.execute(query, params).fetchall()

        result_rows = []
        grand_debit = Decimal("0")
        grand_credit = Decimal("0")

        for r in rows:
            dr = _d(r['total_debit'])
            cr = _d(r['total_credit'])
            if dr == 0 and cr == 0:
                continue  # Skip zero-balance accounts
            closing = dr - cr
            grand_debit += dr
            grand_credit += cr
            result_rows.append({
                'account_id': r['id'],
                'account_name': r['name'],
                'group_name': r['group_name'],
                'total_debit': _r2(dr),
                'total_credit': _r2(cr),
                'closing_balance': _r2(closing),
                'closing_dr': _r2(closing) if closing > 0 else 0.0,
                'closing_cr': _r2(abs(closing)) if closing < 0 else 0.0,
            })

        return {
            'rows': result_rows,
            'total_debit': _r2(grand_debit),
            'total_credit': _r2(grand_credit),
            'balanced': abs(grand_debit - grand_credit) < Decimal("0.02"),
        }
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error fetching trial balance: {e}")
        traceback.print_exc()
        return {'rows': [], 'total_debit': 0, 'total_credit': 0, 'balanced': False}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  PROFIT & LOSS
# ═══════════════════════════════════════════════════════════════════════

INCOME_GROUPS = ['Sales Accounts', 'Sales', 'Direct Income', 'Indirect Income']
EXPENSE_GROUPS = ['Purchase Accounts', 'Purchase', 'Direct Expenses',
                  'Direct Expense', 'Indirect Expenses', 'Indirect Expense']

def get_profit_and_loss(date_from: str = '', date_to: str = '') -> dict:
    """
    Income vs Expense for a date range.
    Returns {'income': [...], 'expenses': [...], 'total_income', 'total_expense', 'net_profit'}
    """
    conn = get_connection()
    try:
        query = """
            SELECT a.name, a.group_name,
                   COALESCE(SUM(je.debit), 0) AS total_debit,
                   COALESCE(SUM(je.credit), 0) AS total_credit
            FROM accounts a
            JOIN journal_entries je ON a.id = je.account_id
        """
        params = []
        conditions = []
        if date_from:
            conditions.append("je.date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("je.date <= ?")
            params.append(date_to)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " GROUP BY a.id ORDER BY a.group_name, a.name"

        rows = conn.execute(query, params).fetchall()

        income_items = []
        expense_items = []
        total_income = Decimal("0")
        total_expense = Decimal("0")

        for r in rows:
            dr = _d(r['total_debit'])
            cr = _d(r['total_credit'])
            group = r['group_name']

            if group in INCOME_GROUPS or group == 'Sales':
                # Income: credit - debit (revenue is credited)
                amount = cr - dr
                if amount != 0:
                    income_items.append({
                        'name': r['name'], 'group': group, 'amount': _r2(amount)
                    })
                    total_income += amount
            elif group in EXPENSE_GROUPS or group == 'Purchase':
                # Expense: debit - credit (expense is debited)
                amount = dr - cr
                if amount != 0:
                    expense_items.append({
                        'name': r['name'], 'group': group, 'amount': _r2(amount)
                    })
                    total_expense += amount

        return {
            'income': income_items,
            'expenses': expense_items,
            'total_income': _r2(total_income),
            'total_expense': _r2(total_expense),
            'net_profit': _r2(total_income - total_expense),
        }
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error: {e}")
        traceback.print_exc()
        return {'income':[],'expenses':[],'total_income':0,'total_expense':0,'net_profit':0}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  BALANCE SHEET
# ═══════════════════════════════════════════════════════════════════════

ASSET_GROUPS = ['Fixed Assets', 'Current Assets', 'Stock-in-Hand',
                'Cash-in-Hand', 'Bank Accounts', 'Sundry Debtors']
LIABILITY_GROUPS = ['Capital', 'Capital Account', 'Loans', 'Current Liabilities',
                    'Sundry Creditors', 'Duties & Taxes']

def get_balance_sheet(as_of: str = '') -> dict:
    """
    Assets vs Liabilities. Must balance.
    Returns {'assets': [...], 'liabilities': [...], 'total_assets', 'total_liabilities', 'balanced'}
    """
    conn = get_connection()
    try:
        query = """
            SELECT a.name, a.group_name,
                   COALESCE(SUM(je.debit), 0) AS total_debit,
                   COALESCE(SUM(je.credit), 0) AS total_credit
            FROM accounts a
            JOIN journal_entries je ON a.id = je.account_id
        """
        params = []
        if as_of:
            query += " WHERE je.date <= ?"
            params.append(as_of)
        query += " GROUP BY a.id ORDER BY a.group_name, a.name"

        rows = conn.execute(query, params).fetchall()

        assets = []
        liabilities = []
        total_assets = Decimal("0")
        total_liabilities = Decimal("0")

        # We also need P&L net profit to add to liabilities (Capital side)
        pl = get_profit_and_loss(date_to=as_of) if as_of else get_profit_and_loss()
        net_profit = _d(pl['net_profit'])

        for r in rows:
            dr = _d(r['total_debit'])
            cr = _d(r['total_credit'])
            group = r['group_name']
            balance = dr - cr

            if group in ASSET_GROUPS:
                if balance != 0:
                    assets.append({'name': r['name'], 'group': group, 'amount': _r2(balance)})
                    total_assets += balance
            elif group in LIABILITY_GROUPS:
                # Liabilities have credit balance (negative of dr-cr)
                lib_bal = cr - dr
                if lib_bal != 0:
                    liabilities.append({'name': r['name'], 'group': group, 'amount': _r2(lib_bal)})
                    total_liabilities += lib_bal

        # Add net profit to liabilities side
        if net_profit != 0:
            liabilities.append({'name': 'Net Profit (Current Year)', 'group': 'Capital', 'amount': _r2(net_profit)})
            total_liabilities += net_profit

        return {
            'assets': assets,
            'liabilities': liabilities,
            'total_assets': _r2(total_assets),
            'total_liabilities': _r2(total_liabilities),
            'balanced': abs(total_assets - total_liabilities) < Decimal("0.02"),
        }
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error: {e}")
        traceback.print_exc()
        return {'assets':[],'liabilities':[],'total_assets':0,'total_liabilities':0,'balanced':False}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  JOURNAL VOUCHER (Manual Double-Entry)
# ═══════════════════════════════════════════════════════════════════════

def create_journal_voucher(date: str, narration: str, entries: list) -> tuple[bool, str, int]:
    """
    Manual double-entry journal voucher.
    entries: list of dicts with account_id, debit, credit.
    Validates total debits == total credits before saving.
    Returns (success, message, voucher_id).
    """
    total_dr = sum(_d(e.get('debit', 0)) for e in entries)
    total_cr = sum(_d(e.get('credit', 0)) for e in entries)

    if abs(total_dr - total_cr) > Decimal("0.01"):
        return False, f"Debits ({_r2(total_dr)}) != Credits ({_r2(total_cr)}). Cannot save.", 0

    if len(entries) < 2:
        return False, "At least 2 entries required.", 0

    conn = get_connection()
    try:
        voucher_no = generate_voucher_no(conn, 'Journal', date)

        cursor = conn.execute(
            """INSERT INTO vouchers (voucher_no, voucher_type, date, narration,
               total_amount, grand_total, status)
            VALUES (?, 'Journal', ?, ?, ?, ?, 'Confirmed')""",
            (voucher_no, date, narration, _r2(total_dr), _r2(total_dr)),
        )
        voucher_id = cursor.lastrowid

        for e in entries:
            conn.execute(
                """INSERT INTO journal_entries (voucher_id, account_id, date, debit, credit, narration)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (voucher_id, e['account_id'], date,
                 _r2(_d(e.get('debit', 0))), _r2(_d(e.get('credit', 0))),
                 narration),
            )

        conn.commit()
        return True, f"Journal Voucher {voucher_no} saved.", voucher_id

    except sqlite3.Error as e:
        conn.rollback()
        print(f"[PlywoodPro] Error: {e}")
        traceback.print_exc()
        return False, f"Database error: {e}", 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  CASH BOOK / BANK BOOK / DAY BOOK
# ═══════════════════════════════════════════════════════════════════════

def get_cash_book(date_from: str = '', date_to: str = '') -> list:
    """Cash account ledger."""
    conn = get_connection()
    try:
        cash = conn.execute(
            "SELECT id FROM accounts WHERE name = 'Cash' AND is_active = 1"
        ).fetchone()
        conn.close()
        if not cash:
            return []
        return get_ledger(cash['id'], date_from, date_to)
    except Exception:
        conn.close()
        return []


def get_bank_book(date_from: str = '', date_to: str = '') -> list:
    """Bank account ledger."""
    conn = get_connection()
    try:
        bank = conn.execute(
            "SELECT id FROM accounts WHERE group_name = 'Bank Accounts' AND is_active = 1"
        ).fetchone()
        conn.close()
        if not bank:
            return []
        return get_ledger(bank['id'], date_from, date_to)
    except Exception:
        conn.close()
        return []


def get_day_book(date: str) -> list:
    """All vouchers for a given date."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT v.id, v.voucher_no, v.voucher_type, v.date,
                   p.name AS party_name, v.grand_total, v.status, v.narration
            FROM vouchers v
            LEFT JOIN parties p ON v.party_id = p.id
            WHERE v.date = ?
            ORDER BY v.id ASC
        """, (date,)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[PlywoodPro] Error: {e}")
        return []
    finally:
        conn.close()

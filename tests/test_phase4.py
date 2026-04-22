"""
Phase 4 Integration Test -- PlywoodPro Accounting
Runs after Phase 2 (which creates journal entries from sales/purchase invoices).
"""
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.connection import get_connection
from modules.accounting import (
    get_ledger, get_trial_balance, get_profit_and_loss, get_balance_sheet,
    create_journal_voucher, get_day_book,
)
from utils.pdf_export import export_ledger_pdf

PASS = FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  [PASS] {label}")
    else:
        FAIL += 1; print(f"  [FAIL] {label} -- {detail}")

def main():
    global PASS, FAIL
    print("=" * 60)
    print("PlywoodPro Phase 4 -- Accounting Integration Test")
    print("=" * 60)

    # ── 1. Trial Balance must balance ──
    print("\n[1] Trial Balance -- Debits == Credits")
    tb = get_trial_balance()
    check("Trial Balance has rows", len(tb['rows']) > 0, f"Got {len(tb['rows'])} rows")
    check("Total Debits == Total Credits", tb['balanced'],
          f"Dr={tb['total_debit']}, Cr={tb['total_credit']}, diff={abs(tb['total_debit']-tb['total_credit'])}")
    print(f"    Total Debits:  {tb['total_debit']}")
    print(f"    Total Credits: {tb['total_credit']}")

    # ── 2. Ledger -- check Sales account ──
    print("\n[2] Ledger -- Sales account entries")
    conn = get_connection()
    sales_acc = conn.execute(
        "SELECT id FROM accounts WHERE name='Sales' AND is_active=1"
    ).fetchone()
    conn.close()
    if sales_acc:
        ledger = get_ledger(sales_acc['id'])
        check("Sales ledger has entries", len(ledger) > 0, f"Got {len(ledger)}")
        if ledger:
            last = ledger[-1]
            check("Sales running balance computed", last['running_balance'] != 0,
                  f"Balance: {last['running_balance']}")
    else:
        check("Sales account exists", False, "Not found")

    # ── 3. Journal Voucher -- Dr Freight 500, Cr Cash 500 ──
    print("\n[3] Journal Voucher -- Manual entry")
    conn = get_connection()
    # Find or create Freight account
    freight = conn.execute(
        "SELECT id FROM accounts WHERE name LIKE '%Freight%' AND is_active=1"
    ).fetchone()
    if not freight:
        conn.execute(
            "INSERT INTO accounts (name, group_name, nature) VALUES ('Freight Charges','Indirect Expense','Expense')")
        conn.commit()
        freight = conn.execute("SELECT id FROM accounts WHERE name='Freight Charges'").fetchone()
    cash = conn.execute(
        "SELECT id FROM accounts WHERE name='Cash' AND is_active=1"
    ).fetchone()
    conn.close()

    if freight and cash:
        ok, msg, vid = create_journal_voucher(
            '2026-04-22', 'Freight payment test',
            [
                {'account_id': freight['id'], 'debit': 500, 'credit': 0},
                {'account_id': cash['id'], 'debit': 0, 'credit': 500},
            ]
        )
        check("JV saved", ok, msg)

        # Verify in day book
        day = get_day_book('2026-04-22')
        jv_found = any(d['voucher_type'] == 'Journal' for d in day)
        check("JV appears in Day Book", jv_found)

        # Verify TB still balances
        tb2 = get_trial_balance()
        check("TB still balanced after JV", tb2['balanced'],
              f"Dr={tb2['total_debit']}, Cr={tb2['total_credit']}")
    else:
        check("Freight & Cash accounts exist", False)

    # ── 4. Profit & Loss ──
    print("\n[4] Profit & Loss")
    pl = get_profit_and_loss()
    check("P&L has income items", len(pl['income']) > 0, f"Got {len(pl['income'])}")
    check("P&L has expense items", len(pl['expenses']) > 0, f"Got {len(pl['expenses'])}")
    check("Total income > 0", pl['total_income'] > 0, f"Got {pl['total_income']}")
    print(f"    Income:  {pl['total_income']}")
    print(f"    Expense: {pl['total_expense']}")
    print(f"    Net:     {pl['net_profit']}")

    # ── 5. Balance Sheet ──
    print("\n[5] Balance Sheet")
    bs = get_balance_sheet()
    check("BS has assets", len(bs['assets']) > 0, f"Got {len(bs['assets'])}")
    check("BS has liabilities", len(bs['liabilities']) > 0, f"Got {len(bs['liabilities'])}")
    check("Assets == Liabilities", bs['balanced'],
          f"Assets={bs['total_assets']}, Liabilities={bs['total_liabilities']}")
    print(f"    Assets:      {bs['total_assets']}")
    print(f"    Liabilities: {bs['total_liabilities']}")

    # ── 6. PDF Export -- Sales Ledger ──
    print("\n[6] PDF Export -- Sales Ledger")
    if sales_acc:
        ok, path = export_ledger_pdf(sales_acc['id'], 'Sales')
        check("Ledger PDF exported", ok, path if not ok else "")
        if ok:
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            check("PDF file exists", exists)
            check("PDF file size > 0", size > 0, f"{size} bytes")
            print(f"    PDF: {path}")
    else:
        check("Sales account for PDF", False)

    # ── Results ──
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("*** ALL TESTS PASSED -- Phase 4 is COMPLETE! ***")
    else:
        print("!!! Some tests failed -- review above.")
    print("=" * 60)
    return FAIL == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

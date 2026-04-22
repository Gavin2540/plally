"""
Phase 2 Integration Test — PlywoodPro
Tests the complete Sales + Purchase invoice workflow end-to-end.
"""

import os
import sys

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.init_db import init_database
from db.connection import get_connection
from modules.masters import (
    create_party, create_item, get_company, save_company,
    get_all_parties, get_all_items
)
from modules.purchase import create_purchase_invoice, confirm_purchase_invoice
from modules.sales import create_sales_invoice, confirm_sales_invoice, get_voucher_with_items
from utils.gst_engine import calculate_tax_split, is_intra_state
from utils.pdf_export import export_invoice_pdf
from decimal import Decimal

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label} -- {detail}")


def main():
    global PASS, FAIL
    print("=" * 60)
    print("PlywoodPro Phase 2 — Integration Test")
    print("=" * 60)

    # -- Step 0: Initialise database ----------------------------
    print("\n[0] Database Init")
    init_database()
    check("Database initialised", True)

    # -- Step 0b: Ensure company exists (Karnataka, state_code 29) --
    company = get_company()
    if not company:
        ok, msg = save_company({
            'name': 'PlywoodPro Test Co',
            'state': 'Karnataka',
            'state_code': '29',
            'city': 'Bangalore',
            'address_line1': '123 Test Street',
            'pincode': '560001',
            'gstin': '29AABCU9603R1ZP',
            'pan': 'AABCU9603R',
            'phone': '9876543210',
            'email': 'test@plywoodpro.com',
            'bank_name': 'State Bank of India',
            'bank_account': '1234567890',
            'bank_ifsc': 'SBIN0001234',
        })
        check("Company created", ok, msg)
    else:
        check("Company exists", True)
    company = get_company()
    print(f"    Company: {company['name']}, State: {company['state']} ({company['state_code']})")

    # -- Step 1: Create 2 test items ----------------------------
    print("\n[1] Create Test Items")
    ok1, msg1 = create_item({
        'name': 'Marine Plywood 18mm 8x4',
        'category': 'Plywood',
        'hsn_code': '4412',
        'unit': 'Sheets',
        'thickness': '18mm',
        'size': '8x4',
        'gst_rate': 18.0,
        'purchase_rate': 1200.0,
        'sale_rate': 1500.0,
    })
    check("Item 1 (Marine Plywood) created", ok1, msg1)

    ok2, msg2 = create_item({
        'name': 'Flush Door Panel 32mm',
        'category': 'Flush Door',
        'hsn_code': '4418',
        'unit': 'Nos',
        'thickness': '32mm',
        'size': '7x3.5',
        'gst_rate': 18.0,
        'purchase_rate': 2800.0,
        'sale_rate': 3500.0,
    })
    check("Item 2 (Flush Door) created", ok2, msg2)

    items = get_all_items()
    item_map = {i['name']: i for i in items}
    check("Items retrievable", len(item_map) >= 2, f"Found {len(item_map)} items")

    # -- Step 2: Add supplier from DIFFERENT state (Maharashtra = 27) --
    print("\n[2] Add Supplier (Different State)")
    ok_s, msg_s = create_party({
        'name': 'Greenply Industries Ltd',
        'type': 'supplier',
        'gstin': '27AAACG1234L1ZP',
        'state': 'Maharashtra',
        'state_code': '27',
        'city': 'Mumbai',
        'phone': '9123456789',
    })
    check("Supplier created (Maharashtra, code 27)", ok_s, msg_s)

    suppliers = get_all_parties(party_type='supplier')
    supplier = None
    for s in suppliers:
        if s['name'] == 'Greenply Industries Ltd':
            supplier = s
            break
    check("Supplier retrievable", supplier is not None)

    # Verify inter-state detection
    is_intra = is_intra_state(company['state_code'], supplier['state_code'])
    check("Inter-state detected (29 vs 27)", not is_intra,
          f"company={company['state_code']}, supplier={supplier['state_code']}")

    # -- Step 3: Create Purchase Invoice (2 line items) + Confirm --
    print("\n[3] Purchase Invoice — Create & Confirm")

    item1 = item_map.get('Marine Plywood 18mm 8x4')
    item2 = item_map.get('Flush Door Panel 32mm')

    # Calculate tax for inter-state purchase
    tax1 = calculate_tax_split(18.0, company['state_code'], supplier['state_code'])
    tax2 = calculate_tax_split(18.0, company['state_code'], supplier['state_code'])

    qty1, rate1 = Decimal("10"), Decimal("1200")
    taxable1 = qty1 * rate1  # 12000
    igst1 = taxable1 * Decimal(str(tax1['igst_rate'])) / Decimal("100")
    total1 = taxable1 + igst1

    qty2, rate2 = Decimal("5"), Decimal("2800")
    taxable2 = qty2 * rate2  # 14000
    igst2 = taxable2 * Decimal(str(tax2['igst_rate'])) / Decimal("100")
    total2 = taxable2 + igst2

    pi_header = {
        'party_id': supplier['id'],
        'date': '2026-04-22',
        'due_date': '2026-05-22',
        'reference_no': 'SUP-BILL-001',
        'narration': 'Test purchase from Greenply',
        'godown_id': 1,
    }
    pi_items = [
        {
            'item_id': item1['id'], 'description': item1['name'],
            'hsn_code': '4412', 'qty': float(qty1), 'unit': 'Sheets',
            'rate': float(rate1), 'discount_pct': 0, 'gst_rate': 18.0,
            'cgst_rate': tax1['cgst_rate'], 'cgst_amount': 0,
            'sgst_rate': tax1['sgst_rate'], 'sgst_amount': 0,
            'igst_rate': tax1['igst_rate'], 'igst_amount': float(igst1),
            'taxable_amount': float(taxable1), 'total_amount': float(total1),
        },
        {
            'item_id': item2['id'], 'description': item2['name'],
            'hsn_code': '4418', 'qty': float(qty2), 'unit': 'Nos',
            'rate': float(rate2), 'discount_pct': 0, 'gst_rate': 18.0,
            'cgst_rate': tax2['cgst_rate'], 'cgst_amount': 0,
            'sgst_rate': tax2['sgst_rate'], 'sgst_amount': 0,
            'igst_rate': tax2['igst_rate'], 'igst_amount': float(igst2),
            'taxable_amount': float(taxable2), 'total_amount': float(total2),
        },
    ]

    ok_pi, msg_pi, pi_id = create_purchase_invoice(pi_header, pi_items)
    check("Purchase Invoice draft created", ok_pi, msg_pi)
    check("Purchase Invoice ID valid", pi_id > 0, f"ID={pi_id}")

    # Confirm it (should book stock + ITC)
    ok_conf, msg_conf = confirm_purchase_invoice(pi_id)
    check("Purchase Invoice confirmed", ok_conf, msg_conf)

    # Verify stock was updated
    conn = get_connection()
    stock1 = conn.execute(
        "SELECT qty FROM stock WHERE item_id = ? AND godown_id = 1", (item1['id'],)
    ).fetchone()
    stock2 = conn.execute(
        "SELECT qty FROM stock WHERE item_id = ? AND godown_id = 1", (item2['id'],)
    ).fetchone()
    conn.close()

    check("Stock updated — Marine Plywood qty = 10",
          stock1 and abs(stock1[0] - 10.0) < 0.01,
          f"Got: {stock1[0] if stock1 else 'None'}")
    check("Stock updated — Flush Door qty = 5",
          stock2 and abs(stock2[0] - 5.0) < 0.01,
          f"Got: {stock2[0] if stock2 else 'None'}")

    # Verify ITC journal entries
    conn = get_connection()
    je_rows = conn.execute(
        "SELECT * FROM journal_entries WHERE voucher_id = ?", (pi_id,)
    ).fetchall()
    conn.close()
    check("Journal entries created for purchase", len(je_rows) >= 3,
          f"Found {len(je_rows)} journal entries")

    # Verify IGST Input was debited
    conn = get_connection()
    igst_in = conn.execute(
        """SELECT je.debit FROM journal_entries je
           JOIN accounts a ON je.account_id = a.id
           WHERE je.voucher_id = ? AND a.name = 'IGST Input'""",
        (pi_id,)
    ).fetchone()
    conn.close()
    expected_igst_total = float(igst1 + igst2)
    check(f"IGST Input debited = {expected_igst_total}",
          igst_in and abs(igst_in[0] - expected_igst_total) < 0.01,
          f"Got: {igst_in[0] if igst_in else 'None'}")

    # -- Step 4: Add customer from DIFFERENT state (Tamil Nadu = 33) --
    print("\n[4] Add Customer (Different State)")
    ok_c, msg_c = create_party({
        'name': 'Chennai Woodworks Pvt Ltd',
        'type': 'customer',
        'gstin': '33AABCC1234L1ZP',
        'state': 'Tamil Nadu',
        'state_code': '33',
        'city': 'Chennai',
        'phone': '9988776655',
    })
    check("Customer created (Tamil Nadu, code 33)", ok_c, msg_c)

    customers = get_all_parties(party_type='customer')
    customer = None
    for c in customers:
        if c['name'] == 'Chennai Woodworks Pvt Ltd':
            customer = c
            break
    check("Customer retrievable", customer is not None)

    is_intra_cust = is_intra_state(company['state_code'], customer['state_code'])
    check("Inter-state detected for customer (29 vs 33)", not is_intra_cust)

    # -- Step 5: Create Sales Invoice + Confirm -----------------
    print("\n[5] Sales Invoice — Create & Confirm (IGST)")

    stax1 = calculate_tax_split(18.0, company['state_code'], customer['state_code'])
    check("Tax split uses IGST (not CGST+SGST)",
          stax1['igst_rate'] == 18.0 and stax1['cgst_rate'] == 0,
          f"Got: {stax1}")

    s_qty1, s_rate1 = Decimal("5"), Decimal("1500")
    s_taxable1 = s_qty1 * s_rate1  # 7500
    s_igst1 = s_taxable1 * Decimal("18") / Decimal("100")  # 1350
    s_total1 = s_taxable1 + s_igst1  # 8850

    si_header = {
        'party_id': customer['id'],
        'date': '2026-04-22',
        'due_date': '2026-05-07',
        'reference_no': 'PO-CHE-001',
        'narration': 'Inter-state sale to Chennai',
        'godown_id': 1,
        'transport_name': 'VRL Logistics',
        'vehicle_no': 'KA-01-AB-1234',
    }
    si_items = [
        {
            'item_id': item1['id'], 'description': item1['name'],
            'hsn_code': '4412', 'qty': float(s_qty1), 'unit': 'Sheets',
            'rate': float(s_rate1), 'discount_pct': 0, 'gst_rate': 18.0,
            'cgst_rate': 0, 'cgst_amount': 0,
            'sgst_rate': 0, 'sgst_amount': 0,
            'igst_rate': 18.0, 'igst_amount': float(s_igst1),
            'taxable_amount': float(s_taxable1), 'total_amount': float(s_total1),
        },
    ]

    ok_si, msg_si, si_id = create_sales_invoice(si_header, si_items)
    check("Sales Invoice draft created", ok_si, msg_si)

    ok_sc, msg_sc = confirm_sales_invoice(si_id)
    check("Sales Invoice confirmed", ok_sc, msg_sc)

    # Verify stock decreased
    conn = get_connection()
    stock_after = conn.execute(
        "SELECT qty FROM stock WHERE item_id = ? AND godown_id = 1", (item1['id'],)
    ).fetchone()
    conn.close()
    check("Stock decreased — Marine Plywood now = 5 (was 10, sold 5)",
          stock_after and abs(stock_after[0] - 5.0) < 0.01,
          f"Got: {stock_after[0] if stock_after else 'None'}")

    # Verify IGST Payable was credited
    conn = get_connection()
    igst_pay = conn.execute(
        """SELECT je.credit FROM journal_entries je
           JOIN accounts a ON je.account_id = a.id
           WHERE je.voucher_id = ? AND a.name = 'IGST Payable'""",
        (si_id,)
    ).fetchone()
    conn.close()
    check(f"IGST Payable credited = {float(s_igst1)}",
          igst_pay and abs(igst_pay[0] - float(s_igst1)) < 0.01,
          f"Got: {igst_pay[0] if igst_pay else 'None'}")

    # -- Step 6: Export PDF -------------------------------------
    print("\n[6] PDF Export")
    pdf_ok, pdf_result = export_invoice_pdf(si_id)
    check("PDF exported successfully", pdf_ok, pdf_result)
    if pdf_ok:
        check("PDF file exists on disk", os.path.exists(pdf_result), pdf_result)
        fsize = os.path.getsize(pdf_result)
        check(f"PDF file size > 0 bytes ({fsize} bytes)", fsize > 0)
        print(f"    PDF path: {pdf_result}")

    # -- Results ------------------------------------------------
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("*** ALL TESTS PASSED -- Phase 2 is COMPLETE! ***")
    else:
        print("!!! Some tests failed -- review above.")
    print("=" * 60)

    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

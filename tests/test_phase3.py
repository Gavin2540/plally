"""
Phase 3 Integration Test -- PlywoodPro Inventory Management
Uses the database left by Phase 2 tests (Plywood=5, Flush Door=5).
"""
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.connection import get_connection
from modules.inventory import (
    get_stock_summary, create_grn, create_stock_adjustment,
    create_godown_transfer, get_stock_movement_report, get_low_stock_items,
)
from modules.masters import get_all_items, get_all_godowns, create_godown

PASS = FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  [PASS] {label}")
    else:
        FAIL += 1; print(f"  [FAIL] {label} -- {detail}")

def get_stock_qty(item_id, godown_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT qty FROM stock WHERE item_id=? AND godown_id=?",
        (item_id, godown_id)).fetchone()
    conn.close()
    return float(row['qty']) if row else 0.0

def main():
    global PASS, FAIL
    print("=" * 60)
    print("PlywoodPro Phase 3 -- Inventory Integration Test")
    print("=" * 60)

    # Resolve items
    items = get_all_items()
    imap = {i['name']: i for i in items}
    plywood = imap.get('Marine Plywood 18mm 8x4')
    flush = imap.get('Flush Door Panel 32mm')
    if not plywood or not flush:
        print("  [FAIL] Phase 2 test items not found. Run test_phase2.py first.")
        return False

    godowns = get_all_godowns()
    gd_map = {g['name']: g for g in godowns}
    main_gd = gd_map.get('Main Godown', godowns[0] if godowns else None)

    # --- Step 1: Stock View baseline from Phase 2 ---
    print("\n[1] Stock View -- Baseline from Phase 2")
    summary = get_stock_summary()
    ply_row = next((r for r in summary if r['item_id'] == plywood['id'] and r['godown_id'] == main_gd['id']), None)
    flu_row = next((r for r in summary if r['item_id'] == flush['id'] and r['godown_id'] == main_gd['id']), None)

    check("Plywood visible in stock", ply_row is not None)
    check("Plywood qty = 5", ply_row and abs(ply_row['qty'] - 5.0) < 0.01,
          f"Got {ply_row['qty'] if ply_row else 'None'}")
    check("Flush Door visible in stock", flu_row is not None)
    check("Flush Door qty = 5", flu_row and abs(flu_row['qty'] - 5.0) < 0.01,
          f"Got {flu_row['qty'] if flu_row else 'None'}")

    # --- Step 2: GRN for 20 Plywood ---
    print("\n[2] GRN -- Add 20 Plywood sheets")

    ok, msg, vid = create_grn(
        {'party_id': None, 'date': '2026-04-22', 'reference_no': 'GRN-TEST-1',
         'narration': 'Test GRN', 'godown_id': main_gd['id']},
        [{'item_id': plywood['id'], 'description': plywood['name'],
          'hsn_code': '4412', 'qty': 20, 'unit': 'Sheets', 'rate': 1200}]
    )
    check("GRN created", ok, msg)
    new_qty = get_stock_qty(plywood['id'], main_gd['id'])
    check("Plywood stock = 25 (5+20)", abs(new_qty - 25.0) < 0.01, f"Got {new_qty}")

    # --- Step 3: Stock Adjustment -- reduce 3 Plywood (Damage) ---
    print("\n[3] Stock Adjustment -- Reduce 3 Plywood (Damage)")

    # Ensure Stock Adjustment voucher sequence exists
    conn = get_connection()
    existing = conn.execute(
        "SELECT voucher_type FROM voucher_sequences WHERE voucher_type='Stock Adjustment'"
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO voucher_sequences (voucher_type, prefix, last_number, financial_year) VALUES ('Stock Adjustment','ADJ-',0,'2024-25')")
        conn.commit()
    conn.close()

    ok2, msg2 = create_stock_adjustment(
        plywood['id'], main_gd['id'], 'Reduce', 3, 'Damage', 'Water damage test'
    )
    check("Adjustment saved", ok2, msg2)
    adj_qty = get_stock_qty(plywood['id'], main_gd['id'])
    check("Plywood stock = 22 (25-3)", abs(adj_qty - 22.0) < 0.01, f"Got {adj_qty}")

    # --- Step 4: Godown Transfer -- move 5 Plywood to second godown ---
    print("\n[4] Godown Transfer -- 5 Plywood Main -> Second godown")

    # Ensure second godown exists
    godowns = get_all_godowns()
    gd_map = {g['name']: g for g in godowns}
    if 'Branch Godown' not in gd_map:
        create_godown({'name': 'Branch Godown', 'address': 'Branch Location'})
        godowns = get_all_godowns()
        gd_map = {g['name']: g for g in godowns}
    second_gd = gd_map['Branch Godown']

    ok3, msg3 = create_godown_transfer(
        plywood['id'], main_gd['id'], second_gd['id'], 5, 'Phase 3 test transfer'
    )
    check("Transfer completed", ok3, msg3)
    main_qty = get_stock_qty(plywood['id'], main_gd['id'])
    branch_qty = get_stock_qty(plywood['id'], second_gd['id'])
    check("Main godown = 17 (22-5)", abs(main_qty - 17.0) < 0.01, f"Got {main_qty}")
    check("Branch godown = 5", abs(branch_qty - 5.0) < 0.01, f"Got {branch_qty}")

    # --- Step 5: Low Stock check ---
    print("\n[5] Low Stock Detection")
    low = get_low_stock_items()
    # Flush Door has reorder_level=0 by default so it won't appear
    flush_in_low = any(l['item_id'] == flush['id'] for l in low)
    check("Flush Door (reorder=0) NOT in low stock", not flush_in_low,
          "Items with reorder_level=0 are excluded")

    # Set a reorder level on Flush Door and check again
    conn = get_connection()
    conn.execute("UPDATE items SET reorder_level = 10 WHERE id = ?", (flush['id'],))
    conn.commit()
    conn.close()
    low2 = get_low_stock_items()
    flush_in_low2 = any(l['item_id'] == flush['id'] for l in low2)
    check("Flush Door (reorder=10, qty=5) IS in low stock", flush_in_low2)

    # Reset reorder level
    conn = get_connection()
    conn.execute("UPDATE items SET reorder_level = 0 WHERE id = ?", (flush['id'],))
    conn.commit()
    conn.close()

    # --- Step 6: Movement Report ---
    print("\n[6] Stock Movement Report")
    movements = get_stock_movement_report(item_id=plywood['id'])
    check("Movement audit trail exists", len(movements) >= 4,
          f"Found {len(movements)} movements")
    types_found = set(m['movement_type'] for m in movements)
    check("IN movements present", 'IN' in types_found, f"Types: {types_found}")
    check("ADJUSTMENT movements present", 'ADJUSTMENT' in types_found, f"Types: {types_found}")
    check("TRANSFER movements present", 'TRANSFER' in types_found, f"Types: {types_found}")

    # --- Results ---
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("*** ALL TESTS PASSED -- Phase 3 is COMPLETE! ***")
    else:
        print("!!! Some tests failed -- review above.")
    print("=" * 60)
    return FAIL == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

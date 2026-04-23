"""
PlywoodPro v1.1 — Headless Verification Test Suite
===================================================
Tests new modules and bug fixes without launching the GUI.
Run: python -m pytest tests/test_v1_1.py -v
"""

import os
import sys
import unittest
from decimal import Decimal

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Initialise a fresh test database
os.environ['PLYWOODPRO_DB'] = os.path.join(PROJECT_ROOT, 'test_plywoodpro.db')

from db.init_db import init_database
from db.connection import get_connection


def _setup_test_db():
    """Ensure database is initialised and seed minimal test data."""
    # Remove old test db
    db_path = os.environ['PLYWOODPRO_DB']
    if os.path.exists(db_path):
        os.remove(db_path)

    init_database()
    conn = get_connection()
    try:
        # Seed company
        conn.execute("""INSERT OR REPLACE INTO company
            (id, name, state, state_code, gstin, pan, fy_start_month)
            VALUES (1, 'Test Timber Co', 'Karnataka', '29', '29AABCT1234F1Z5', 'AABCT1234F', 4)""")

        # Seed accounts
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (1, 'Cash', 'Cash-in-Hand')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (2, 'Sales', 'Sales Accounts')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (3, 'Purchase', 'Purchase Accounts')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (4, 'CGST Output', 'Duties & Taxes')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (5, 'SGST Output', 'Duties & Taxes')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (6, 'IGST Output', 'Duties & Taxes')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (7, 'CGST Input', 'Duties & Taxes')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (8, 'SGST Input', 'Duties & Taxes')")
        conn.execute("INSERT OR IGNORE INTO accounts (id, name, group_name) VALUES (9, 'IGST Input', 'Duties & Taxes')")

        # Seed a godown
        conn.execute("INSERT OR IGNORE INTO godowns (id, name) VALUES (1, 'Main Godown')")

        # Seed a customer
        conn.execute("""INSERT OR IGNORE INTO parties
            (id, name, type, gstin, state, state_code, address_line1, city, pincode)
            VALUES (1, 'Acme Ply Ltd', 'customer', '29AABCA1234H1Z5', 'Karnataka', '29',
                    '123 MG Road', 'Bangalore', '560001')""")

        # Seed a supplier
        conn.execute("""INSERT OR IGNORE INTO parties
            (id, name, type, gstin, state, state_code, address_line1, city, pincode)
            VALUES (2, 'WoodSource Pvt Ltd', 'supplier', '29AABCW5678K1Z3', 'Karnataka', '29',
                    '456 Industrial Area', 'Mysore', '570001')""")

        # Seed items
        conn.execute("""INSERT OR IGNORE INTO items
            (id, name, hsn_code, unit, gst_rate, sale_rate, purchase_rate)
            VALUES (1, 'BWP Marine Ply 18mm', '4412', 'Sheets', 18, 1200.00, 900.00)""")
        conn.execute("""INSERT OR IGNORE INTO items
            (id, name, hsn_code, unit, gst_rate, sale_rate, purchase_rate)
            VALUES (2, 'MR Grade Ply 12mm', '4412', 'Sheets', 18, 800.00, 600.00)""")

        # Seed stock
        conn.execute("""INSERT OR IGNORE INTO stock
            (item_id, godown_id, qty) VALUES (1, 1, 100)""")
        conn.execute("""INSERT OR IGNORE INTO stock
            (item_id, godown_id, qty) VALUES (2, 1, 200)""")

        conn.commit()
    finally:
        conn.close()


class TestSettingsManager(unittest.TestCase):
    """Test the SettingsManager key-value store."""

    @classmethod
    def setUpClass(cls):
        _setup_test_db()

    def test_set_and_get(self):
        from utils.settings_manager import get_setting, set_setting
        set_setting('test_key', 'test_value')
        self.assertEqual(get_setting('test_key'), 'test_value')

    def test_get_default(self):
        from utils.settings_manager import get_setting
        self.assertEqual(get_setting('nonexistent_key', 'fallback'), 'fallback')

    def test_overwrite(self):
        from utils.settings_manager import get_setting, set_setting
        set_setting('overwrite_key', 'v1')
        set_setting('overwrite_key', 'v2')
        self.assertEqual(get_setting('overwrite_key'), 'v2')


class TestSalesOrderLifecycle(unittest.TestCase):
    """Test Sales Order create → confirm → convert-to-invoice."""

    @classmethod
    def setUpClass(cls):
        _setup_test_db()

    def test_sales_order_lifecycle(self):
        from modules.sales import create_sales_order, confirm_sales_order
        
        # 1. Create SO
        header = {
            'party_id': 1, 'date': '2026-04-20', 'due_date': '2026-05-20',
            'reference_no': 'SO-TEST', 'narration': 'Test order',
            'godown_id': 1,
        }
        items = [{
            'item_id': 1, 'description': 'BWP Marine Ply 18mm',
            'hsn_code': '4412', 'qty': 10, 'unit': 'Sheets',
            'rate': 1200, 'discount_pct': 5,
        }]
        ok, msg, vid = create_sales_order(header, items)
        self.assertTrue(ok, msg)
        self.assertGreater(vid, 0)
        
        # 2. Confirm SO
        ok, msg = confirm_sales_order(vid)
        self.assertTrue(ok, msg)

        # 3. Confirm already confirmed SO
        ok, msg = confirm_sales_order(vid)
        self.assertFalse(ok)
        self.assertIn("already", msg.lower())

    def test_convert_to_invoice(self):
        from modules.sales import convert_so_to_invoice
        # Need a new SO since the previous one is already Confirmed
        from modules.sales import create_sales_order, confirm_sales_order
        header = {
            'party_id': 1, 'date': '2026-04-21', 'due_date': '',
            'reference_no': '', 'narration': '', 'godown_id': 1,
        }
        items = [{'item_id': 2, 'description': 'MR Grade', 'hsn_code': '4412',
                  'qty': 5, 'unit': 'Sheets', 'rate': 800, 'discount_pct': 0}]
        ok, _, vid = create_sales_order(header, items)
        self.assertTrue(ok)
        ok, _ = confirm_sales_order(vid)
        self.assertTrue(ok)
        ok, msg, inv_id = convert_so_to_invoice(vid)
        self.assertTrue(ok, msg)
        self.assertGreater(inv_id, 0)


class TestReceiptPayment(unittest.TestCase):
    """Test Receipt (money from customer) and Payment (money to supplier)."""

    @classmethod
    def setUpClass(cls):
        _setup_test_db()

    def test_receipt_flow(self):
        """Create a sales invoice, confirm it, then process a receipt."""
        from modules.sales import create_sales_invoice, confirm_sales_invoice
        from modules.sales import get_outstanding_invoices, create_receipt

        header = {
            'party_id': 1, 'date': '2026-04-22', 'due_date': '2026-05-22',
            'reference_no': 'SI-RCP-TEST', 'narration': '', 'godown_id': 1,
        }
        items = [{
            'item_id': 1, 'description': 'BWP Marine Ply 18mm',
            'hsn_code': '4412', 'qty': 5, 'unit': 'Sheets', 'rate': 1200,
            'discount_pct': 0, 'taxable_amount': 6000, 'gst_rate': 18,
            'cgst_rate': 9, 'cgst_amount': 540, 'sgst_rate': 9,
            'sgst_amount': 540, 'igst_rate': 0, 'igst_amount': 0,
            'discount_amount': 0, 'total_amount': 7080,
        }]
        ok, msg, vid = create_sales_invoice(header, items)
        self.assertTrue(ok, msg)

        ok, msg = confirm_sales_invoice(vid)
        self.assertTrue(ok, msg)

        # Check outstanding
        outstanding = get_outstanding_invoices(1, 'Sales Invoice')
        self.assertGreater(len(outstanding), 0)
        inv = outstanding[0]
        self.assertGreater(float(inv['balance_due']), 0)

        # Create receipt
        ok, msg, rcp_id = create_receipt(
            party_id=1, invoice_id=inv['id'], amount=float(inv['balance_due']),
            mode='UPI', reference_no='UPI123', date_str='2026-04-22',
        )
        self.assertTrue(ok, msg)
        self.assertGreater(rcp_id, 0)

    def test_payment_flow(self):
        """Create a purchase invoice, confirm it, then make a payment."""
        from modules.purchase import (
            create_purchase_invoice, confirm_purchase_invoice,
            get_outstanding_purchase_invoices, create_payment,
        )

        header = {
            'party_id': 2, 'date': '2026-04-22', 'due_date': '2026-05-22',
            'reference_no': 'PI-PAY-TEST', 'narration': '', 'godown_id': 1,
        }
        items = [{
            'item_id': 2, 'description': 'MR Grade Ply 12mm',
            'hsn_code': '4412', 'qty': 20, 'unit': 'Sheets', 'rate': 600,
            'discount_pct': 0, 'taxable_amount': 12000, 'gst_rate': 18,
            'cgst_rate': 9, 'cgst_amount': 1080, 'sgst_rate': 9,
            'sgst_amount': 1080, 'igst_rate': 0, 'igst_amount': 0,
            'discount_amount': 0, 'total_amount': 14160,
        }]
        ok, msg, vid = create_purchase_invoice(header, items)
        self.assertTrue(ok, msg)

        ok, msg = confirm_purchase_invoice(vid)
        self.assertTrue(ok, msg)

        outstanding = get_outstanding_purchase_invoices(2)
        self.assertGreater(len(outstanding), 0)
        inv = outstanding[0]

        ok, msg, pmt_id = create_payment(
            party_id=2, invoice_id=inv['id'],
            amount=float(inv['balance_due']),
            mode='NEFT', reference_no='NEFT456', date_str='2026-04-22',
        )
        self.assertTrue(ok, msg)
        self.assertGreater(pmt_id, 0)

    def test_overpayment_rejected(self):
        """Ensure paying more than balance_due is rejected."""
        from modules.purchase import (
            create_purchase_invoice, confirm_purchase_invoice, create_payment,
        )

        header = {
            'party_id': 2, 'date': '2026-04-23', 'due_date': '',
            'reference_no': '', 'narration': '', 'godown_id': 1,
        }
        items = [{
            'item_id': 1, 'description': 'BWP Marine', 'hsn_code': '4412',
            'qty': 1, 'unit': 'Sheets', 'rate': 900, 'discount_pct': 0,
            'taxable_amount': 900, 'gst_rate': 18, 'cgst_rate': 9,
            'cgst_amount': 81, 'sgst_rate': 9, 'sgst_amount': 81,
            'igst_rate': 0, 'igst_amount': 0, 'discount_amount': 0,
            'total_amount': 1062,
        }]
        ok, _, vid = create_purchase_invoice(header, items)
        self.assertTrue(ok)
        ok, _ = confirm_purchase_invoice(vid)
        self.assertTrue(ok)

        ok, msg, _ = create_payment(2, vid, 999999, 'Cash', '', '2026-04-23')
        self.assertFalse(ok)
        self.assertIn("exceeds", msg.lower())


class TestPurchaseOrderLifecycle(unittest.TestCase):
    """Test Purchase Order create → confirm."""

    @classmethod
    def setUpClass(cls):
        _setup_test_db()

    def test_create_and_confirm(self):
        from modules.purchase import create_purchase_order, confirm_purchase_order

        header = {
            'party_id': 2, 'date': '2026-04-20', 'due_date': '',
            'reference_no': 'PO-TEST', 'narration': '', 'godown_id': 1,
        }
        items = [{'item_id': 1, 'description': 'BWP Marine', 'hsn_code': '4412',
                  'qty': 50, 'unit': 'Sheets', 'rate': 900, 'discount_pct': 2}]

        ok, msg, vid = create_purchase_order(header, items)
        self.assertTrue(ok, msg)
        self.assertGreater(vid, 0)

        ok, msg = confirm_purchase_order(vid)
        self.assertTrue(ok, msg)


class TestModuleImports(unittest.TestCase):
    """Verify all new modules can be imported without error."""

    def test_import_orders_ui(self):
        # Skip if no display (headless)
        try:
            from ui.orders_ui import OrdersUI
        except Exception as e:
            if 'display' in str(e).lower() or 'no module' in str(e).lower():
                self.skipTest("No display available")
            raise

    def test_import_payments_ui(self):
        try:
            from ui.payments_ui import PaymentsUI
        except Exception as e:
            if 'display' in str(e).lower() or 'no module' in str(e).lower():
                self.skipTest("No display available")
            raise

    def test_import_date_picker(self):
        from utils.date_picker import DatePickerEntry

    def test_import_settings_manager(self):
        try:
            from utils.settings_manager import get_setting, set_setting
        except Exception as e:
            self.fail(f"Settings manager failed to import: {e}")


class TestDatePicker(unittest.TestCase):
    """Test DatePickerEntry utility (non-GUI parts)."""

    def test_import_and_attributes(self):
        from utils.date_picker import DatePickerEntry
        self.assertTrue(hasattr(DatePickerEntry, '__init__'))
        self.assertTrue(callable(DatePickerEntry))


if __name__ == '__main__':
    unittest.main()

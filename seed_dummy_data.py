"""
PlywoodPro — Dummy Data Seeder
Run: python seed_dummy_data.py
Creates 20 realistic plywood business records for manual testing.
Safe to run multiple times (uses INSERT OR IGNORE).
"""

import sqlite3
import os
import hashlib
from datetime import date, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), 'plywoodpro.db')

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def seed_company(conn):
    existing = conn.execute("SELECT id FROM company WHERE id=1").fetchone()
    if existing:
        print("  Company already set up — skipping.")
        return
    conn.execute("""
        INSERT OR IGNORE INTO company
        (id, name, address_line1, city, state, state_code, gstin, pan, phone, email,
         bank_name, bank_account, bank_ifsc, fy_start_month)
        VALUES (1, 'PlywoodPro Test Co', 'MG Road, Bengaluru', 'Bengaluru',
                'Karnataka', '29', '29AABCP1234Q1Z5', 'AABCP1234Q',
                '9876543210', 'test@plywoodpro.in',
                'State Bank of India', '1234567890', 'SBIN0001234', 4)
    """)
    conn.commit()
    print("  ✅ Company: PlywoodPro Test Co (Karnataka, GSTIN: 29AABCP1234Q1Z5)")

def seed_godowns(conn):
    godowns = [
        (1, 'Main Godown', 'MG Road, Bengaluru'),
        (2, 'Branch Godown', 'Whitefield, Bengaluru'),
    ]
    for gid, name, addr in godowns:
        conn.execute("INSERT OR IGNORE INTO godowns (id, name, address) VALUES (?,?,?)",
                     (gid, name, addr))
    conn.commit()
    print("  ✅ Godowns: Main Godown, Branch Godown")

def seed_items(conn):
    items = [
        # (name, category, hsn, unit, thickness, size, gst_rate, purchase_rate, sale_rate, reorder)
        ('BWR Plywood 18mm', 'Plywood', '4412', 'Sheets', '18mm', '8x4', 18.0, 1200, 1500, 10),
        ('BWR Plywood 12mm', 'Plywood', '4412', 'Sheets', '12mm', '8x4', 18.0, 850, 1050, 10),
        ('BWR Plywood 6mm',  'Plywood', '4412', 'Sheets', '6mm',  '8x4', 18.0, 480, 620,  15),
        ('MR Grade Plywood 18mm', 'Plywood', '4412', 'Sheets', '18mm', '8x4', 18.0, 980, 1250, 8),
        ('MR Grade Plywood 12mm', 'Plywood', '4412', 'Sheets', '12mm', '8x4', 18.0, 720, 920,  8),
        ('Blockboard 19mm',  'Blockboard', '4412', 'Sheets', '19mm', '8x4', 18.0, 950, 1200, 5),
        ('Flush Door 32mm',  'Flush Door', '4418', 'Nos',    '32mm', '7x3', 18.0, 1800, 2300, 5),
        ('Flush Door 25mm',  'Flush Door', '4418', 'Nos',    '25mm', '7x3', 18.0, 1500, 1900, 5),
        ('MDF Board 12mm',   'MDF',        '4421', 'Sheets', '12mm', '8x4', 18.0, 680, 880,   10),
        ('MDF Board 6mm',    'MDF',        '4421', 'Sheets', '6mm',  '8x4', 18.0, 420, 550,   10),
        ('Particle Board 18mm', 'Particle Board', '4421', 'Sheets', '18mm', '8x4', 18.0, 580, 750, 8),
        ('Veneer Teak 0.5mm', 'Veneer',   '4408', 'Sheets', '0.5mm','8x4', 12.0, 320, 420,   20),
        ('Marine Plywood 18mm', 'Plywood', '4412', 'Sheets', '18mm', '8x4', 18.0, 1600, 2000, 5),
        ('Fire Retardant Plywood 18mm', 'Plywood', '4412', 'Sheets', '18mm', '8x4', 18.0, 1900, 2400, 3),
        ('Packing Plywood 6mm', 'Plywood', '4415', 'Sheets', '6mm',  '8x4', 12.0, 280, 380,  20),
        ('Hard Board 3mm',   'Hardboard',  '4411', 'Sheets', '3mm',  '8x4', 18.0, 180, 240,  25),
        ('Laminates 1mm',    'Laminates',  '3921', 'Sheets', '1mm',  '8x4', 18.0, 450, 580,  30),
        ('Wood Putty 1kg',   'Hardware',   '3214', 'Nos',    None,   None,  18.0, 80,  120,  50),
        ('Nails 1kg Box',    'Hardware',   '7317', 'Nos',    None,   None,  18.0, 45,   70,  100),
        ('Edge Banding Tape','Hardware',   '3921', 'Running Ft', None, None, 18.0, 5,    8,   200),
    ]
    count = 0
    for item in items:
        name, cat, hsn, unit, thick, size, gst, pur, sal, reorder = item
        conn.execute("""
            INSERT OR IGNORE INTO items
            (name, category, hsn_code, unit, thickness, size, gst_rate,
             purchase_rate, sale_rate, reorder_level, opening_stock)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (name, cat, hsn, unit, thick, size, gst, pur, sal, reorder, 0))
        count += 1
    conn.commit()
    print(f"  ✅ Items: {count} plywood products seeded")

def seed_parties(conn):
    parties = [
        # (name, type, gstin, state, state_code, phone, credit_limit, credit_days)
        # Suppliers (inter-state — Maharashtra)
        ('Greenply Industries Ltd',   'supplier', '27AABCG1234Q1Z5', 'Maharashtra', '27', '9001001001', 0, 30),
        ('Century Plyboards Ltd',     'supplier', '27AABCC5678Q1Z5', 'Maharashtra', '27', '9001002002', 0, 30),
        ('Kitply Industries',         'supplier', '27AABCK9012Q1Z5', 'Maharashtra', '27', '9001003003', 0, 45),
        ('Archidply Industries',      'supplier', '29AABCA3456Q1Z5', 'Karnataka',   '29', '9001004004', 0, 30),
        ('Uniply Industries',         'supplier', '29AABCU7890Q1Z5', 'Karnataka',   '29', '9001005005', 0, 45),

        # Customers — same state (Karnataka) → CGST+SGST
        ('Rahul Furniture Works',     'customer', '29AABCR1111Q1Z5', 'Karnataka',   '29', '9002001001', 50000,  30),
        ('Sri Lakshmi Interiors',     'customer', '29AABCS2222Q1Z5', 'Karnataka',   '29', '9002002002', 30000,  15),
        ('Modern Wood Crafts',        'customer', '29AABCM3333Q1Z5', 'Karnataka',   '29', '9002003003', 75000,  45),
        ('Bangalore Furniture Hub',   'customer', '29AABCB4444Q1Z5', 'Karnataka',   '29', '9002004004', 100000, 30),
        ('Krishna Plywood Depot',     'customer', None,              'Karnataka',   '29', '9002005005', 10000,  0),  # B2C

        # Customers — different state → IGST
        ('Chennai Woodworks',         'customer', '33AABCC5555Q1Z5', 'Tamil Nadu',  '33', '9003001001', 50000,  30),
        ('Hyderabad Ply Traders',     'customer', '36AABCH6666Q1Z5', 'Telangana',   '36', '9003002002', 40000,  30),
        ('Mumbai Interior Solutions', 'customer', '27AABCM7777Q1Z5', 'Maharashtra', '27', '9003003003', 60000,  45),
        ('Delhi Timber Mart',         'customer', '07AABCD8888Q1Z5', 'Delhi',       '07', '9003004004', 80000,  30),
        ('Kochi Ply House',           'customer', '32AABCK9999Q1Z5', 'Kerala',      '32', '9003005005', 25000,  15),

        # Both (supplier + customer)
        ('Sriram Wood Products',      'both',     '29AABCS0000Q1Z5', 'Karnataka',   '29', '9004001001', 20000,  30),
    ]
    count = 0
    for p in parties:
        name, ptype, gstin, state, sc, phone, cl, cd = p
        conn.execute("""
            INSERT OR IGNORE INTO parties
            (name, type, gstin, state, state_code, phone, credit_limit, credit_days)
            VALUES (?,?,?,?,?,?,?,?)
        """, (name, ptype, gstin, state, sc, phone, cl, cd))
        count += 1
    conn.commit()
    print(f"  ✅ Parties: {count} customers and suppliers seeded")

def seed_accounts(conn):
    extra_accounts = [
        ('Petty Cash',       'Cash-in-Hand',      0, 'Dr'),
        ('HDFC Bank',        'Bank Accounts',      0, 'Dr'),
        ('ICICI Bank',       'Bank Accounts',      0, 'Dr'),
        ('Office Rent',      'Indirect Expenses',  0, 'Dr'),
        ('Telephone Exp',    'Indirect Expenses',  0, 'Dr'),
        ('Vehicle Fuel',     'Indirect Expenses',  0, 'Dr'),
        ('Commission Income','Indirect Income',     0, 'Cr'),
        ('TDS Payable',      'Current Liabilities',0, 'Cr'),
    ]
    for name, group, bal, btype in extra_accounts:
        conn.execute("""
            INSERT OR IGNORE INTO accounts (name, group_name, opening_balance, balance_type)
            VALUES (?,?,?,?)
        """, (name, group, bal, btype))
    conn.commit()
    print("  ✅ Accounts: Extra bank and expense accounts seeded")

def seed_opening_stock(conn):
    """Add opening stock for all items in Main Godown."""
    items = conn.execute("SELECT id FROM items").fetchall()
    godown_id = 1  # Main Godown
    stock_data = [
        (25, 1200), (30, 850), (50, 480), (20, 980), (25, 720),
        (15, 950),  (10, 1800),(12, 1500),(20, 680), (30, 420),
        (18, 580),  (40, 320), (8, 1600), (5, 1900), (35, 280),
        (60, 180),  (45, 450), (80, 80),  (100, 45), (150, 5),
    ]
    for i, item in enumerate(items):
        if i >= len(stock_data):
            break
        qty, rate = stock_data[i]
        conn.execute("""
            INSERT INTO stock (item_id, godown_id, qty)
            VALUES (?, ?, ?)
            ON CONFLICT(item_id, godown_id) DO UPDATE SET qty = qty + excluded.qty
        """, (item['id'], godown_id, qty))
    conn.commit()
    print("  ✅ Opening stock seeded for all items in Main Godown")

def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Please run the app once first to create the database.")
        return

    print("\n🌱 PlywoodPro Dummy Data Seeder")
    print("=" * 45)

    conn = get_conn()
    try:
        seed_company(conn)
        seed_godowns(conn)
        seed_items(conn)
        seed_parties(conn)
        seed_accounts(conn)
        seed_opening_stock(conn)
    finally:
        conn.close()

    print("=" * 45)
    print("✅ All dummy data seeded successfully!")
    print("\nTest credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nTest scenarios ready:")
    print("  • 5 suppliers (3 inter-state Maharashtra, 2 Karnataka)")
    print("  • 10 customers (5 Karnataka CGST+SGST, 5 other states IGST)")
    print("  • 20 products across 8 categories")
    print("  • Opening stock in Main Godown")
    print("  • Extra bank accounts (HDFC, ICICI)")
    print("\nReady to test invoicing, GST, inventory, and payments!")

if __name__ == '__main__':
    main()

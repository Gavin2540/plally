-- PlywoodPro Database Schema
-- All 13 tables as defined in the Master Technical Specification v1.0

-- 4.1 company (single row — business profile)
CREATE TABLE IF NOT EXISTS company (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    name            TEXT NOT NULL,
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    state           TEXT NOT NULL,
    state_code      TEXT NOT NULL,       -- 2-digit GST state code e.g. '29' for Karnataka
    pincode         TEXT,
    gstin           TEXT,               -- 15-char GSTIN
    pan             TEXT,               -- 10-char PAN
    phone           TEXT,
    email           TEXT,
    bank_name       TEXT,
    bank_account    TEXT,
    bank_ifsc       TEXT,
    fy_start_month  INTEGER DEFAULT 4,  -- 4 = April (Indian financial year)
    logo_path       TEXT,               -- path to logo image file
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.2 parties (customers and suppliers)
CREATE TABLE IF NOT EXISTS parties (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL CHECK(type IN ('customer','supplier','both')),
    gstin           TEXT,
    pan             TEXT,
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    state           TEXT,
    state_code      TEXT,               -- for IGST vs CGST/SGST determination
    pincode         TEXT,
    phone           TEXT,
    email           TEXT,
    credit_limit    REAL DEFAULT 0,
    credit_days     INTEGER DEFAULT 0,
    opening_balance REAL DEFAULT 0,
    balance_type    TEXT DEFAULT 'Dr' CHECK(balance_type IN ('Dr','Cr')),
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.3 items (product/stock master)
CREATE TABLE IF NOT EXISTS items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    category        TEXT,               -- 'Plywood', 'Blockboard', 'MDF', 'Flush Door', 'Hardware', etc.
    hsn_code        TEXT NOT NULL,      -- e.g. '4412', '4418', '4421'
    unit            TEXT NOT NULL CHECK(unit IN ('Sheets','Sq.Ft','Kg','Nos','Running Ft')),
    thickness       TEXT,               -- '3mm','4mm','6mm','9mm','12mm','16mm','18mm','25mm','Custom'
    size            TEXT,               -- '8x4','7x3.5','6x3','Custom'
    gst_rate        REAL NOT NULL DEFAULT 18.0,  -- 0, 5, 12, 18, 28
    purchase_rate   REAL DEFAULT 0,
    sale_rate       REAL DEFAULT 0,
    reorder_level   REAL DEFAULT 0,
    opening_stock   REAL DEFAULT 0,
    description     TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.4 godowns (warehouses / storage locations)
CREATE TABLE IF NOT EXISTS godowns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    address     TEXT,
    is_active   INTEGER DEFAULT 1
);

-- 4.5 stock (current stock per item per godown)
CREATE TABLE IF NOT EXISTS stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL REFERENCES items(id),
    godown_id   INTEGER NOT NULL REFERENCES godowns(id),
    qty         REAL DEFAULT 0,
    last_updated TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(item_id, godown_id)
);

-- 4.6 accounts (chart of accounts)
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    group_name      TEXT NOT NULL CHECK(group_name IN (
                        'Capital Account','Loans (Liability)','Current Liabilities',
                        'Fixed Assets','Current Assets','Stock-in-Hand',
                        'Sales Accounts','Purchase Accounts',
                        'Direct Income','Indirect Income',
                        'Direct Expenses','Indirect Expenses',
                        'Bank Accounts','Cash-in-Hand','Sundry Debtors','Sundry Creditors',
                        'Duties & Taxes'
                    )),
    opening_balance REAL DEFAULT 0,
    balance_type    TEXT DEFAULT 'Dr' CHECK(balance_type IN ('Dr','Cr')),
    is_system       INTEGER DEFAULT 0,   -- 1 = auto-created, cannot be deleted
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.7 vouchers (master header for all financial transactions)
CREATE TABLE IF NOT EXISTS vouchers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_no      TEXT NOT NULL UNIQUE,   -- e.g. 'SI-2024-001', 'PI-2024-001'
    voucher_type    TEXT NOT NULL CHECK(voucher_type IN (
                        'Sales Invoice','Sales Order','Quotation','Delivery Challan',
                        'Purchase Invoice','Purchase Order','GRN',
                        'Receipt','Payment','Journal',
                        'Credit Note','Debit Note','Stock Adjustment'
                    )),
    party_id        INTEGER REFERENCES parties(id),
    date            TEXT NOT NULL,
    due_date        TEXT,
    reference_no    TEXT,               -- supplier bill no, cheque no, etc.
    narration       TEXT,
    total_amount    REAL DEFAULT 0,
    tax_amount      REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    grand_total     REAL DEFAULT 0,
    paid_amount     REAL DEFAULT 0,
    balance_due     REAL DEFAULT 0,
    status          TEXT DEFAULT 'Draft' CHECK(status IN ('Draft','Confirmed','Converted','Cancelled','Paid','Partial')),
    godown_id       INTEGER REFERENCES godowns(id),
    transport_name  TEXT,
    vehicle_no      TEXT,
    created_by      TEXT DEFAULT 'Admin',
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.8 voucher_items (line items for every voucher)
CREATE TABLE IF NOT EXISTS voucher_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id      INTEGER NOT NULL REFERENCES vouchers(id) ON DELETE CASCADE,
    item_id         INTEGER NOT NULL REFERENCES items(id),
    description     TEXT,
    hsn_code        TEXT,
    qty             REAL NOT NULL,
    unit            TEXT,
    rate            REAL NOT NULL,
    discount_pct    REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    taxable_amount  REAL DEFAULT 0,
    gst_rate        REAL DEFAULT 0,
    cgst_rate       REAL DEFAULT 0,
    cgst_amount     REAL DEFAULT 0,
    sgst_rate       REAL DEFAULT 0,
    sgst_amount     REAL DEFAULT 0,
    igst_rate       REAL DEFAULT 0,
    igst_amount     REAL DEFAULT 0,
    total_amount    REAL NOT NULL
);

-- 4.9 journal_entries (double-entry ledger — auto-generated)
CREATE TABLE IF NOT EXISTS journal_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id  INTEGER REFERENCES vouchers(id) ON DELETE CASCADE,
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    date        TEXT NOT NULL,
    debit       REAL DEFAULT 0,
    credit      REAL DEFAULT 0,
    narration   TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.10 payments (receipts and payments linked to vouchers)
CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id      INTEGER REFERENCES vouchers(id),
    party_id        INTEGER REFERENCES parties(id),
    payment_type    TEXT CHECK(payment_type IN ('Receipt','Payment')),
    mode            TEXT CHECK(mode IN ('Cash','UPI','NEFT','RTGS','Cheque','Card')),
    amount          REAL NOT NULL,
    date            TEXT NOT NULL,
    reference_no    TEXT,               -- UTR, cheque number, etc.
    bank_account_id INTEGER REFERENCES accounts(id),
    narration       TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.11 stock_movements (audit log of all stock changes)
CREATE TABLE IF NOT EXISTS stock_movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES items(id),
    godown_id       INTEGER NOT NULL REFERENCES godowns(id),
    voucher_id      INTEGER REFERENCES vouchers(id),
    movement_type   TEXT CHECK(movement_type IN ('IN','OUT','ADJUSTMENT','TRANSFER')),
    qty             REAL NOT NULL,      -- always positive; direction from movement_type
    rate            REAL,
    date            TEXT NOT NULL,
    narration       TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.12 users (login accounts)
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,          -- SHA-256 hashed, never plain text
    full_name   TEXT,
    role        TEXT NOT NULL CHECK(role IN ('Admin','Accountant','Salesperson','Store Manager','Purchase Manager','Viewer')),
    is_active   INTEGER DEFAULT 1,
    last_login  TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 4.13 voucher_sequences (auto-incrementing voucher number tracking)
CREATE TABLE IF NOT EXISTS voucher_sequences (
    voucher_type    TEXT PRIMARY KEY,
    prefix          TEXT NOT NULL,
    last_number     INTEGER DEFAULT 0,
    financial_year  TEXT NOT NULL        -- e.g. '2024-25'
);

-- 4.14 settings (key-value app config)
CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT
);

# PlywoodPro — Master Technical Specification
> **READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE.**
> This is the single source of truth for the PlywoodPro Windows desktop application.
> Every architectural decision, database table, module scope, and naming convention is defined here.
> Do not deviate from this spec without being explicitly told to.

---

## 1. Project Identity

| Field | Value |
|---|---|
| Product Name | PlywoodPro |
| Type | Windows Desktop Application |
| Target Users | Plywood dealers, timber merchants, wood panel distributors in India |
| Comparable To | Tally ERP 9 — same workflow category, purpose-built for plywood trade |
| Primary Market | India (GST-registered businesses) |
| Offline First | Yes — must work 100% without internet |
| Multi-User | Single machine, multiple login roles (no LAN networking in v1) |

---

## 2. Tech Stack — FIXED, DO NOT CHANGE

### Language & Runtime
- **Python 3.11+** — primary language for all code
- **No JavaScript, no Electron, no web frameworks**

### UI Framework
- **CustomTkinter** (`customtkinter`) — modern themed tkinter
- Use `CTk` widgets everywhere: `CTkFrame`, `CTkButton`, `CTkEntry`, `CTkLabel`, `CTkComboBox`, `CTkScrollableFrame`, `CTkTabview`, `CTkSwitch`
- Use `ttk.Treeview` inside `CTkScrollableFrame` for all data tables/grids
- Use `CTkMessagebox` (from `CTkMessagebox` package) for all popups, confirmations, and alerts
- Theme: Dark by default, user-switchable to Light via Settings
- Color accent: `#2E7D32` (forest green) — used for primary buttons, highlights, active nav

### Database
- **SQLite3** — built into Python, zero installation
- Single database file: `plywoodpro.db` in the app's root directory
- Accessed via Python's built-in `sqlite3` module
- **All queries must use parameterized placeholders (`?`)** — never string format SQL
- Enable WAL mode on every connection: `PRAGMA journal_mode=WAL;`
- Enable foreign keys on every connection: `PRAGMA foreign_keys=ON;`
- All monetary values stored as `REAL` (float, 2 decimal places)
- All dates stored as `TEXT` in `YYYY-MM-DD` format
- All datetimes stored as `TEXT` in `YYYY-MM-DD HH:MM:SS` format

### PDF Generation
- **ReportLab** (`reportlab`) — for invoice, report, and statement PDF export
- All PDFs saved to `exports/` folder in app root, then opened with `os.startfile()`

### Excel Export
- **openpyxl** — for GST reports and register exports to `.xlsx`

### Packaging (for later)
- **PyInstaller** — to build `.exe` for Windows 10/11
- Entry point: `main.py`

### Required Python Packages (`requirements.txt`)
```
customtkinter>=5.2.0
CTkMessagebox>=2.5
reportlab>=4.0.0
openpyxl>=3.1.0
Pillow>=10.0.0
pyinstaller>=6.0.0
```

---

## 3. Folder Structure — FIXED

```
PlywoodPro/
├── main.py                  ← App entry point, window init, nav router
├── plywoodpro.db            ← SQLite database (auto-created on first run)
├── requirements.txt
├── README.md
│
├── db/
│   ├── connection.py        ← get_connection() function, WAL + FK pragmas
│   ├── schema.sql           ← Full CREATE TABLE statements
│   └── init_db.py           ← Reads schema.sql and creates tables if not exist
│
├── modules/                 ← Business logic (no UI here)
│   ├── masters.py           ← CRUD for Company, Party, Item, Godown, Account
│   ├── inventory.py         ← GRN, stock outward, stock ledger, adjustments
│   ├── sales.py             ← Quotation, Sales Order, Invoice, Receipt
│   ├── purchase.py          ← Purchase Order, GRN, Purchase Invoice, Payment
│   ├── accounting.py        ← Journal entries, ledger, trial balance
│   ├── gst.py               ← GST calculation engine, GSTR-1, GSTR-3B
│   └── reports.py           ← All report data fetchers
│
├── ui/                      ← All CustomTkinter screens
│   ├── dashboard.py         ← Home dashboard with KPI cards
│   ├── masters_ui.py        ← Party, Item, Godown, Account master screens
│   ├── inventory_ui.py      ← GRN form, stock view, adjustment form
│   ├── sales_ui.py          ← Invoice form, order form, receipt form
│   ├── purchase_ui.py       ← Purchase order, purchase invoice forms
│   ├── accounting_ui.py     ← Ledger view, journal voucher, bank book
│   ├── gst_ui.py            ← GST reports, GSTR-1, GSTR-3B views
│   ├── reports_ui.py        ← Report selection and display
│   └── settings_ui.py       ← Company setup, preferences, backup
│
├── utils/
│   ├── pdf_export.py        ← ReportLab invoice and report PDF builders
│   ├── excel_export.py      ← openpyxl GST register exports
│   ├── validators.py        ← GSTIN, PAN, HSN validation functions
│   ├── gst_engine.py        ← GST rate lookup, CGST/SGST/IGST split logic
│   └── helpers.py           ← Date formatting, number formatting, INR formatter
│
└── exports/                 ← Auto-created folder for PDF and Excel exports
```

---

## 4. Database Schema — COMPLETE

> Implement exactly as defined. Do not rename columns. Do not add or remove tables without instruction.

---

### 4.1 `company` (single row — business profile)
```sql
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
```

---

### 4.2 `parties` (customers and suppliers)
```sql
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
```

---

### 4.3 `items` (product/stock master)
```sql
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
```

---

### 4.4 `godowns` (warehouses / storage locations)
```sql
CREATE TABLE IF NOT EXISTS godowns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    address     TEXT,
    is_active   INTEGER DEFAULT 1
);
```

---

### 4.5 `stock` (current stock per item per godown)
```sql
CREATE TABLE IF NOT EXISTS stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL REFERENCES items(id),
    godown_id   INTEGER NOT NULL REFERENCES godowns(id),
    qty         REAL DEFAULT 0,
    last_updated TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(item_id, godown_id)
);
```

---

### 4.6 `accounts` (chart of accounts)
```sql
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
```

---

### 4.7 `vouchers` (master header for all financial transactions)
```sql
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
    status          TEXT DEFAULT 'Draft' CHECK(status IN ('Draft','Confirmed','Cancelled','Paid','Partial')),
    godown_id       INTEGER REFERENCES godowns(id),
    transport_name  TEXT,
    vehicle_no      TEXT,
    created_by      TEXT DEFAULT 'Admin',
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);
```

---

### 4.8 `voucher_items` (line items for every voucher)
```sql
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
```

---

### 4.9 `journal_entries` (double-entry ledger — auto-generated)
```sql
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
```

---

### 4.10 `payments` (receipts and payments linked to vouchers)
```sql
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
```

---

### 4.11 `stock_movements` (audit log of all stock changes)
```sql
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
```

---

### 4.12 `users` (login accounts)
```sql
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
```

---

### 4.13 `voucher_sequences` (auto-incrementing voucher number tracking)
```sql
CREATE TABLE IF NOT EXISTS voucher_sequences (
    voucher_type    TEXT PRIMARY KEY,
    prefix          TEXT NOT NULL,
    last_number     INTEGER DEFAULT 0,
    financial_year  TEXT NOT NULL        -- e.g. '2024-25'
);
```
**Seed data for voucher_sequences:**
```sql
INSERT OR IGNORE INTO voucher_sequences VALUES ('Sales Invoice','SI',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Purchase Invoice','PI',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Sales Order','SO',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Purchase Order','PO',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Delivery Challan','DC',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('GRN','GRN',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Receipt','RCP',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Payment','PMT',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Journal','JV',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Credit Note','CN',0,'2024-25');
INSERT OR IGNORE INTO voucher_sequences VALUES ('Debit Note','DN',0,'2024-25');
```

---

### 4.14 `settings` (key-value app config)
```sql
CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT
);
```

---

## 5. Default Seed Data

Insert these on first run (in `init_db.py`) if tables are empty:

### Default Godown
```sql
INSERT OR IGNORE INTO godowns (id, name) VALUES (1, 'Main Godown');
```

### Default System Accounts (is_system=1, cannot be deleted)
```sql
INSERT OR IGNORE INTO accounts (name, group_name, is_system) VALUES
('Cash',            'Cash-in-Hand',     1),
('Bank',            'Bank Accounts',    1),
('Sales',           'Sales Accounts',   1),
('Purchase',        'Purchase Accounts',1),
('CGST Payable',    'Duties & Taxes',   1),
('SGST Payable',    'Duties & Taxes',   1),
('IGST Payable',    'Duties & Taxes',   1),
('CGST Input',      'Duties & Taxes',   1),
('SGST Input',      'Duties & Taxes',   1),
('IGST Input',      'Duties & Taxes',   1),
('Discount Given',  'Indirect Expenses',1),
('Freight Charges', 'Indirect Expenses',1),
('Capital Account', 'Capital Account',  1);
```

### Default Admin User
```sql
INSERT OR IGNORE INTO users (username, password, full_name, role)
VALUES ('admin', '<sha256 of "admin123">', 'Administrator', 'Admin');
```

---

## 6. GST Engine Rules

### 6.1 Intra-state vs Inter-state
```
company.state_code == party.state_code  →  CGST + SGST  (each = gst_rate / 2)
company.state_code != party.state_code  →  IGST          (= gst_rate)
```

### 6.2 GST Rate Slabs
Only these rates are valid: `0`, `5`, `12`, `18`, `28`

### 6.3 Common HSN Codes (pre-populate item creation dropdown)
| HSN Code | Description | GST Rate |
|---|---|---|
| 4412 | Plywood, veneered panels, blockboard | 18% |
| 4418 | Flush doors, builders' joinery, wood panel products | 18% |
| 4421 | Particle board, MDF, fibreboard | 18% |
| 4415 | Packing cases, wooden boxes | 12% |
| 4414 | Wooden frames for paintings, photos | 12% |
| 3214 | Wood putty, fillers | 18% |
| 7317 | Nails, tacks, staples (hardware) | 18% |

### 6.4 Tax Calculation Per Line Item
```
taxable_amount  = (qty × rate) - discount_amount
cgst_amount     = taxable_amount × (cgst_rate / 100)   [if intra-state]
sgst_amount     = taxable_amount × (sgst_rate / 100)   [if intra-state]
igst_amount     = taxable_amount × (igst_rate / 100)   [if inter-state]
line_total      = taxable_amount + cgst_amount + sgst_amount + igst_amount
```

### 6.5 GSTR-1 Data Structure
- **B2B**: Sales to GST-registered parties — group by GSTIN, show invoice-wise
- **B2C Large**: Sales to unregistered, invoice value > ₹2.5 Lakh — invoice-wise
- **B2C Small**: All other B2C sales — aggregated by state and rate
- **CDNR**: Credit/debit notes to registered parties

---

## 7. Module Descriptions

### 7.1 Module: Masters (Phase 1)
Screen for managing all master records. Each master has:
- A searchable list/table view (Treeview) as the main view
- An Add/Edit form (either modal dialog or right-panel)
- Inline search bar to filter records
- Double-click on row to open edit form

**Party Master fields:** Name*, Type*, GSTIN, PAN, State*, State Code*, Phone, Email, Address, Credit Limit, Credit Days, Opening Balance, Balance Type
**Item Master fields:** Name*, Category*, HSN Code*, Unit*, Thickness, Size, GST Rate*, Purchase Rate*, Sale Rate*, Reorder Level, Opening Stock
**Godown Master fields:** Name*, Address
**Account Master fields:** Name*, Group*, Opening Balance, Balance Type

### 7.2 Module: Sales Invoice (Phase 1)
Tally-style form layout:
```
[Party Name ▼]          [Invoice No: SI-2024-001]    [Date: DD/MM/YYYY]
[Godown ▼]              [Due Date: DD/MM/YYYY]        [Reference No]

Item Table:
# | Item | HSN | Qty | Unit | Rate | Disc% | Taxable | GST% | CGST | SGST | IGST | Total

[+ Add Row]

                                        Subtotal:  ___
                                        Discount:  ___
                                    Taxable Amt:   ___
                                          CGST:    ___
                                          SGST:    ___
                                          IGST:    ___
                                   Grand Total:    ___
[Narration]                        Amount in Words: Rupees ___

[Save Draft]  [Confirm & Print]  [Share PDF]  [Cancel]
```

### 7.3 Module: Purchase Invoice (Phase 1)
Same structure as Sales Invoice but:
- Party type is Supplier
- Triggers stock IN movement
- Creates ITC journal entries (CGST Input, SGST Input, IGST Input)

### 7.4 Module: Inventory (Phase 2)
- **GRN (Goods Receipt Note):** Linked to Purchase Order or standalone. Updates stock + table.
- **Stock View:** Grid of item × godown with current qty. Filter by godown, category, low stock.
- **Stock Adjustment:** Entry to add or reduce stock with reason (damage, found, opening).
- **Godown Transfer:** Move stock between godowns with a transfer challan.
- **Stock Movement Report:** Full audit trail — item-wise, date-range filter.

### 7.5 Module: Accounting (Phase 2)
- **Ledger View:** Select any account → see all Dr/Cr entries, running balance
- **Cash Book:** Cash account ledger with daily totals
- **Bank Book:** Bank account ledger with reconciliation flag
- **Journal Voucher:** Manual double-entry form
- **Trial Balance:** All accounts with opening + transaction + closing balances
- **P&L Statement:** Income vs Expense for selected date range
- **Balance Sheet:** Assets vs Liabilities snapshot

### 7.6 Module: GST Reports (Phase 2)
- **GSTR-1 Summary:** B2B table, B2C table, CDNR table — month-wise filter
- **GSTR-3B Summary:** Net tax payable calculation with ITC offset
- **HSN Summary:** Required for GSTR-1 — item-wise HSN with qty, value, taxes
- **ITC Register:** All purchase invoices with eligible ITC amounts
- **Export:** All GST reports exportable to Excel (.xlsx) via openpyxl

---

## 8. Voucher Number Generation

Function in `modules/masters.py`:
```python
def generate_voucher_no(conn, voucher_type: str, date: str) -> str:
    """
    Generates next voucher number for the given type.
    Format: PREFIX-YY-NNNN  e.g. SI-25-0001
    Uses voucher_sequences table. Increments last_number atomically.
    """
    year_suffix = date[2:4]  # from 'YYYY-MM-DD'
    row = conn.execute(
        "SELECT prefix, last_number FROM voucher_sequences WHERE voucher_type=?",
        (voucher_type,)
    ).fetchone()
    new_num = row[1] + 1
    conn.execute(
        "UPDATE voucher_sequences SET last_number=? WHERE voucher_type=?",
        (new_num, voucher_type)
    )
    return f"{row[0]}-{year_suffix}-{new_num:04d}"
```

---

## 9. db/connection.py (exact implementation required)

```python
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plywoodpro.db')

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row        # access columns by name
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn
```

---

## 10. UI Layout & Navigation

### Main Window
```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] PlywoodPro          [Company Name]    [Date] [User] │  ← Top bar (height 50px)
├───────────┬─────────────────────────────────────────────────┤
│           │                                                 │
│  NAV      │   CONTENT AREA                                  │
│  SIDEBAR  │   (swapped by navigation)                       │
│  (200px)  │                                                 │
│           │                                                 │
│ Dashboard │                                                 │
│ ──────    │                                                 │
│ Masters   │                                                 │
│  Parties  │                                                 │
│  Items    │                                                 │
│  Godowns  │                                                 │
│  Accounts │                                                 │
│ ──────    │                                                 │
│ Sales     │                                                 │
│  Invoice  │                                                 │
│  Orders   │                                                 │
│  Receipts │                                                 │
│ ──────    │                                                 │
│ Purchase  │                                                 │
│  Invoice  │                                                 │
│  Orders   │                                                 │
│  Payments │                                                 │
│ ──────    │                                                 │
│ Inventory │                                                 │
│ ──────    │                                                 │
│ Accounts  │                                                 │
│ ──────    │                                                 │
│ GST       │                                                 │
│ ──────    │                                                 │
│ Reports   │                                                 │
│ ──────    │                                                 │
│ Settings  │                                                 │
│           │                                                 │
└───────────┴─────────────────────────────────────────────────┘
```

### Window Defaults
- Minimum size: 1200 × 700 px
- Default size: 1366 × 768 px (most common Indian SMB laptop resolution)
- Resizable: Yes
- Title bar: `PlywoodPro — [Company Name]`

---

## 11. Plywood-Specific Business Rules

1. **Unit conversions** — When unit is `Sq.Ft`, calculate from sheets:
   - 8×4 sheet = 32 sq.ft | 7×3.5 sheet = 24.5 sq.ft | 6×3 sheet = 18 sq.ft
   - Allow manual sq.ft entry override

2. **Thickness grouping** — Stock reports must be groupable by thickness when category is Plywood/Blockboard

3. **Standard sizes dropdown** — `8x4 ft`, `7x3.5 ft`, `6x3 ft`, `Custom` — when Custom selected, show width × height inputs

4. **Credit customer workflow** — If party has credit_limit > 0:
   - On invoice creation, check outstanding balance
   - If balance + new invoice > credit_limit → show warning popup (allow override for Admin/Manager)

5. **Damage/Wastage** — Stock Adjustment with type = `ADJUSTMENT` and negative qty. Must prompt for reason: `Damage`, `Breakage`, `Theft`, `Moisture Damage`, `Other`

6. **Transport details** — Sales Invoice must optionally capture: Transport Name, Vehicle No, LR Number, Dispatch Date

---

## 12. PDF Invoice Layout (ReportLab)

### GST Tax Invoice must contain (legally required):
1. Title: "TAX INVOICE" (bold, centered, large)
2. Supplier details: Name, Address, GSTIN, State, Phone
3. Buyer details: Name, Address, GSTIN, State
4. Invoice number and date
5. Items table: Sr#, Description, HSN, Qty, Unit, Rate, Disc, Taxable Value, GST%, CGST, SGST, IGST, Total
6. Totals: Subtotal, Discount, Taxable Total, CGST Total, SGST Total, IGST Total, Grand Total
7. Amount in words (Indian numbering: Rupees — Lakhs, Thousands)
8. Payment terms / due date
9. Bank details for payment
10. Authorized signatory box
11. Note: "This is a computer generated invoice"

---

## 13. Error Handling Standards

- **All database operations** must be wrapped in `try/except sqlite3.Error`
- **On error:** Show `CTkMessagebox` with title "Error", icon "cancel", and the error message
- **On success (create/update/delete):** Show `CTkMessagebox` with title "Success", icon "check"
- **Form validation:** Validate all required fields before DB call. Highlight empty required fields in red border
- **Never crash silently** — all `except` blocks must at minimum `print()` the traceback

---

## 14. Coding Standards

- All Python files must have a module-level docstring explaining what the file does
- Functions must have docstrings for any function longer than 10 lines
- Use `f-strings` for string formatting (not `.format()` or `%`)
- Date display to user: `DD/MM/YYYY` (Indian format)
- Date storage in DB: `YYYY-MM-DD`
- Currency display: `₹ 1,23,456.00` (Indian numbering — lakhs and crores)
- All amounts rounded to 2 decimal places using `round(value, 2)`
- Use `Decimal` from `decimal` module for all monetary calculations to avoid float errors
- Every UI form that saves data must have a `clear_form()` method to reset fields

---

## 15. Phase Build Order

Build in this exact order. Each phase must be fully working before starting the next.

| Phase | Scope | Files |
|---|---|---|
| **Phase 1** | DB + Navigation + Master Data | `db/`, `main.py`, `ui/masters_ui.py`, `ui/settings_ui.py`, `modules/masters.py` |
| **Phase 2** | Sales Invoice + Purchase Invoice | `modules/sales.py`, `modules/purchase.py`, `ui/sales_ui.py`, `ui/purchase_ui.py`, `utils/pdf_export.py` |
| **Phase 3** | Inventory (GRN, stock view, adjustment) | `modules/inventory.py`, `ui/inventory_ui.py` |
| **Phase 4** | Accounting (ledger, journal, trial balance) | `modules/accounting.py`, `ui/accounting_ui.py` |
| **Phase 5** | GST Reports (GSTR-1, GSTR-3B, ITC) | `modules/gst.py`, `ui/gst_ui.py`, `utils/excel_export.py` |
| **Phase 6** | Dashboard + All Reports | `ui/dashboard.py`, `modules/reports.py`, `ui/reports_ui.py` |
| **Phase 7** | User login, polish, PyInstaller exe | `ui/login.py`, packaging config |

---

## 16. First Prompt to Execute (Phase 1)

When you receive this file, your first task is **Phase 1 only**. Build:

1. `db/connection.py` — exactly as defined in Section 9
2. `db/schema.sql` — all 13 CREATE TABLE statements from Section 4, in order
3. `db/init_db.py` — reads `schema.sql`, creates all tables, inserts seed data from Section 5
4. `main.py` — CustomTkinter main window with sidebar nav and content area switcher (Section 10 layout)
5. `modules/masters.py` — CRUD functions for Party, Item, Godown, Account
6. `ui/masters_ui.py` — Party Master screen with searchable Treeview list + Add/Edit form
7. `ui/settings_ui.py` — Company setup form (first-run wizard if company table is empty)
8. `requirements.txt` — from Section 2

**Output rules:**
- Print the full path and complete code for every file — no truncation, no `# ... rest of code`
- Code must be immediately runnable with `python main.py` after `pip install -r requirements.txt`
- Do not ask clarifying questions — build based on this spec

---

*End of PlywoodPro Master Technical Specification v1.0*
*Generated: April 2026*

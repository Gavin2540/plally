# PlywoodPro

**Tally-style Desktop Business Suite for Plywood Dealers**

GST-compliant invoicing, double-entry accounting, inventory management, and financial reporting — built with Python, CustomTkinter, and SQLite.

---

## Quick Start (from source)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python ui/login.py
```

### Default Login
| Field    | Value     |
|----------|-----------|
| Username | `admin`   |
| Password | `admin123`|

> Change the default password immediately after first login via the **Password** button in the top bar.

---

## Build Windows Executable

```bash
# One-click build
build.bat

# Or manually
pip install pyinstaller
pyinstaller build.spec --clean
```

Output: `dist\PlywoodPro\PlywoodPro.exe`

---

## Features

### Phase 1 — Foundations
- Company setup, party/item/godown/account masters
- SQLite WAL mode, dark themed UI

### Phase 2 — Invoicing
- Sales & Purchase invoices with GST auto-calculation
- CGST/SGST (intra-state) and IGST (inter-state) support
- Legal GST invoice PDF export (all 11 required fields)

### Phase 3 — Inventory
- GRN processing, stock adjustments, godown transfers
- Low stock monitoring with reorder alerts

### Phase 4 — Accounting
- Double-entry journal vouchers with Dr/Cr validation
- Ledger, Trial Balance, Profit & Loss, Balance Sheet
- All reports exportable to PDF

### Phase 5 — GST Reports
- GSTR-1: B2B, B2C, CDNR, HSN Summary (Excel export)
- GSTR-3B: Net tax payable summary (PDF export)
- ITC Register with eligibility flagging

### Phase 6 — Dashboard & Reports
- Live KPI dashboard (auto-refresh every 60s)
- Sales/Purchase registers, Party outstanding
- Item profit report with margin analysis
- Stock valuation report

### Phase 7 — Login & Packaging
- SHA-256 password authentication
- 3-attempt lockout with 30-second countdown
- Database backup with timestamp
- PyInstaller Windows executable

---

## Database Backup

Click the **Backup** button in the top bar to create a timestamped copy:
```
backups/plywoodpro_20260422_153000.db
```

---

## Folder Structure

```
plally/
├── ui/                  # UI screens (CustomTkinter)
│   ├── login.py         # Entry point — login screen
│   ├── dashboard.py     # KPI dashboard
│   ├── sales_ui.py      # Sales invoice form
│   ├── purchase_ui.py   # Purchase invoice form
│   ├── inventory_ui.py  # Stock management
│   ├── accounting_ui.py # Ledger, JV, Trial Balance
│   ├── gst_ui.py        # GST reports
│   ├── reports_ui.py    # Registers & profitability
│   └── ...
├── modules/             # Business logic (no UI)
│   ├── sales.py
│   ├── purchase.py
│   ├── inventory.py
│   ├── accounting.py
│   ├── gst.py
│   └── reports.py
├── db/                  # Database
│   ├── schema.sql
│   ├── init_db.py
│   └── connection.py
├── utils/               # Shared utilities
│   ├── pdf_export.py
│   ├── excel_export.py
│   ├── gst_engine.py
│   └── helpers.py
├── tests/               # Integration tests (109 tests)
├── exports/             # Generated PDFs and Excel files
├── backups/             # Database backups
├── main.py              # Main application window
├── build.spec           # PyInstaller build config
├── build.bat            # One-click build script
└── requirements.txt
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language  | Python 3.10+ |
| UI        | CustomTkinter (dark theme) |
| Database  | SQLite 3 (WAL mode) |
| PDF       | ReportLab |
| Excel     | OpenPyXL |
| Packaging | PyInstaller |

---

## Tests

```bash
# Run all tests (seed + verify)
python tests/test_phase2.py    # 26 tests
python tests/test_phase3.py    # 17 tests
python tests/test_phase4.py    # 16 tests
python tests/test_phase5.py    # 20 tests
python tests/test_phase6.py    # 30 tests
# Total: 109 tests
```

---

*Built with precision for the Indian plywood trading industry.*

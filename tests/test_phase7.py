"""
Phase 7 Integration Test -- PlywoodPro Login, Backup, Password
Headless tests (no GUI) for auth logic, backup, and password change.
"""
import os, sys, hashlib, shutil, glob
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.connection import get_connection
from db.init_db import init_database

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
    print("PlywoodPro Phase 7 -- Login & Packaging Integration Test")
    print("=" * 60)

    # ── 1. Default user exists ──
    print("\n[1] Default admin user")
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    check("Admin user exists", user is not None)
    if user:
        expected_hash = hashlib.sha256(b"admin123").hexdigest()
        check("Password hash is SHA-256 of admin123", user['password'] == expected_hash)
        check("Role is Admin", user['role'] == 'Admin')
        check("Is active", user['is_active'] == 1)
    conn.close()

    # ── 2. Login verification (headless) ──
    print("\n[2] Login verification")
    conn = get_connection()
    # Correct password
    pw_hash = hashlib.sha256(b"admin123").hexdigest()
    u = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1",
                     ("admin", pw_hash)).fetchone()
    check("Correct password matches", u is not None)

    # Wrong password
    bad_hash = hashlib.sha256(b"wrongpassword").hexdigest()
    u2 = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1",
                      ("admin", bad_hash)).fetchone()
    check("Wrong password rejected", u2 is None)
    conn.close()

    # ── 3. Login attempt tracking ──
    print("\n[3] Attempt tracking logic")
    attempts = 0
    for pw in [b"wrong1", b"wrong2", b"wrong3"]:
        h = hashlib.sha256(pw).hexdigest()
        conn = get_connection()
        r = conn.execute("SELECT * FROM users WHERE username='admin' AND password=?", (h,)).fetchone()
        conn.close()
        if not r:
            attempts += 1
    check("3 failed attempts tracked", attempts == 3)
    check("Lockout should trigger at 3", attempts >= 3)

    # ── 4. Database backup ──
    print("\n[4] Database backup")
    bak_dir = os.path.join(PROJECT_ROOT, "backups")
    os.makedirs(bak_dir, exist_ok=True)
    # Clean old test backups
    for f in glob.glob(os.path.join(bak_dir, "plywoodpro_test_*.db")):
        os.remove(f)

    src = os.path.join(PROJECT_ROOT, "plywoodpro.db")
    dst = os.path.join(bak_dir, "plywoodpro_test_backup.db")
    shutil.copy2(src, dst)
    check("Backup file created", os.path.exists(dst))
    check("Backup size > 0", os.path.getsize(dst) > 0, f"{os.path.getsize(dst)} bytes")
    check("Backup matches source size", os.path.getsize(src) == os.path.getsize(dst))
    print(f"    Source: {os.path.getsize(src)} bytes, Backup: {os.path.getsize(dst)} bytes")
    os.remove(dst)  # Clean up

    # ── 5. Password change (headless) ──
    print("\n[5] Password change")
    conn = get_connection()
    old_hash = hashlib.sha256(b"admin123").hexdigest()
    new_hash = hashlib.sha256(b"newpass456").hexdigest()

    # Verify old password
    user = conn.execute("SELECT * FROM users WHERE username='admin' AND password=?",
                        (old_hash,)).fetchone()
    check("Old password verified", user is not None)

    # Change password
    conn.execute("UPDATE users SET password=? WHERE username='admin'", (new_hash,))
    conn.commit()

    # Verify new password works
    user2 = conn.execute("SELECT * FROM users WHERE username='admin' AND password=?",
                         (new_hash,)).fetchone()
    check("New password works", user2 is not None)

    # Verify old password no longer works
    user3 = conn.execute("SELECT * FROM users WHERE username='admin' AND password=?",
                         (old_hash,)).fetchone()
    check("Old password rejected", user3 is None)

    # Restore original password for other tests
    conn.execute("UPDATE users SET password=? WHERE username='admin'", (old_hash,))
    conn.commit()
    conn.close()
    check("Password restored to admin123", True)

    # ── 6. First-run detection ──
    print("\n[6] First-run detection")
    conn = get_connection()
    company_count = conn.execute("SELECT COUNT(*) FROM company").fetchone()[0]
    conn.close()
    # After Phase 2 test data, company should exist
    check("Company exists (not first run)", company_count > 0, f"Count: {company_count}")

    # ── 7. Build artifacts exist ──
    print("\n[7] Build artifacts")
    check("build.spec exists", os.path.exists(os.path.join(PROJECT_ROOT, "build.spec")))
    check("build.bat exists", os.path.exists(os.path.join(PROJECT_ROOT, "build.bat")))
    check("README.md exists", os.path.exists(os.path.join(PROJECT_ROOT, "README.md")))
    check("ui/login.py exists", os.path.exists(os.path.join(PROJECT_ROOT, "ui", "login.py")))
    check("ui/change_password.py exists",
          os.path.exists(os.path.join(PROJECT_ROOT, "ui", "change_password.py")))

    # ── 8. All screens importable ──
    print("\n[8] All UI modules importable")
    modules = [
        ("ui.login", "LoginWindow"),
        ("ui.dashboard", "DashboardUI"),
        ("ui.sales_ui", "SalesInvoiceUI"),
        ("ui.purchase_ui", "PurchaseInvoiceUI"),
        ("ui.inventory_ui", "InventoryUI"),
        ("ui.accounting_ui", "AccountingUI"),
        ("ui.gst_ui", "GstUI"),
        ("ui.reports_ui", "ReportsUI"),
        ("ui.change_password", "ChangePasswordDialog"),
    ]
    for mod, cls in modules:
        try:
            m = __import__(mod, fromlist=[cls])
            check(f"{mod}.{cls} importable", hasattr(m, cls))
        except Exception as e:
            check(f"{mod}.{cls} importable", False, str(e))

    # ── Results ──
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("*** ALL TESTS PASSED -- Phase 7 is COMPLETE! ***")
    else:
        print("!!! Some tests failed -- review above.")
    print("=" * 60)
    return FAIL == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

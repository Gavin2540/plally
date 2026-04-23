"""
PlywoodPro — Main Application Entry Point
==========================================
Windows desktop application for plywood dealers, timber merchants,
and wood panel distributors in India. Built with CustomTkinter + SQLite3.

This file initialises the main window, sidebar navigation, content area,
and routes between different modules. Also triggers database setup on first run.
"""

import os
import sys
import customtkinter as ctk
from datetime import date

# ── Ensure project root is on sys.path ──────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Database initialisation ─────────────────────────────────────────
from db.init_db import init_database
from modules.masters import get_company
from utils.helpers import today_display

# ── UI Modules ──────────────────────────────────────────────────────
from ui.settings_ui import SettingsUI
from ui.masters_ui import MastersUI
from ui.sales_ui import SalesInvoiceUI
from ui.purchase_ui import PurchaseInvoiceUI
from ui.inventory_ui import InventoryUI
from ui.accounting_ui import AccountingUI
from ui.gst_ui import GstUI
from ui.dashboard import DashboardUI
from ui.reports_ui import ReportsUI
from ui.orders_ui import OrdersUI
from ui.payments_ui import PaymentsUI


# ── Appearance defaults ─────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ── Constants ───────────────────────────────────────────────────────
ACCENT_COLOR = "#2E7D32"
ACCENT_HOVER = "#1B5E20"
SIDEBAR_WIDTH = 200
TOPBAR_HEIGHT = 50
MIN_WIDTH = 1200
MIN_HEIGHT = 700
DEFAULT_WIDTH = 1366
DEFAULT_HEIGHT = 768


class PlywoodProApp(ctk.CTk):
    """Main application window for PlywoodPro."""

    def __init__(self, login_window=None, logged_in_user=None):
        super().__init__()
        self.login_window = login_window
        self.logged_in_user = logged_in_user or {}

        # ── Initialise database on first run ───────────────────────
        init_database()

        # ── Create folders if missing ──────────────────────────────
        for d in ('exports', 'backups'):
            p = os.path.join(PROJECT_ROOT, d)
            if not os.path.exists(p): os.makedirs(p)

        # ── Window configuration ───────────────────────────────────
        self.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self._set_window_title()

        # ── Track active navigation ────────────────────────────────
        self.active_nav_button = None
        self.nav_buttons = {}

        # ── Build the main layout ──────────────────────────────────
        self._build_topbar()
        self._build_sidebar()
        self._build_content_area()

        # ── Show first-run wizard or dashboard ─────────────────────
        company = get_company()
        if not company:
            self._navigate_to("Settings")
        else:
            self._navigate_to("Dashboard")

    # ═══════════════════════════════════════════════════════════════
    #  WINDOW TITLE
    # ═══════════════════════════════════════════════════════════════

    def _set_window_title(self):
        """Set the title bar text: 'PlywoodPro — [Company Name]'."""
        company = get_company()
        if company and company.get('name'):
            self.title(f"PlywoodPro — {company['name']}")
        else:
            self.title("PlywoodPro — Setup Required")

    def update_title_bar(self):
        """Public method called after company details are saved."""
        self._set_window_title()
        # Also refresh the company name in the top bar
        company = get_company()
        if company and company.get('name'):
            self.company_label.configure(text=company['name'])

    # ═══════════════════════════════════════════════════════════════
    #  TOP BAR
    # ═══════════════════════════════════════════════════════════════

    def _build_topbar(self):
        """
        Build the top bar with logo text, company name, date, and user info.
        Height: 50px, spans full width.
        """
        self.topbar = ctk.CTkFrame(self, height=TOPBAR_HEIGHT, corner_radius=0)
        self.topbar.pack(fill="x", side="top")
        self.topbar.pack_propagate(False)

        # ── Left side: Logo / App name ─────────────────────────────
        logo_label = ctk.CTkLabel(
            self.topbar, text="🪵  PlywoodPro",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=ACCENT_COLOR,
        )
        logo_label.pack(side="left", padx=15)

        # ── Center: Company name ───────────────────────────────────
        company = get_company()
        company_name = company['name'] if company and company.get('name') else 'Setup Required'
        self.company_label = ctk.CTkLabel(
            self.topbar, text=company_name,
            font=ctk.CTkFont(size=14),
        )
        self.company_label.pack(side="left", padx=30)

        # ── Right side: Actions ────────────────────────────────────
        ctk.CTkButton(self.topbar, text="Logout", fg_color="#C62828", width=70,
                       height=30, command=self._logout).pack(side="right", padx=5)
        ctk.CTkButton(self.topbar, text="About", fg_color="#555", width=60,
                       height=30, command=self._show_about).pack(side="right", padx=5)
        ctk.CTkButton(self.topbar, text="Backup", fg_color="#1565C0", width=70,
                       height=30, command=self._backup_db).pack(side="right", padx=5)
        ctk.CTkButton(self.topbar, text="Password", fg_color="#555", width=75,
                       height=30, command=self._change_password).pack(side="right", padx=5)

        user_name = self.logged_in_user.get('full_name', 'Admin')
        user_label = ctk.CTkLabel(
            self.topbar, text=f"  {user_name}",
            font=ctk.CTkFont(size=12),
        )
        user_label.pack(side="right", padx=5)

        date_label = ctk.CTkLabel(
            self.topbar, text=f"  {today_display()}",
            font=ctk.CTkFont(size=12),
        )
        date_label.pack(side="right", padx=10)

    # ═══════════════════════════════════════════════════════════════
    #  SIDEBAR NAVIGATION
    # ═══════════════════════════════════════════════════════════════

    def _build_sidebar(self):
        """
        Build the left sidebar with navigation buttons.
        Width: 200px, dark background, grouped by module.
        """
        self.sidebar = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.pack(fill="y", side="left")
        self.sidebar.pack_propagate(False)

        # Scrollable container for navigation items
        self.nav_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color="#555555",
        )
        self.nav_scroll.pack(fill="both", expand=True, padx=0, pady=5)

        # ── Navigation Structure ───────────────────────────────────
        nav_items = [
            ("section", "MAIN"),
            ("nav", "Dashboard",  "📊"),

            ("section", "MASTERS"),
            ("nav", "Parties",    "👥"),
            ("nav", "Items",      "📦"),
            ("nav", "Godowns",    "🏭"),
            ("nav", "Accounts",   "📒"),

            ("section", "TRANSACTIONS"),
            ("nav", "Sales Invoice",     "🧾"),
            ("nav", "Sales Orders",      "📋"),
            ("nav", "Receipts",          "💰"),

            ("separator", None, None),

            ("nav", "Purchase Invoice",  "🛒"),
            ("nav", "Purchase Orders",   "📝"),
            ("nav", "Payments",          "💳"),

            ("section", "OPERATIONS"),
            ("nav", "Inventory",   "📊"),
            ("nav", "Accounting",  "📖"),
            ("nav", "GST Reports", "🏛"),
            ("nav", "Reports",     "📈"),

            ("section", "SYSTEM"),
            ("nav", "Settings",    "⚙"),
        ]

        for item in nav_items:
            if item[0] == "section":
                self._add_section_label(item[1])
            elif item[0] == "separator":
                sep = ctk.CTkFrame(self.nav_scroll, height=1, fg_color="#444444")
                sep.pack(fill="x", padx=10, pady=5)
            elif item[0] == "nav":
                self._add_nav_button(item[1], item[2])

    def _add_section_label(self, text: str):
        """Add a section header label to the sidebar."""
        label = ctk.CTkLabel(
            self.nav_scroll, text=text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#888888",
        )
        label.pack(anchor="w", padx=15, pady=(12, 2))

    def _add_nav_button(self, name: str, icon: str):
        """Add a navigation button to the sidebar."""
        btn = ctk.CTkButton(
            self.nav_scroll,
            text=f"  {icon}  {name}",
            anchor="w",
            height=32,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#333333",
            text_color="#CCCCCC",
            font=ctk.CTkFont(size=13),
            command=lambda n=name: self._navigate_to(n),
        )
        btn.pack(fill="x", padx=8, pady=1)
        self.nav_buttons[name] = btn

    def _set_active_nav(self, name: str):
        """Highlight the active navigation button and reset others."""
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=ACCENT_COLOR, text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#CCCCCC")

    # ═══════════════════════════════════════════════════════════════
    #  CONTENT AREA
    # ═══════════════════════════════════════════════════════════════

    def _build_content_area(self):
        """Build the main content area that holds swappable screens."""
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, side="right")

        # Will hold the current active screen
        self.current_screen = None

    def _clear_content(self):
        """Remove the current screen from the content area."""
        if self.current_screen:
            self.current_screen.destroy()
            self.current_screen = None

    # ═══════════════════════════════════════════════════════════════
    #  NAVIGATION ROUTER
    # ═══════════════════════════════════════════════════════════════

    def _navigate_to(self, screen_name: str):
        """
        Navigate to a screen by name. Clears the content area and
        loads the appropriate module screen.
        """
        self._clear_content()
        self._set_active_nav(screen_name)

        if screen_name == "Dashboard":
            self._show_dashboard()
        elif screen_name in ("Parties", "Items", "Godowns", "Accounts"):
            self._show_masters(screen_name)
        elif screen_name == "Sales Invoice":
            self._show_sales_invoice()
        elif screen_name == "Purchase Invoice":
            self._show_purchase_invoice()
        elif screen_name == "Inventory":
            self._show_inventory()
        elif screen_name == "Accounting":
            self._show_accounting()
        elif screen_name == "GST Reports":
            self._show_gst()
        elif screen_name == "Reports":
            self._show_reports()
        elif screen_name == "Settings":
            self._show_settings()
        elif screen_name == "Sales Orders":
            self._show_orders('sales')
        elif screen_name == "Purchase Orders":
            self._show_orders('purchase')
        elif screen_name == "Receipts":
            self._show_payments('receipts')
        elif screen_name == "Payments":
            self._show_payments('payments')

    def _show_dashboard(self):
        """Show the live Dashboard with KPIs and quick actions."""
        screen = DashboardUI(self.content_area, app=self)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_masters(self, tab_name: str):
        """Show the Masters UI and switch to the requested tab."""
        masters = MastersUI(self.content_area, app=self)
        masters.pack(fill="both", expand=True)

        # Map nav names to tab names
        tab_map = {
            "Parties": "Parties",
            "Items": "Items",
            "Godowns": "Godowns",
            "Accounts": "Accounts",
        }

        target_tab = tab_map.get(tab_name, "Parties")
        masters.show_tab(target_tab)
        self.current_screen = masters

    def _show_settings(self):
        """Show the Settings / Company Setup screen."""
        settings = SettingsUI(self.content_area, app=self)
        settings.pack(fill="both", expand=True)
        self.current_screen = settings

    def _show_sales_invoice(self):
        """Show the Sales Invoice form."""
        screen = SalesInvoiceUI(self.content_area, app=self)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_purchase_invoice(self):
        """Show the Purchase Invoice form."""
        screen = PurchaseInvoiceUI(self.content_area, app=self)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_inventory(self):
        """Show the Inventory Management screen."""
        screen = InventoryUI(self.content_area, app=self)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_accounting(self):
        """Show the Accounting screen."""
        screen = AccountingUI(self.content_area, app=self)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_gst(self):
        """Show the GST Reports screen."""
        screen = GstUI(self.content_area, app=self)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_reports(self):
        """Show the Reports hub screen."""
        screen = ReportsUI(self.content_area, app=self)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_orders(self, tab='sales'):
        """Show the Sales/Purchase Orders screen."""
        screen = OrdersUI(self.content_area, app=self, tab=tab)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _show_payments(self, tab='receipts'):
        """Show the Receipts/Payments screen."""
        screen = PaymentsUI(self.content_area, app=self, tab=tab)
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    # ═══════════════════════════════════════════════════════════════
    #  TOP BAR ACTIONS
    # ═══════════════════════════════════════════════════════════════

    def _logout(self):
        """Close main window, reopen login."""
        self.destroy()
        if self.login_window:
            self.login_window.deiconify()
            self.login_window.pass_entry.delete(0, "end")
            self.login_window.status_label.configure(text="Logged out.", text_color="#888")
            self.login_window.attempts = 0

    def _backup_db(self):
        """Copy plywoodpro.db to backups/ with timestamp."""
        import shutil
        from datetime import datetime
        from CTkMessagebox import CTkMessagebox
        src = os.path.join(PROJECT_ROOT, "plywoodpro.db")
        bak_dir = os.path.join(PROJECT_ROOT, "backups")
        os.makedirs(bak_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(bak_dir, f"plywoodpro_{ts}.db")
        try:
            shutil.copy2(src, dst)
            CTkMessagebox(title="Backup", message=f"Backup saved:\n{dst}", icon="check")
        except Exception as e:
            CTkMessagebox(title="Error", message=str(e), icon="cancel")

    def _change_password(self):
        """Open change password dialog."""
        uid = self.logged_in_user.get('id', 1)
        from ui.change_password import ChangePasswordDialog
        ChangePasswordDialog(self, user_id=uid)

    def _show_about(self):
        """Show About dialog."""
        win = ctk.CTkToplevel(self)
        win.title("About PlywoodPro"); win.geometry("400x280"); win.resizable(False, False)
        win.grab_set()
        ctk.CTkLabel(win, text="PlywoodPro", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#2E7D32").pack(pady=(25, 5))
        ctk.CTkLabel(win, text="Version 1.0.0", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(win, text="Build: April 2026", font=ctk.CTkFont(size=12),
                     text_color="#888").pack(pady=5)
        ctk.CTkLabel(win, text="Tally-style Desktop Business Suite\n\n"
                     "Tech: Python 3 | CustomTkinter | SQLite (WAL)\n"
                     "Reports: ReportLab (PDF) | OpenPyXL (Excel)\n"
                     "GST Compliant | Double-Entry Accounting",
                     font=ctk.CTkFont(size=11), justify="center").pack(pady=10)
        ctk.CTkButton(win, text="Close", width=100, command=win.destroy).pack(pady=10)

    def _show_coming_soon(self, module_name: str):
        """Show a placeholder for modules not yet built in Phase 1."""
        frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(
            frame, text=f"🚧  {module_name}",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", pady=(0, 20))

        ctk.CTkLabel(
            frame,
            text=f"The {module_name} module will be available in a future phase.",
            font=ctk.CTkFont(size=14),
            text_color="#AAAAAA",
        ).pack(anchor="w")

        # Phase mapping info
        phase_map = {
            "Sales Invoice": "Phase 2",
            "Sales Orders": "Phase 2",
            "Receipts": "Phase 2",
            "Purchase Invoice": "Phase 2",
            "Purchase Orders": "Phase 2",
            "Payments": "Phase 2",
            "Inventory": "Phase 3",
            "Accounting": "Phase 4",
            "GST Reports": "Phase 5",
            "Reports": "Phase 6",
        }
        phase = phase_map.get(module_name, "a future phase")

        ctk.CTkLabel(
            frame,
            text=f"Scheduled for: {phase}",
            font=ctk.CTkFont(size=12),
            text_color="#666666",
        ).pack(anchor="w", pady=(10, 0))

        self.current_screen = frame


# ═══════════════════════════════════════════════════════════════════════
#  APPLICATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = PlywoodProApp()
    app.mainloop()

"""
Dashboard UI for PlywoodPro — Home screen with KPIs, recent invoices,
low stock alerts, and quick action buttons.
"""
import customtkinter as ctk
from tkinter import ttk
from modules.reports import get_dashboard_stats
from modules.inventory import get_low_stock_items
from utils.helpers import format_inr

ACCENT = "#2E7D32"
BLUE = "#1565C0"
RED = "#C62828"
ORANGE = "#E65100"


class DashboardUI(ctk.CTkFrame):
    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build()
        self._refresh()
        self._schedule_refresh()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(hdr, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=ACCENT).pack(side="left")
        ctk.CTkButton(hdr, text="Refresh", fg_color=ACCENT, width=90,
                       command=self._refresh).pack(side="right")

        # KPI Cards
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.pack(fill="x", padx=20, pady=10)

        self.kpi_cards = {}
        cards = [
            ("today_sales", "Today's Sales", ACCENT, "0"),
            ("receivables", "Outstanding Receivables", BLUE, "0"),
            ("low_stock", "Low Stock Items", RED, "0"),
            ("pending_dc", "Pending Challans", ORANGE, "0"),
        ]
        for i, (key, title, color, val) in enumerate(cards):
            card = ctk.CTkFrame(self.kpi_frame, corner_radius=12, border_width=2, border_color=color)
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            self.kpi_frame.columnconfigure(i, weight=1)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11),
                         text_color="gray").pack(padx=15, pady=(12, 2), anchor="w")
            lbl = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=22, weight="bold"),
                               text_color=color)
            lbl.pack(padx=15, pady=(0, 12), anchor="w")
            self.kpi_cards[key] = lbl

        # Middle: Recent Invoices + Low Stock
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=20, pady=5)
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)

        # Recent Invoices
        lf = ctk.CTkFrame(mid, corner_radius=10)
        lf.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")
        mid.rowconfigure(0, weight=1)
        ctk.CTkLabel(lf, text="Recent Invoices", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=ACCENT).pack(padx=10, pady=(10, 5), anchor="w")
        cols_ri = ('invoice', 'date', 'party', 'amount', 'status')
        self.ri_tree = ttk.Treeview(lf, columns=cols_ri, show='headings', height=5)
        for c, t, w in [('invoice', 'Invoice', 90), ('date', 'Date', 80), ('party', 'Party', 140),
                         ('amount', 'Amount', 90), ('status', 'Status', 70)]:
            self.ri_tree.heading(c, text=t)
            self.ri_tree.column(c, width=w, anchor='e' if c == 'amount' else 'w')
        self.ri_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Low Stock
        rf = ctk.CTkFrame(mid, corner_radius=10)
        rf.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="nsew")
        ctk.CTkLabel(rf, text="Low Stock Alerts", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=RED).pack(padx=10, pady=(10, 5), anchor="w")
        cols_ls = ('item', 'qty', 'reorder', 'deficit')
        self.ls_tree = ttk.Treeview(rf, columns=cols_ls, show='headings', height=5)
        for c, t, w in [('item', 'Item', 180), ('qty', 'Current Qty', 80),
                         ('reorder', 'Reorder Level', 90), ('deficit', 'Deficit', 70)]:
            self.ls_tree.heading(c, text=t)
            self.ls_tree.column(c, width=w, anchor='e' if c != 'item' else 'w')
        self.ls_tree.tag_configure('alert', background='#FFCDD2')
        self.ls_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Quick Actions
        qa = ctk.CTkFrame(self, fg_color="transparent")
        qa.pack(fill="x", padx=20, pady=(5, 15))
        ctk.CTkLabel(qa, text="Quick Actions", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="gray").pack(anchor="w", pady=(0, 5))

        bf = ctk.CTkFrame(qa, fg_color="transparent")
        bf.pack(fill="x")
        actions = [
            ("New Sale Invoice", ACCENT, lambda: self._nav("Sales Invoice")),
            ("New Purchase Invoice", BLUE, lambda: self._nav("Purchase Invoice")),
            ("View Stock", ORANGE, lambda: self._nav("Inventory")),
            ("View Reports", "#7B1FA2", lambda: self._nav("Reports")),
        ]
        for text, color, cmd in actions:
            ctk.CTkButton(bf, text=text, fg_color=color, width=160, height=38,
                           font=ctk.CTkFont(size=13, weight="bold"),
                           command=cmd).pack(side="left", padx=8)

    def _nav(self, screen):
        if self.app and hasattr(self.app, 'show_screen'):
            self.app.show_screen(screen)

    def _refresh(self):
        stats = get_dashboard_stats()
        self.kpi_cards['today_sales'].configure(text=format_inr(stats['today_sales']))
        self.kpi_cards['receivables'].configure(text=format_inr(stats['receivables']))
        self.kpi_cards['low_stock'].configure(text=str(stats['low_stock_count']))
        self.kpi_cards['pending_dc'].configure(text=str(stats['pending_challans']))

        # Recent invoices
        self.ri_tree.delete(*self.ri_tree.get_children())
        for r in stats['recent_invoices']:
            self.ri_tree.insert('', 'end', values=(
                r.get('voucher_no', ''), r.get('date', ''),
                r.get('party_name', ''), format_inr(r.get('grand_total', 0)),
                r.get('status', '')))

        # Low stock
        self.ls_tree.delete(*self.ls_tree.get_children())
        low = get_low_stock_items()
        for r in low:
            deficit = (r.get('reorder_level', 0) or 0) - (r.get('total_qty', 0) or 0)
            self.ls_tree.insert('', 'end', values=(
                r.get('item_name', ''), f"{r.get('total_qty', 0):.0f}",
                r.get('reorder_level', 0), f"{deficit:.0f}"),
                tags=('alert',))

    def _schedule_refresh(self):
        self.after(60000, self._auto_refresh)

    def _auto_refresh(self):
        try:
            self._refresh()
        except Exception:
            pass
        self._schedule_refresh()

"""
Reports UI for PlywoodPro — Two tabs:
Tab 1: Registers (Sales, Purchase, Party Outstanding, Stock Valuation)
Tab 2: Profitability (Item Profit Report)
"""
import customtkinter as ctk
from tkinter import ttk
from CTkMessagebox import CTkMessagebox

from modules.reports import (
    get_sales_register, get_purchase_register, get_party_outstanding,
    get_item_profit_report, get_stock_valuation_report,
)
from utils.helpers import format_inr
from utils.pdf_export import export_sales_register_pdf, export_purchase_register_pdf, export_party_outstanding_pdf
from utils.excel_export import export_sales_register_excel, export_party_outstanding_excel, export_item_profit_excel
from utils.date_picker import DatePickerEntry

ACCENT = "#2E7D32"; BLUE = "#1565C0"; PURPLE = "#7B1FA2"


def _force_top(win):
    """Force a CTkToplevel to appear on top on Windows."""
    win.lift()
    win.attributes('-topmost', True)
    win.after(200, lambda: win.attributes('-topmost', False))
    win.focus_force()


class ReportsUI(ctk.CTkFrame):
    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        ctk.CTkLabel(self, text="Reports", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=ACCENT).pack(padx=10, pady=(10, 5), anchor="w")

        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)
        self.tabview.add("Registers"); self.tabview.add("Profitability")
        self._build_registers(self.tabview.tab("Registers"))
        self._build_profitability(self.tabview.tab("Profitability"))

    def _build_registers(self, tab):
        bf = ctk.CTkFrame(tab, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=15)
        for text, color, cmd in [
            ("Sales Register", ACCENT, self._open_sales_reg),
            ("Purchase Register", BLUE, self._open_purchase_reg),
            ("Party Outstanding", PURPLE, self._open_party_os),
            ("Stock Valuation", "#E65100", self._open_stock_val),
        ]:
            ctk.CTkButton(bf, text=text, fg_color=color, width=170, height=40,
                           font=ctk.CTkFont(size=13, weight="bold"),
                           command=cmd).pack(side="left", padx=10)

    def _build_profitability(self, tab):
        ctk.CTkButton(tab, text="Item Profit Report", fg_color=ACCENT, width=200, height=40,
                       font=ctk.CTkFont(size=14, weight="bold"),
                       command=self._open_item_profit).pack(padx=10, pady=15, anchor="w")

    # ── Register Windows ──

    def _open_sales_reg(self):
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Sales Register"); win.geometry("900x500")
        _force_top(win)

        f = ctk.CTkFrame(win, fg_color="transparent"); f.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f, text="From:").pack(side="left")
        df = DatePickerEntry(f, width=130); df.pack(side="left", padx=5)
        ctk.CTkLabel(f, text="To:").pack(side="left")
        dt = DatePickerEntry(f, width=130); dt.pack(side="left", padx=5)

        cols = ('date','invoice','party','taxable','cgst','sgst','igst','total','status')
        tree = ttk.Treeview(win, columns=cols, show='headings', height=14)
        for c,t,w in [('date','Date',80),('invoice','Invoice',100),('party','Party',150),
                       ('taxable','Taxable',90),('cgst','CGST',70),('sgst','SGST',70),
                       ('igst','IGST',70),('total','Total',90),('status','Status',70)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c in ('taxable','cgst','sgst','igst','total') else 'w')
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def load():
            tree.delete(*tree.get_children())
            for r in get_sales_register(df.get_date(), dt.get_date()):
                tree.insert('','end', values=(r['date'], r['voucher_no'], r['party_name'],
                    format_inr(r.get('taxable_amount',0)), format_inr(r.get('cgst',0)),
                    format_inr(r.get('sgst',0)), format_inr(r.get('igst',0)),
                    format_inr(r.get('grand_total',0)), r['status']))

        ctk.CTkButton(f, text="Load", fg_color=ACCENT, width=80, command=load).pack(side="left", padx=10)
        bf2 = ctk.CTkFrame(win, fg_color="transparent"); bf2.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(bf2, text="Export PDF", fg_color=BLUE, width=100,
                       command=lambda: self._msg(*export_sales_register_pdf(df.get_date(), dt.get_date()))).pack(side="left", padx=5)
        ctk.CTkButton(bf2, text="Export Excel", fg_color=PURPLE, width=100,
                       command=lambda: self._msg(*export_sales_register_excel(df.get_date(), dt.get_date()))).pack(side="left", padx=5)

    def _open_purchase_reg(self):
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Purchase Register"); win.geometry("900x500")
        _force_top(win)

        f = ctk.CTkFrame(win, fg_color="transparent"); f.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f, text="From:").pack(side="left")
        df = DatePickerEntry(f, width=130); df.pack(side="left", padx=5)
        ctk.CTkLabel(f, text="To:").pack(side="left")
        dt = DatePickerEntry(f, width=130); dt.pack(side="left", padx=5)

        cols = ('date','invoice','party','taxable','cgst','sgst','igst','total','status')
        tree = ttk.Treeview(win, columns=cols, show='headings', height=14)
        for c,t,w in [('date','Date',80),('invoice','Invoice',100),('party','Party',150),
                       ('taxable','Taxable',90),('cgst','CGST',70),('sgst','SGST',70),
                       ('igst','IGST',70),('total','Total',90),('status','Status',70)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c in ('taxable','cgst','sgst','igst','total') else 'w')
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def load():
            tree.delete(*tree.get_children())
            for r in get_purchase_register(df.get_date(), dt.get_date()):
                tree.insert('','end', values=(r['date'], r['voucher_no'], r['party_name'],
                    format_inr(r.get('taxable_amount',0)), format_inr(r.get('cgst',0)),
                    format_inr(r.get('sgst',0)), format_inr(r.get('igst',0)),
                    format_inr(r.get('grand_total',0)), r['status']))

        ctk.CTkButton(f, text="Load", fg_color=ACCENT, width=80, command=load).pack(side="left", padx=10)
        bf2 = ctk.CTkFrame(win, fg_color="transparent"); bf2.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(bf2, text="Export PDF", fg_color=BLUE, width=100,
                       command=lambda: self._msg(*export_purchase_register_pdf(df.get_date(), dt.get_date()))).pack(side="left", padx=5)

    def _open_party_os(self):
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Party Outstanding"); win.geometry("850x450")
        _force_top(win)

        cols = ('party','type','invoiced','paid','balance','oldest')
        tree = ttk.Treeview(win, columns=cols, show='headings', height=14)
        for c,t,w in [('party','Party',180),('type','Type',80),('invoiced','Invoiced',100),
                       ('paid','Paid',100),('balance','Balance',100),('oldest','Oldest',90)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c in ('invoiced','paid','balance') else 'w')
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        for r in get_party_outstanding():
            tree.insert('','end', values=(r['party_name'], r['type'],
                format_inr(r['total_invoiced']), format_inr(r['total_paid']),
                format_inr(r['balance']), r.get('oldest_invoice_date','')))
        bf = ctk.CTkFrame(win, fg_color="transparent"); bf.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(bf, text="Export PDF", fg_color=BLUE, width=100,
                       command=lambda: self._msg(*export_party_outstanding_pdf())).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Export Excel", fg_color=PURPLE, width=100,
                       command=lambda: self._msg(*export_party_outstanding_excel())).pack(side="left", padx=5)

    def _open_stock_val(self):
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Stock Valuation"); win.geometry("800x450")
        _force_top(win)

        cols = ('item','hsn','unit','godown','qty','rate','value')
        tree = ttk.Treeview(win, columns=cols, show='headings', height=14)
        for c,t,w in [('item','Item',160),('hsn','HSN',70),('unit','Unit',50),
                       ('godown','Godown',120),('qty','Qty',70),('rate','Avg Rate',80),('value','Value',100)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c in ('qty','rate','value') else 'w')
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        total = 0
        for r in get_stock_valuation_report():
            tree.insert('','end', values=(r['item_name'], r.get('hsn_code',''), r.get('unit',''),
                r['godown_name'], f"{r['qty']:.0f}", format_inr(r['avg_rate']),
                format_inr(r['stock_value'])))
            total += r['stock_value']
        ctk.CTkLabel(win, text=f"Grand Total: {format_inr(total)}",
                     font=ctk.CTkFont(size=15, weight="bold"), text_color=ACCENT).pack(padx=10, pady=5, anchor="e")

    def _open_item_profit(self):
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Item Profit Report"); win.geometry("900x450")
        _force_top(win)

        cols = ('item','hsn','pqty','pavg','sqty','savg','profit','margin')
        tree = ttk.Treeview(win, columns=cols, show='headings', height=14)
        for c,t,w in [('item','Item',150),('hsn','HSN',70),('pqty','Purchased',70),
                       ('pavg','Avg Buy',80),('sqty','Sold',70),('savg','Avg Sell',80),
                       ('profit','Gross Profit',90),('margin','Margin %',70)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c not in ('item','hsn') else 'w')
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        tree.tag_configure('low_margin', background='#FFE0B2')
        for r in get_item_profit_report():
            tag = ('low_margin',) if r['margin_pct'] < 10 else ()
            tree.insert('','end', values=(r['item_name'], r.get('hsn_code',''),
                f"{r['purchased_qty']:.0f}", format_inr(r['avg_purchase_rate']),
                f"{r['sold_qty']:.0f}", format_inr(r['avg_sale_rate']),
                format_inr(r['gross_profit']), f"{r['margin_pct']:.1f}%"), tags=tag)
        bf = ctk.CTkFrame(win, fg_color="transparent"); bf.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(bf, text="Export Excel", fg_color=PURPLE, width=100,
                       command=lambda: self._msg(*export_item_profit_excel())).pack(side="left", padx=5)

    def _msg(self, ok, result):
        if ok: CTkMessagebox(title="Success", message=f"Exported: {result}", icon="check")
        else: CTkMessagebox(title="Error", message=result, icon="cancel")

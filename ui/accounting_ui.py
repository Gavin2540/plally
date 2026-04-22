"""
Accounting UI for PlywoodPro — 4 tabs:
Tab 1: Ledger, Tab 2: Journal Voucher, Tab 3: Day Book, Tab 4: Financial Reports
"""
import customtkinter as ctk
from tkinter import ttk
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from CTkMessagebox import CTkMessagebox

from db.connection import get_connection
from modules.accounting import (
    get_ledger, get_trial_balance, get_profit_and_loss, get_balance_sheet,
    create_journal_voucher, get_day_book,
)
from utils.helpers import format_inr
from utils.pdf_export import (
    export_ledger_pdf, export_trial_balance_pdf, export_pl_pdf, export_bs_pdf,
)

ACCENT = "#2E7D32"
BLUE = "#1565C0"


def _all_accounts():
    conn = get_connection()
    rows = conn.execute("SELECT id, name, group_name FROM accounts WHERE is_active=1 ORDER BY group_name, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


class AccountingUI(ctk.CTkFrame):
    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.accounts = _all_accounts()
        self.jv_entries = []

        ctk.CTkLabel(self, text="Accounting", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=ACCENT).pack(padx=10, pady=(10,5), anchor="w")

        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)
        for t in ["Ledger", "Journal Voucher", "Day Book", "Financial Reports"]:
            self.tabview.add(t)

        self._build_ledger(self.tabview.tab("Ledger"))
        self._build_jv(self.tabview.tab("Journal Voucher"))
        self._build_daybook(self.tabview.tab("Day Book"))
        self._build_reports(self.tabview.tab("Financial Reports"))

    # ══════════════════════════════════════════════════════════
    #  TAB 1 — LEDGER
    # ══════════════════════════════════════════════════════════
    def _build_ledger(self, tab):
        f = ctk.CTkFrame(tab, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(f, text="Account:").pack(side="left")
        anames = [f"{a['name']} ({a['group_name']})" for a in self.accounts]
        self.led_acc = ctk.StringVar()
        ctk.CTkComboBox(f, variable=self.led_acc, values=anames, width=280).pack(side="left", padx=5)
        if anames: self.led_acc.set(anames[0])

        ctk.CTkLabel(f, text="From:").pack(side="left", padx=(15,0))
        self.led_from = ctk.StringVar()
        ctk.CTkEntry(f, textvariable=self.led_from, width=100, placeholder_text="YYYY-MM-DD").pack(side="left", padx=5)

        ctk.CTkLabel(f, text="To:").pack(side="left")
        self.led_to = ctk.StringVar()
        ctk.CTkEntry(f, textvariable=self.led_to, width=100, placeholder_text="YYYY-MM-DD").pack(side="left", padx=5)

        ctk.CTkButton(f, text="View", fg_color=ACCENT, width=80, command=self._view_ledger).pack(side="left", padx=5)
        ctk.CTkButton(f, text="Export PDF", fg_color=BLUE, width=100, command=self._export_ledger).pack(side="left", padx=5)

        cols = ('date','voucher','type','narration','debit','credit','balance')
        tc = ctk.CTkFrame(tab, fg_color="transparent")
        tc.pack(fill="both", expand=True, padx=10, pady=5)
        self.led_tree = ttk.Treeview(tc, columns=cols, show='headings', height=14)
        for c,t,w in [('date','Date',90),('voucher','Voucher',100),('type','Type',110),
                       ('narration','Narration',200),('debit','Debit',90),
                       ('credit','Credit',90),('balance','Balance',100)]:
            self.led_tree.heading(c, text=t)
            self.led_tree.column(c, width=w, anchor='e' if c in ('debit','credit','balance') else 'w')
        sb = ttk.Scrollbar(tc, orient="vertical", command=self.led_tree.yview)
        self.led_tree.configure(yscrollcommand=sb.set)
        self.led_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _get_selected_account(self):
        val = self.led_acc.get()
        for a in self.accounts:
            if f"{a['name']} ({a['group_name']})" == val: return a
        return None

    def _view_ledger(self):
        acc = self._get_selected_account()
        if not acc: return
        self.led_tree.delete(*self.led_tree.get_children())
        rows = get_ledger(acc['id'], self.led_from.get(), self.led_to.get())
        for r in rows:
            self.led_tree.insert('','end', values=(
                r['date'], r['voucher_no'], r['voucher_type'], r['narration'],
                format_inr(r['debit']) if r['debit'] else '',
                format_inr(r['credit']) if r['credit'] else '',
                format_inr(r['running_balance'])))

    def _export_ledger(self):
        acc = self._get_selected_account()
        if not acc: return
        ok, result = export_ledger_pdf(acc['id'], acc['name'], self.led_from.get(), self.led_to.get())
        if ok:
            CTkMessagebox(title="Success", message=f"PDF exported: {result}", icon="check")
        else:
            CTkMessagebox(title="Error", message=result, icon="cancel")

    # ══════════════════════════════════════════════════════════
    #  TAB 2 — JOURNAL VOUCHER
    # ══════════════════════════════════════════════════════════
    def _build_jv(self, tab):
        hdr = ctk.CTkFrame(tab, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(hdr, text="Date:").pack(side="left")
        self.jv_date = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkEntry(hdr, textvariable=self.jv_date, width=110).pack(side="left", padx=5)

        ctk.CTkLabel(hdr, text="Narration:").pack(side="left", padx=(15,0))
        self.jv_narr = ctk.StringVar()
        ctk.CTkEntry(hdr, textvariable=self.jv_narr, width=300).pack(side="left", padx=5)

        # Add row controls
        ar = ctk.CTkFrame(tab, fg_color="transparent")
        ar.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(ar, text="Account:").pack(side="left")
        anames = [f"{a['name']} ({a['group_name']})" for a in self.accounts]
        self.jv_acc = ctk.StringVar()
        ctk.CTkComboBox(ar, variable=self.jv_acc, values=anames, width=250).pack(side="left", padx=5)
        if anames: self.jv_acc.set(anames[0])

        ctk.CTkLabel(ar, text="Dr:").pack(side="left")
        self.jv_dr = ctk.StringVar(value="0")
        ctk.CTkEntry(ar, textvariable=self.jv_dr, width=90).pack(side="left", padx=5)

        ctk.CTkLabel(ar, text="Cr:").pack(side="left")
        self.jv_cr = ctk.StringVar(value="0")
        ctk.CTkEntry(ar, textvariable=self.jv_cr, width=90).pack(side="left", padx=5)

        ctk.CTkButton(ar, text="+ Add Row", fg_color=BLUE, width=90, command=self._jv_add).pack(side="left", padx=5)
        ctk.CTkButton(ar, text="Delete", fg_color="#C62828", width=80, command=self._jv_del).pack(side="left")

        # Tree
        tc = ctk.CTkFrame(tab, fg_color="transparent")
        tc.pack(fill="both", expand=True, padx=10, pady=5)
        cols = ('account','debit','credit')
        self.jv_tree = ttk.Treeview(tc, columns=cols, show='headings', height=6)
        for c,t,w in [('account','Account',300),('debit','Debit',120),('credit','Credit',120)]:
            self.jv_tree.heading(c, text=t)
            self.jv_tree.column(c, width=w, anchor='e' if c != 'account' else 'w')
        self.jv_tree.pack(side="left", fill="both", expand=True)

        # Totals + Save
        bf = ctk.CTkFrame(tab, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=5)

        self.jv_dr_total = ctk.StringVar(value="Dr: 0.00")
        self.jv_cr_total = ctk.StringVar(value="Cr: 0.00")
        self.jv_diff = ctk.StringVar(value="Diff: 0.00")

        ctk.CTkLabel(bf, textvariable=self.jv_dr_total, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(bf, textvariable=self.jv_cr_total, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(bf, textvariable=self.jv_diff, font=ctk.CTkFont(weight="bold"), text_color="#C62828").pack(side="left", padx=10)

        self.jv_save_btn = ctk.CTkButton(bf, text="Save Journal Voucher", fg_color=ACCENT, width=180, command=self._jv_save)
        self.jv_save_btn.pack(side="right", padx=10)

    def _jv_add(self):
        val = self.jv_acc.get()
        acc = None
        for a in self.accounts:
            if f"{a['name']} ({a['group_name']})" == val: acc = a; break
        if not acc: return
        try:
            dr = float(self.jv_dr.get() or 0)
            cr = float(self.jv_cr.get() or 0)
        except: return
        if dr == 0 and cr == 0: return
        self.jv_entries.append({'account_id': acc['id'], 'account_name': acc['name'], 'debit': dr, 'credit': cr})
        self._jv_refresh()

    def _jv_del(self):
        sel = self.jv_tree.selection()
        if sel:
            idx = self.jv_tree.index(sel[0])
            if 0 <= idx < len(self.jv_entries): self.jv_entries.pop(idx)
            self._jv_refresh()

    def _jv_refresh(self):
        self.jv_tree.delete(*self.jv_tree.get_children())
        tdr = tcr = 0
        for e in self.jv_entries:
            self.jv_tree.insert('','end', values=(
                e['account_name'],
                format_inr(e['debit']) if e['debit'] else '',
                format_inr(e['credit']) if e['credit'] else ''))
            tdr += e['debit']; tcr += e['credit']
        self.jv_dr_total.set(f"Dr: {format_inr(tdr)}")
        self.jv_cr_total.set(f"Cr: {format_inr(tcr)}")
        diff = abs(tdr - tcr)
        self.jv_diff.set(f"Diff: {format_inr(diff)}" if diff > 0.01 else "BALANCED")

    def _jv_save(self):
        if not self.jv_entries:
            CTkMessagebox(title="Error", message="Add entries first.", icon="cancel"); return
        tdr = sum(e['debit'] for e in self.jv_entries)
        tcr = sum(e['credit'] for e in self.jv_entries)
        if abs(tdr - tcr) > 0.01:
            CTkMessagebox(title="Error", message=f"Debits ({tdr}) != Credits ({tcr})", icon="cancel"); return
        ok, msg, vid = create_journal_voucher(self.jv_date.get(), self.jv_narr.get(), self.jv_entries)
        if ok:
            CTkMessagebox(title="Success", message=msg, icon="check")
            self.jv_entries.clear(); self._jv_refresh()
        else:
            CTkMessagebox(title="Error", message=msg, icon="cancel")

    # ══════════════════════════════════════════════════════════
    #  TAB 3 — DAY BOOK
    # ══════════════════════════════════════════════════════════
    def _build_daybook(self, tab):
        f = ctk.CTkFrame(tab, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f, text="Date:").pack(side="left")
        self.db_date = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkEntry(f, textvariable=self.db_date, width=110).pack(side="left", padx=5)
        ctk.CTkButton(f, text="View", fg_color=ACCENT, width=80, command=self._view_daybook).pack(side="left", padx=5)

        cols = ('voucher','type','party','amount','status','narration')
        tc = ctk.CTkFrame(tab, fg_color="transparent")
        tc.pack(fill="both", expand=True, padx=10, pady=5)
        self.db_tree = ttk.Treeview(tc, columns=cols, show='headings', height=14)
        for c,t,w in [('voucher','Voucher',110),('type','Type',120),('party','Party',150),
                       ('amount','Amount',100),('status','Status',80),('narration','Narration',220)]:
            self.db_tree.heading(c, text=t)
            self.db_tree.column(c, width=w, anchor='e' if c=='amount' else 'w')
        self.db_tree.pack(side="left", fill="both", expand=True)

    def _view_daybook(self):
        self.db_tree.delete(*self.db_tree.get_children())
        rows = get_day_book(self.db_date.get())
        for r in rows:
            self.db_tree.insert('','end', values=(
                r['voucher_no'], r['voucher_type'], r.get('party_name',''),
                format_inr(r.get('grand_total',0) or 0), r['status'], r.get('narration','')))

    # ══════════════════════════════════════════════════════════
    #  TAB 4 — FINANCIAL REPORTS
    # ══════════════════════════════════════════════════════════
    def _build_reports(self, tab):
        bf = ctk.CTkFrame(tab, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=10)

        for text, color, cmd in [
            ("Trial Balance", ACCENT, self._show_trial_balance),
            ("Profit & Loss", BLUE, self._show_pl),
            ("Balance Sheet", "#7B1FA2", self._show_bs),
        ]:
            ctk.CTkButton(bf, text=text, fg_color=color, width=160, height=40,
                           font=ctk.CTkFont(size=14, weight="bold"), command=cmd).pack(side="left", padx=10)

        self.report_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.report_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def _clear_report(self):
        for w in self.report_frame.winfo_children(): w.destroy()

    def _show_trial_balance(self):
        self._clear_report()
        data = get_trial_balance()
        ctk.CTkLabel(self.report_frame, text=f"Trial Balance  |  Balanced: {'YES' if data['balanced'] else 'NO'}",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=ACCENT if data['balanced'] else "#C62828").pack(anchor="w", pady=5)

        cols = ('group','account','debit','credit','closing_dr','closing_cr')
        tree = ttk.Treeview(self.report_frame, columns=cols, show='headings', height=14)
        for c,t,w in [('group','Group',120),('account','Account',180),('debit','Total Dr',100),
                       ('credit','Total Cr',100),('closing_dr','Closing Dr',100),('closing_cr','Closing Cr',100)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c!='account' and c!='group' else 'w')
        tree.pack(fill="both", expand=True, pady=5)

        for r in data['rows']:
            tree.insert('','end', values=(r['group_name'], r['account_name'],
                format_inr(r['total_debit']), format_inr(r['total_credit']),
                format_inr(r['closing_dr']) if r['closing_dr'] else '',
                format_inr(r['closing_cr']) if r['closing_cr'] else ''))

        ctk.CTkLabel(self.report_frame,
            text=f"Totals — Dr: {format_inr(data['total_debit'])}  |  Cr: {format_inr(data['total_credit'])}",
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="e", pady=5)

        ctk.CTkButton(self.report_frame, text="Export PDF", fg_color=BLUE, width=120,
                       command=lambda: self._export_report('tb')).pack(anchor="e")

    def _show_pl(self):
        self._clear_report()
        data = get_profit_and_loss()
        color = ACCENT if data['net_profit'] >= 0 else "#C62828"
        ctk.CTkLabel(self.report_frame, text=f"Profit & Loss  |  Net: {format_inr(data['net_profit'])}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack(anchor="w", pady=5)

        cols = ('type','name','group','amount')
        tree = ttk.Treeview(self.report_frame, columns=cols, show='headings', height=14)
        for c,t,w in [('type','Type',80),('name','Account',200),('group','Group',140),('amount','Amount',120)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c=='amount' else 'w')
        tree.pack(fill="both", expand=True, pady=5)

        for r in data['income']:
            tree.insert('','end', values=('Income', r['name'], r['group'], format_inr(r['amount'])))
        for r in data['expenses']:
            tree.insert('','end', values=('Expense', r['name'], r['group'], format_inr(r['amount'])))

        ctk.CTkButton(self.report_frame, text="Export PDF", fg_color=BLUE, width=120,
                       command=lambda: self._export_report('pl')).pack(anchor="e", pady=5)

    def _show_bs(self):
        self._clear_report()
        data = get_balance_sheet()
        bal = "BALANCED" if data['balanced'] else "NOT BALANCED"
        color = ACCENT if data['balanced'] else "#C62828"
        ctk.CTkLabel(self.report_frame, text=f"Balance Sheet  |  {bal}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack(anchor="w", pady=5)

        cols = ('side','name','group','amount')
        tree = ttk.Treeview(self.report_frame, columns=cols, show='headings', height=14)
        for c,t,w in [('side','Side',80),('name','Account',200),('group','Group',140),('amount','Amount',120)]:
            tree.heading(c, text=t); tree.column(c, width=w, anchor='e' if c=='amount' else 'w')
        tree.pack(fill="both", expand=True, pady=5)

        for r in data['assets']:
            tree.insert('','end', values=('Asset', r['name'], r['group'], format_inr(r['amount'])))
        for r in data['liabilities']:
            tree.insert('','end', values=('Liability', r['name'], r['group'], format_inr(r['amount'])))

        ctk.CTkLabel(self.report_frame,
            text=f"Assets: {format_inr(data['total_assets'])}  |  Liabilities: {format_inr(data['total_liabilities'])}",
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="e", pady=5)

        ctk.CTkButton(self.report_frame, text="Export PDF", fg_color=BLUE, width=120,
                       command=lambda: self._export_report('bs')).pack(anchor="e")

    def _export_report(self, report_type):
        if report_type == 'tb':
            ok, r = export_trial_balance_pdf()
        elif report_type == 'pl':
            ok, r = export_pl_pdf()
        else:
            ok, r = export_bs_pdf()
        if ok:
            CTkMessagebox(title="Success", message=f"PDF: {r}", icon="check")
        else:
            CTkMessagebox(title="Error", message=r, icon="cancel")

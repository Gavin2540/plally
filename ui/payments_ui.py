"""
Payments UI for PlywoodPro.
Tabbed interface: Receipts (money IN) | Payments (money OUT).
Each tab shows a list view and provides a form for creating new entries.
"""

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from tkinter import ttk, StringVar

from modules.sales import (
    create_receipt, get_receipts, get_outstanding_invoices,
)
from modules.purchase import (
    create_payment, get_payments, get_outstanding_purchase_invoices,
)
from modules.masters import get_all_parties
from utils.helpers import format_inr, format_date_display, today_db
from utils.date_picker import DatePickerEntry


PAYMENT_MODES = ['Cash', 'UPI', 'NEFT', 'RTGS', 'Cheque', 'Card']


class PaymentsUI(ctk.CTkFrame):
    """Receipts & Payments management screen."""

    def __init__(self, parent, app=None, tab='receipts'):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.initial_tab = tab
        self._build_ui()

    def _build_ui(self):
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 5))
        ctk.CTkLabel(title_frame, text="💰  Receipts & Payments",
                      font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        self.tabs = ctk.CTkTabview(self, corner_radius=8)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_rcp = self.tabs.add("Receipts")
        self.tab_pmt = self.tabs.add("Payments")

        self._build_receipt_tab()
        self._build_payment_tab()

        if self.initial_tab == 'payments':
            self.tabs.set("Payments")

    # ══════════════════════════════════════════════════════════════
    #  RECEIPTS TAB
    # ══════════════════════════════════════════════════════════════

    def _build_receipt_tab(self):
        top = ctk.CTkFrame(self.tab_rcp, fg_color="transparent")
        top.pack(fill="x", pady=5)

        ctk.CTkButton(top, text="➕ New Receipt", fg_color="#2E7D32",
                       hover_color="#1B5E20",
                       command=self._show_receipt_form).pack(side="left", padx=5)
        ctk.CTkButton(top, text="🔄 Refresh", fg_color="#555",
                       command=self._load_receipts).pack(side="right", padx=5)

        tree_frame = ctk.CTkFrame(self.tab_rcp)
        tree_frame.pack(fill="both", expand=True, pady=5)

        cols = ("id", "receipt_no", "date", "party", "amount", "mode", "reference")
        self.rcp_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        for c, h, w in zip(cols,
                            ("ID", "Receipt No", "Date", "Customer", "Amount", "Mode", "Reference"),
                            (40, 120, 90, 180, 110, 80, 120)):
            self.rcp_tree.heading(c, text=h)
            self.rcp_tree.column(c, width=w, anchor="center" if c != "party" else "w")
        self.rcp_tree.column("id", width=0, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.rcp_tree.yview)
        self.rcp_tree.configure(yscrollcommand=scrollbar.set)
        self.rcp_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._load_receipts()

    def _load_receipts(self):
        for row in self.rcp_tree.get_children():
            self.rcp_tree.delete(row)
        rcps = get_receipts()
        for i, r in enumerate(rcps):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.rcp_tree.insert("", "end", values=(
                r['id'], r['voucher_no'], format_date_display(r['date']),
                r.get('party_name', ''), format_inr(r.get('amount', 0)),
                r.get('mode', ''), r.get('reference_no', ''),
            ), tags=(tag,))
        self.rcp_tree.tag_configure('even', background='#1a1a2e')
        self.rcp_tree.tag_configure('odd', background='#16213e')

    def _show_receipt_form(self):
        _ReceiptPaymentPopup(self, ptype='Receipt', save_fn=self._save_receipt)

    def _save_receipt(self, party_id, invoice_id, amount, mode, ref, date_str, narration):
        ok, msg, _ = create_receipt(party_id, invoice_id, amount, mode, ref, date_str, narration)
        CTkMessagebox(title="Result", message=msg, icon="check" if ok else "cancel")
        self._load_receipts()

    # ══════════════════════════════════════════════════════════════
    #  PAYMENTS TAB
    # ══════════════════════════════════════════════════════════════

    def _build_payment_tab(self):
        top = ctk.CTkFrame(self.tab_pmt, fg_color="transparent")
        top.pack(fill="x", pady=5)

        ctk.CTkButton(top, text="➕ New Payment", fg_color="#1565C0",
                       hover_color="#0D47A1",
                       command=self._show_payment_form).pack(side="left", padx=5)
        ctk.CTkButton(top, text="🔄 Refresh", fg_color="#555",
                       command=self._load_payments).pack(side="right", padx=5)

        tree_frame = ctk.CTkFrame(self.tab_pmt)
        tree_frame.pack(fill="both", expand=True, pady=5)

        cols = ("id", "payment_no", "date", "party", "amount", "mode", "reference")
        self.pmt_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        for c, h, w in zip(cols,
                            ("ID", "Payment No", "Date", "Supplier", "Amount", "Mode", "Reference"),
                            (40, 120, 90, 180, 110, 80, 120)):
            self.pmt_tree.heading(c, text=h)
            self.pmt_tree.column(c, width=w, anchor="center" if c != "party" else "w")
        self.pmt_tree.column("id", width=0, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.pmt_tree.yview)
        self.pmt_tree.configure(yscrollcommand=scrollbar.set)
        self.pmt_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._load_payments()

    def _load_payments(self):
        for row in self.pmt_tree.get_children():
            self.pmt_tree.delete(row)
        pmts = get_payments()
        for i, p in enumerate(pmts):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.pmt_tree.insert("", "end", values=(
                p['id'], p['voucher_no'], format_date_display(p['date']),
                p.get('party_name', ''), format_inr(p.get('amount', 0)),
                p.get('mode', ''), p.get('reference_no', ''),
            ), tags=(tag,))
        self.pmt_tree.tag_configure('even', background='#1a1a2e')
        self.pmt_tree.tag_configure('odd', background='#16213e')

    def _show_payment_form(self):
        _ReceiptPaymentPopup(self, ptype='Payment', save_fn=self._save_payment)

    def _save_payment(self, party_id, invoice_id, amount, mode, ref, date_str, narration):
        ok, msg, _ = create_payment(party_id, invoice_id, amount, mode, ref, date_str, narration)
        CTkMessagebox(title="Result", message=msg, icon="check" if ok else "cancel")
        self._load_payments()


# ══════════════════════════════════════════════════════════════════════
#  RECEIPT / PAYMENT FORM POPUP
# ══════════════════════════════════════════════════════════════════════

class _ReceiptPaymentPopup(ctk.CTkToplevel):
    """Popup form for creating a Receipt or Payment."""

    def __init__(self, parent, ptype: str, save_fn):
        super().__init__(parent)
        self.title(f"New {ptype}")
        self.geometry("650x480")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()

        self.ptype = ptype
        self.save_fn = save_fn
        self.invoice_map = {}

        is_receipt = ptype == 'Receipt'
        parties = get_all_parties(party_type='customer') if is_receipt else get_all_parties(party_type='supplier')
        self.party_map = {p['name']: p['id'] for p in parties}

        self._build_form()

    def _build_form(self):
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=15)
        form.columnconfigure(1, weight=1)

        row = 0

        # Party
        ctk.CTkLabel(form, text="Party *").grid(row=row, column=0, sticky="w", pady=8, padx=5)
        self.cmb_party = ctk.CTkComboBox(
            form, values=list(self.party_map.keys()), width=300,
            command=self._on_party_change,
        )
        self.cmb_party.set('')
        self.cmb_party.grid(row=row, column=1, sticky="ew", pady=8, padx=5)
        row += 1

        # Invoice
        ctk.CTkLabel(form, text="Against Invoice *").grid(row=row, column=0, sticky="w", pady=8, padx=5)
        self.cmb_invoice = ctk.CTkComboBox(form, values=[], width=300,
                                             command=self._on_invoice_change)
        self.cmb_invoice.set('')
        self.cmb_invoice.grid(row=row, column=1, sticky="ew", pady=8, padx=5)
        row += 1

        # Balance label
        self.lbl_balance = ctk.CTkLabel(form, text="Balance Due: —",
                                         font=ctk.CTkFont(size=12), text_color="#FF9800")
        self.lbl_balance.grid(row=row, column=0, columnspan=2, sticky="w", padx=5)
        row += 1

        # Amount
        ctk.CTkLabel(form, text="Amount *").grid(row=row, column=0, sticky="w", pady=8, padx=5)
        self.entry_amount = ctk.CTkEntry(form, width=200, placeholder_text="0.00")
        self.entry_amount.grid(row=row, column=1, sticky="w", pady=8, padx=5)
        row += 1

        # Mode
        ctk.CTkLabel(form, text="Mode *").grid(row=row, column=0, sticky="w", pady=8, padx=5)
        self.cmb_mode = ctk.CTkComboBox(form, values=PAYMENT_MODES, width=200)
        self.cmb_mode.set('Cash')
        self.cmb_mode.grid(row=row, column=1, sticky="w", pady=8, padx=5)
        row += 1

        # Reference
        ctk.CTkLabel(form, text="Reference No").grid(row=row, column=0, sticky="w", pady=8, padx=5)
        self.entry_ref = ctk.CTkEntry(form, width=200, placeholder_text="UTR / Cheque No")
        self.entry_ref.grid(row=row, column=1, sticky="w", pady=8, padx=5)
        row += 1

        # Date
        ctk.CTkLabel(form, text="Date *").grid(row=row, column=0, sticky="w", pady=8, padx=5)
        self.dp_date = DatePickerEntry(form, width=130)
        self.dp_date.grid(row=row, column=1, sticky="w", pady=8, padx=5)
        row += 1

        # Narration
        ctk.CTkLabel(form, text="Narration").grid(row=row, column=0, sticky="w", pady=8, padx=5)
        self.entry_narration = ctk.CTkEntry(form, width=300, placeholder_text="Optional note")
        self.entry_narration.grid(row=row, column=1, sticky="ew", pady=8, padx=5)
        row += 1

        # Save
        ctk.CTkButton(form, text=f"💾  Save {self.ptype}", width=200, height=40,
                       fg_color="#2E7D32", hover_color="#1B5E20",
                       font=ctk.CTkFont(size=14, weight="bold"),
                       command=self._save).grid(row=row, column=0, columnspan=2, pady=20)

    def _on_party_change(self, party_name: str):
        """Load outstanding invoices for selected party."""
        party_id = self.party_map.get(party_name, 0)
        if not party_id:
            return

        if self.ptype == 'Receipt':
            invoices = get_outstanding_invoices(party_id, 'Sales Invoice')
        else:
            invoices = get_outstanding_purchase_invoices(party_id)

        self.invoice_map = {}
        inv_labels = []
        for inv in invoices:
            label = f"{inv['voucher_no']} | {format_date_display(inv['date'])} | Due: {format_inr(inv['balance_due'])}"
            inv_labels.append(label)
            self.invoice_map[label] = inv

        self.cmb_invoice.configure(values=inv_labels)
        if inv_labels:
            self.cmb_invoice.set(inv_labels[0])
            self._on_invoice_change(inv_labels[0])
        else:
            self.cmb_invoice.set('')
            self.lbl_balance.configure(text="No outstanding invoices.")

    def _on_invoice_change(self, label: str):
        inv = self.invoice_map.get(label)
        if inv:
            self.lbl_balance.configure(
                text=f"Balance Due: {format_inr(inv['balance_due'])}  (Total: {format_inr(inv['grand_total'])})"
            )
            self.entry_amount.delete(0, "end")
            self.entry_amount.insert(0, f"{inv['balance_due']:.2f}")

    def _save(self):
        party_name = self.cmb_party.get().strip()
        if party_name not in self.party_map:
            CTkMessagebox(title="Error", message="Select a valid party.", icon="cancel")
            return

        inv_label = self.cmb_invoice.get().strip()
        inv = self.invoice_map.get(inv_label)
        if not inv:
            CTkMessagebox(title="Error", message="Select a valid invoice.", icon="cancel")
            return

        try:
            amount = float(self.entry_amount.get().strip())
        except (ValueError, TypeError):
            CTkMessagebox(title="Error", message="Enter a valid amount.", icon="cancel")
            return

        if amount <= 0:
            CTkMessagebox(title="Error", message="Amount must be > 0.", icon="cancel")
            return

        self.save_fn(
            party_id=self.party_map[party_name],
            invoice_id=inv['id'],
            amount=amount,
            mode=self.cmb_mode.get(),
            ref=self.entry_ref.get().strip(),
            date_str=self.dp_date.get_date(),
            narration=self.entry_narration.get().strip(),
        )
        self.destroy()

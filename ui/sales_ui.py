"""
Sales Invoice UI for PlywoodPro.
Tally-style invoice form with line item table, live GST calculation,
amount in words, and Save Draft / Confirm & Print / Cancel buttons.
"""

import customtkinter as ctk
from tkinter import ttk
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import traceback

from CTkMessagebox import CTkMessagebox

from db.connection import get_connection
from modules.masters import get_all_parties, get_all_items, get_all_godowns, get_company
from modules.sales import (
    create_sales_invoice, confirm_sales_invoice, get_sales_invoices
)
from utils.helpers import format_inr, amount_in_words
from utils.gst_engine import calculate_tax_split, is_intra_state
from utils.pdf_export import export_invoice_pdf


ACCENT = "#2E7D32"
ACCENT_HOVER = "#1B5E20"


def _d(val) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


class SalesInvoiceUI(ctk.CTkFrame):
    """Sales Invoice form screen."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.party_list = []
        self.item_list = []
        self.godown_list = []
        self.company = get_company()
        self.line_items = []  # List of dicts for the treeview
        self._build_ui()
        self._load_dropdowns()

    # ──────────────────────────────────────────────────────────
    #  BUILD UI
    # ──────────────────────────────────────────────────────────

    def _build_ui(self):
        """Build the complete invoice form."""
        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(
            title_frame, text="Sales Invoice",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT,
        ).pack(side="left")

        # ── Header Section ─────────────────────────────────────
        header = ctk.CTkFrame(self, corner_radius=10)
        header.pack(fill="x", padx=10, pady=5)

        # Row 1: Party, Invoice No, Date
        r1 = ctk.CTkFrame(header, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(r1, text="Party:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.party_var = ctk.StringVar()
        self.party_combo = ctk.CTkComboBox(
            r1, variable=self.party_var, width=300,
            command=self._on_party_changed,
        )
        self.party_combo.pack(side="left", padx=(5, 20))

        ctk.CTkLabel(r1, text="Date:").pack(side="left")
        self.date_var = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkEntry(r1, textvariable=self.date_var, width=120).pack(side="left", padx=(5, 20))

        ctk.CTkLabel(r1, text="Due Date:").pack(side="left")
        self.due_date_var = ctk.StringVar()
        ctk.CTkEntry(r1, textvariable=self.due_date_var, width=120).pack(side="left", padx=5)

        # Row 2: Godown, Reference
        r2 = ctk.CTkFrame(header, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(r2, text="Godown:").pack(side="left")
        self.godown_var = ctk.StringVar()
        self.godown_combo = ctk.CTkComboBox(
            r2, variable=self.godown_var, width=200,
        )
        self.godown_combo.pack(side="left", padx=(5, 20))

        ctk.CTkLabel(r2, text="Reference No:").pack(side="left")
        self.ref_var = ctk.StringVar()
        ctk.CTkEntry(r2, textvariable=self.ref_var, width=150).pack(side="left", padx=(5, 20))

        # Transport
        ctk.CTkLabel(r2, text="Transport:").pack(side="left")
        self.transport_var = ctk.StringVar()
        ctk.CTkEntry(r2, textvariable=self.transport_var, width=150).pack(side="left", padx=(5, 20))

        ctk.CTkLabel(r2, text="Vehicle:").pack(side="left")
        self.vehicle_var = ctk.StringVar()
        ctk.CTkEntry(r2, textvariable=self.vehicle_var, width=120).pack(side="left", padx=5)

        # ── Tax type indicator ─────────────────────────────────
        self.tax_label = ctk.CTkLabel(
            header, text="Tax: CGST + SGST (Intra-state)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#FF9800"
        )
        self.tax_label.pack(padx=10, pady=5, anchor="w")

        # ── Line Items Table ───────────────────────────────────
        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Add Row controls
        add_row_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        add_row_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(add_row_frame, text="Item:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.item_var = ctk.StringVar()
        self.item_combo = ctk.CTkComboBox(
            add_row_frame, variable=self.item_var, width=250,
        )
        self.item_combo.pack(side="left", padx=5)

        ctk.CTkLabel(add_row_frame, text="Qty:").pack(side="left")
        self.qty_var = ctk.StringVar(value="1")
        ctk.CTkEntry(add_row_frame, textvariable=self.qty_var, width=70).pack(side="left", padx=5)

        ctk.CTkLabel(add_row_frame, text="Rate:").pack(side="left")
        self.rate_var = ctk.StringVar(value="0")
        ctk.CTkEntry(add_row_frame, textvariable=self.rate_var, width=90).pack(side="left", padx=5)

        ctk.CTkLabel(add_row_frame, text="Disc%:").pack(side="left")
        self.disc_var = ctk.StringVar(value="0")
        ctk.CTkEntry(add_row_frame, textvariable=self.disc_var, width=60).pack(side="left", padx=5)

        ctk.CTkButton(
            add_row_frame, text="+ Add Row", fg_color=ACCENT,
            hover_color=ACCENT_HOVER, width=100, command=self._add_row,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            add_row_frame, text="Delete Row", fg_color="#C62828",
            hover_color="#B71C1C", width=100, command=self._delete_row,
        ).pack(side="left")

        # Treeview
        tree_container = ctk.CTkFrame(table_frame, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ('item', 'hsn', 'qty', 'unit', 'rate', 'disc', 'taxable',
                    'gst', 'cgst', 'sgst', 'igst', 'total')
        self.tree = ttk.Treeview(
            tree_container, columns=columns, show='headings', height=8,
        )

        headings = {
            'item': ('Item', 150), 'hsn': ('HSN', 60), 'qty': ('Qty', 60),
            'unit': ('Unit', 60), 'rate': ('Rate', 80), 'disc': ('Disc%', 50),
            'taxable': ('Taxable', 90), 'gst': ('GST%', 50),
            'cgst': ('CGST', 80), 'sgst': ('SGST', 80),
            'igst': ('IGST', 80), 'total': ('Total', 100),
        }
        for col, (text, width) in headings.items():
            self.tree.heading(col, text=text)
            anchor = 'e' if col not in ('item', 'unit') else 'w'
            self.tree.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Totals Section ─────────────────────────────────────
        totals_frame = ctk.CTkFrame(self, corner_radius=10)
        totals_frame.pack(fill="x", padx=10, pady=5)

        totals_inner = ctk.CTkFrame(totals_frame, fg_color="transparent")
        totals_inner.pack(side="right", padx=20, pady=10)

        # ── Totals labels (direct text, NOT textvariable) ──────
        labels_config = [
            ("Subtotal:", "lbl_subtotal", 12, None),
            ("Discount:", "lbl_discount", 12, None),
            ("Taxable Amount:", "lbl_taxable", 12, None),
            ("CGST:", "lbl_cgst", 12, None),
            ("SGST:", "lbl_sgst", 12, None),
            ("IGST:", "lbl_igst", 12, None),
            ("Grand Total:", "lbl_grand_total", 14, ACCENT),
        ]
        for i, (text, attr_name, fsize, color) in enumerate(labels_config):
            ctk.CTkLabel(totals_inner, text=text, font=ctk.CTkFont(weight="bold")).grid(
                row=i, column=0, sticky="e", padx=(0, 10), pady=2
            )
            weight = "bold" if text == "Grand Total:" else "normal"
            lbl = ctk.CTkLabel(
                totals_inner, text="₹ 0.00",
                font=ctk.CTkFont(size=fsize, weight=weight),
                text_color=color,
            )
            lbl.grid(row=i, column=1, sticky="e", pady=2)
            setattr(self, attr_name, lbl)

        # Narration + Amount in words
        narr_frame = ctk.CTkFrame(totals_frame, fg_color="transparent")
        narr_frame.pack(side="left", padx=20, pady=10, fill="x", expand=True)

        ctk.CTkLabel(narr_frame, text="Narration:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.narration_var = ctk.StringVar()
        ctk.CTkEntry(narr_frame, textvariable=self.narration_var, width=350).pack(anchor="w", pady=2)

        ctk.CTkLabel(narr_frame, text="Amount in Words:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        self.lbl_amount_words = ctk.CTkLabel(
            narr_frame, text="Rupees Zero Only",
            font=ctk.CTkFont(size=11), text_color=ACCENT, wraplength=350,
        )
        self.lbl_amount_words.pack(anchor="w")

        # ── Action Buttons ─────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkButton(
            btn_frame, text="💾 Save Draft", fg_color="#1565C0",
            hover_color="#0D47A1", width=140, command=self._save_draft,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="✅ Confirm & Print", fg_color=ACCENT,
            hover_color=ACCENT_HOVER, width=160, command=self._confirm_and_print,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="🔄 Clear Form", fg_color="#757575",
            hover_color="#616161", width=120, command=self.clear_form,
        ).pack(side="left", padx=5)

    # ──────────────────────────────────────────────────────────
    #  DATA LOADING
    # ──────────────────────────────────────────────────────────

    def _load_dropdowns(self):
        """Load parties, items, godowns into dropdowns."""
        # Parties (customers and both)
        self.party_list = get_all_parties(party_type='customer')
        party_names = [p['name'] for p in self.party_list]
        self.party_combo.configure(values=party_names)
        if party_names:
            self.party_combo.set(party_names[0])
            self._on_party_changed(party_names[0])

        # Items
        self.item_list = get_all_items()
        item_names = [f"{i['name']} [{i['hsn_code']}]" for i in self.item_list]
        self.item_combo.configure(values=item_names)
        if item_names:
            self.item_combo.set(item_names[0])
            # Pre-fill rate from item's sale_rate
            self.rate_var.set(str(self.item_list[0].get('sale_rate', 0)))

        # Godowns
        self.godown_list = get_all_godowns()
        godown_names = [g['name'] for g in self.godown_list]
        self.godown_combo.configure(values=godown_names)
        if godown_names:
            self.godown_combo.set(godown_names[0])

    def _get_selected_party(self) -> dict | None:
        name = self.party_var.get()
        for p in self.party_list:
            if p['name'] == name:
                return p
        return None

    def _get_selected_item(self) -> dict | None:
        val = self.item_var.get()
        for i in self.item_list:
            display = f"{i['name']} [{i['hsn_code']}]"
            if display == val:
                return i
        return None

    def _get_selected_godown_id(self) -> int:
        name = self.godown_var.get()
        for g in self.godown_list:
            if g['name'] == name:
                return g['id']
        return 1

    # ──────────────────────────────────────────────────────────
    #  GST DETECTION
    # ──────────────────────────────────────────────────────────

    def _on_party_changed(self, *args):
        """When party changes, detect intra/inter-state and update label."""
        party = self._get_selected_party()
        if not party or not self.company:
            return

        company_code = self.company.get('state_code', '')
        party_code = party.get('state_code', '')

        if is_intra_state(company_code, party_code):
            self.tax_label.configure(
                text="Tax: CGST + SGST (Intra-state)",
                text_color="#FF9800"
            )
        else:
            self.tax_label.configure(
                text="Tax: IGST (Inter-state)",
                text_color="#E91E63"
            )
        # Recalculate existing rows
        self._recalculate_all_rows()

    # ──────────────────────────────────────────────────────────
    #  LINE ITEM OPERATIONS
    # ──────────────────────────────────────────────────────────

    def _add_row(self):
        """Add a line item to the table."""
        item = self._get_selected_item()
        if not item:
            CTkMessagebox(title="Error", message="Please select an item.", icon="cancel")
            return

        try:
            qty = Decimal(self.qty_var.get())
            rate = Decimal(self.rate_var.get())
            disc_pct = Decimal(self.disc_var.get())
        except Exception:
            CTkMessagebox(title="Error", message="Invalid qty, rate, or discount.", icon="cancel")
            return

        if qty <= 0:
            CTkMessagebox(title="Error", message="Quantity must be > 0.", icon="cancel")
            return

        # Calculate
        gross = qty * rate
        disc_amt = gross * disc_pct / Decimal("100")
        taxable = gross - disc_amt
        gst_rate = _d(item.get('gst_rate', 18))

        party = self._get_selected_party()
        company_code = self.company.get('state_code', '') if self.company else ''
        party_code = party.get('state_code', '') if party else ''

        tax_split = calculate_tax_split(float(gst_rate), company_code, party_code)
        cgst_rate = _d(tax_split.get('cgst_rate', 0))
        sgst_rate = _d(tax_split.get('sgst_rate', 0))
        igst_rate = _d(tax_split.get('igst_rate', 0))

        cgst_amt = taxable * cgst_rate / Decimal("100")
        sgst_amt = taxable * sgst_rate / Decimal("100")
        igst_amt = taxable * igst_rate / Decimal("100")
        total = taxable + cgst_amt + sgst_amt + igst_amt

        # Round all
        r = lambda v: float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        row_data = {
            'item_id': item['id'],
            'description': item['name'],
            'hsn_code': item.get('hsn_code', ''),
            'qty': float(qty),
            'unit': item.get('unit', ''),
            'rate': float(rate),
            'discount_pct': float(disc_pct),
            'discount_amount': r(disc_amt),
            'taxable_amount': r(taxable),
            'gst_rate': float(gst_rate),
            'cgst_rate': float(cgst_rate),
            'cgst_amount': r(cgst_amt),
            'sgst_rate': float(sgst_rate),
            'sgst_amount': r(sgst_amt),
            'igst_rate': float(igst_rate),
            'igst_amount': r(igst_amt),
            'total_amount': r(total),
        }

        self.line_items.append(row_data)
        self._refresh_tree()
        self._recalc_totals()

        # Pre-fill next item rate
        self.qty_var.set("1")
        self.disc_var.set("0")

    def _delete_row(self):
        """Delete selected row from the table."""
        selected = self.tree.selection()
        if not selected:
            CTkMessagebox(title="Info", message="Select a row to delete.", icon="info")
            return
        idx = self.tree.index(selected[0])
        if 0 <= idx < len(self.line_items):
            self.line_items.pop(idx)
        self._refresh_tree()
        self._recalc_totals()

    def _refresh_tree(self):
        """Refresh the treeview from self.line_items."""
        self.tree.delete(*self.tree.get_children())
        for row in self.line_items:
            self.tree.insert('', 'end', values=(
                row['description'],
                row['hsn_code'],
                f"{row['qty']:.2f}",
                row['unit'],
                f"{row['rate']:.2f}",
                f"{row['discount_pct']:.1f}",
                format_inr(row['taxable_amount']),
                f"{row['gst_rate']:.0f}%",
                format_inr(row['cgst_amount']),
                format_inr(row['sgst_amount']),
                format_inr(row['igst_amount']),
                format_inr(row['total_amount']),
            ))

    def _recalculate_all_rows(self):
        """Recalculate all line items when party changes (tax type may change)."""
        party = self._get_selected_party()
        company_code = self.company.get('state_code', '') if self.company else ''
        party_code = party.get('state_code', '') if party else ''

        for row in self.line_items:
            qty = _d(row['qty'])
            rate = _d(row['rate'])
            disc_pct = _d(row['discount_pct'])
            gst_rate = _d(row['gst_rate'])

            gross = qty * rate
            disc_amt = gross * disc_pct / Decimal("100")
            taxable = gross - disc_amt

            tax_split = calculate_tax_split(float(gst_rate), company_code, party_code)
            cgst_rate = _d(tax_split.get('cgst_rate', 0))
            sgst_rate = _d(tax_split.get('sgst_rate', 0))
            igst_rate = _d(tax_split.get('igst_rate', 0))

            cgst_amt = taxable * cgst_rate / Decimal("100")
            sgst_amt = taxable * sgst_rate / Decimal("100")
            igst_amt = taxable * igst_rate / Decimal("100")
            total = taxable + cgst_amt + sgst_amt + igst_amt

            r = lambda v: float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

            row['discount_amount'] = r(disc_amt)
            row['taxable_amount'] = r(taxable)
            row['cgst_rate'] = float(cgst_rate)
            row['cgst_amount'] = r(cgst_amt)
            row['sgst_rate'] = float(sgst_rate)
            row['sgst_amount'] = r(sgst_amt)
            row['igst_rate'] = float(igst_rate)
            row['igst_amount'] = r(igst_amt)
            row['total_amount'] = r(total)

        self._refresh_tree()
        self._recalc_totals()

    def _recalc_totals(self):
        """Recalculate and display totals from line_items."""
        subtotal = Decimal("0")
        discount = Decimal("0")
        cgst = Decimal("0")
        sgst = Decimal("0")
        igst = Decimal("0")
        grand = Decimal("0")

        for row in self.line_items:
            subtotal += _d(row['taxable_amount'])
            discount += _d(row['discount_amount'])
            cgst += _d(row['cgst_amount'])
            sgst += _d(row['sgst_amount'])
            igst += _d(row['igst_amount'])
            grand += _d(row['total_amount'])

        r = lambda v: float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        self.lbl_subtotal.configure(text=format_inr(r(subtotal)))
        self.lbl_discount.configure(text=format_inr(r(discount)))
        self.lbl_taxable.configure(text=format_inr(r(subtotal)))
        self.lbl_cgst.configure(text=format_inr(r(cgst)))
        self.lbl_sgst.configure(text=format_inr(r(sgst)))
        self.lbl_igst.configure(text=format_inr(r(igst)))
        self.lbl_grand_total.configure(text=format_inr(r(grand)))
        self.lbl_amount_words.configure(text=amount_in_words(r(grand)))

    # ──────────────────────────────────────────────────────────
    #  SAVE / CONFIRM / CLEAR
    # ──────────────────────────────────────────────────────────

    def _validate_form(self) -> tuple[bool, str]:
        """Validate the invoice form before saving."""
        if not self._get_selected_party():
            return False, "Please select a party."
        if not self.date_var.get():
            return False, "Please enter a date."
        if not self.line_items:
            return False, "Add at least one line item."
        return True, ""

    def _build_header(self) -> dict:
        """Build the header dict for saving."""
        party = self._get_selected_party()
        return {
            'party_id': party['id'] if party else 0,
            'date': self.date_var.get(),
            'due_date': self.due_date_var.get(),
            'reference_no': self.ref_var.get(),
            'narration': self.narration_var.get(),
            'godown_id': self._get_selected_godown_id(),
            'transport_name': self.transport_var.get(),
            'vehicle_no': self.vehicle_var.get(),
        }

    def _save_draft(self):
        """Save the invoice as a draft."""
        valid, msg = self._validate_form()
        if not valid:
            CTkMessagebox(title="Validation Error", message=msg, icon="cancel")
            return

        header = self._build_header()
        success, message, vid = create_sales_invoice(header, self.line_items)

        if success:
            CTkMessagebox(title="Success", message=message, icon="check")
            self.clear_form()
        else:
            CTkMessagebox(title="Error", message=message, icon="cancel")

    def _confirm_and_print(self):
        """Save as draft, confirm, generate PDF."""
        valid, msg = self._validate_form()
        if not valid:
            CTkMessagebox(title="Validation Error", message=msg, icon="cancel")
            return

        header = self._build_header()
        success, message, vid = create_sales_invoice(header, self.line_items)
        if not success:
            CTkMessagebox(title="Error", message=message, icon="cancel")
            return

        # Confirm
        ok, cmsg = confirm_sales_invoice(vid)
        if not ok:
            CTkMessagebox(title="Error", message=cmsg, icon="cancel")
            return

        # Export PDF
        pdf_ok, pdf_result = export_invoice_pdf(vid)
        if pdf_ok:
            CTkMessagebox(
                title="Success",
                message=f"Invoice confirmed and PDF exported.\n{pdf_result}",
                icon="check"
            )
        else:
            CTkMessagebox(
                title="Warning",
                message=f"Invoice confirmed but PDF failed: {pdf_result}",
                icon="warning"
            )

        self.clear_form()

    def clear_form(self):
        """Reset all form fields to defaults."""
        self.date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.due_date_var.set("")
        self.ref_var.set("")
        self.transport_var.set("")
        self.vehicle_var.set("")
        self.narration_var.set("")
        self.qty_var.set("1")
        self.rate_var.set("0")
        self.disc_var.set("0")
        self.line_items.clear()
        self._refresh_tree()
        self._recalc_totals()
        self._load_dropdowns()

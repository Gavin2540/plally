"""
GST Reports UI for PlywoodPro — 3 tabs:
Tab 1: GSTR-1 (B2B, B2C, CDNR, HSN), Tab 2: GSTR-3B, Tab 3: ITC Register
"""
import customtkinter as ctk
from tkinter import ttk
from datetime import datetime
from CTkMessagebox import CTkMessagebox

from modules.gst import (
    get_gstr1_b2b, get_gstr1_b2c, get_gstr1_hsn_summary,
    get_gstr3b_summary, get_itc_register,
)
from utils.excel_export import export_gstr1_excel, export_itc_register_excel
from utils.pdf_export import export_trial_balance_pdf
from utils.helpers import format_inr

ACCENT = "#2E7D32"
BLUE = "#1565C0"
PURPLE = "#7B1FA2"


class GstUI(ctk.CTkFrame):
    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        ctk.CTkLabel(self, text="GST Reports", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=ACCENT).pack(padx=10, pady=(10, 5), anchor="w")

        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)
        for t in ["GSTR-1", "GSTR-3B", "ITC Register"]:
            self.tabview.add(t)

        self._build_gstr1(self.tabview.tab("GSTR-1"))
        self._build_gstr3b(self.tabview.tab("GSTR-3B"))
        self._build_itc(self.tabview.tab("ITC Register"))

    # ══════════════════════════════════════════════════════════
    #  TAB 1 — GSTR-1
    # ══════════════════════════════════════════════════════════
    def _build_gstr1(self, tab):
        f = ctk.CTkFrame(tab, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(f, text="Month:").pack(side="left")
        now = datetime.now()
        self.g1_month = ctk.StringVar(value=str(now.month))
        ctk.CTkComboBox(f, variable=self.g1_month,
                        values=[str(i) for i in range(1, 13)], width=70).pack(side="left", padx=5)

        ctk.CTkLabel(f, text="Year:").pack(side="left")
        self.g1_year = ctk.StringVar(value=str(now.year))
        ctk.CTkEntry(f, textvariable=self.g1_year, width=70).pack(side="left", padx=5)

        ctk.CTkButton(f, text="Load", fg_color=ACCENT, width=80,
                       command=self._load_gstr1).pack(side="left", padx=10)
        ctk.CTkButton(f, text="Export Excel", fg_color=BLUE, width=110,
                       command=self._export_gstr1).pack(side="left", padx=5)

        # B2B tree
        ctk.CTkLabel(tab, text="B2B — Registered Parties", font=ctk.CTkFont(weight="bold"),
                     text_color=ACCENT).pack(padx=10, anchor="w", pady=(5, 0))
        cols_b2b = ('gstin', 'party', 'invoice', 'date', 'taxable', 'cgst', 'sgst', 'igst', 'total')
        self.b2b_tree = ttk.Treeview(tab, columns=cols_b2b, show='headings', height=5)
        for c, t, w in [('gstin', 'GSTIN', 130), ('party', 'Party', 140), ('invoice', 'Invoice', 90),
                         ('date', 'Date', 80), ('taxable', 'Taxable', 80), ('cgst', 'CGST', 70),
                         ('sgst', 'SGST', 70), ('igst', 'IGST', 70), ('total', 'Total', 80)]:
            self.b2b_tree.heading(c, text=t)
            self.b2b_tree.column(c, width=w, anchor='e' if c in ('taxable', 'cgst', 'sgst', 'igst', 'total') else 'w')
        self.b2b_tree.pack(fill="x", padx=10, pady=2)

        # HSN tree
        ctk.CTkLabel(tab, text="HSN Summary", font=ctk.CTkFont(weight="bold"),
                     text_color=BLUE).pack(padx=10, anchor="w", pady=(5, 0))
        cols_hsn = ('hsn', 'desc', 'unit', 'qty', 'value', 'taxable', 'cgst', 'sgst', 'igst')
        self.hsn_tree = ttk.Treeview(tab, columns=cols_hsn, show='headings', height=4)
        for c, t, w in [('hsn', 'HSN', 70), ('desc', 'Description', 160), ('unit', 'Unit', 50),
                         ('qty', 'Qty', 60), ('value', 'Value', 80), ('taxable', 'Taxable', 80),
                         ('cgst', 'CGST', 70), ('sgst', 'SGST', 70), ('igst', 'IGST', 70)]:
            self.hsn_tree.heading(c, text=t)
            self.hsn_tree.column(c, width=w, anchor='e' if c in ('qty', 'value', 'taxable', 'cgst', 'sgst', 'igst') else 'w')
        self.hsn_tree.pack(fill="x", padx=10, pady=2)

    def _load_gstr1(self):
        m = int(self.g1_month.get()); y = int(self.g1_year.get())
        # B2B
        self.b2b_tree.delete(*self.b2b_tree.get_children())
        for r in get_gstr1_b2b(m, y):
            self.b2b_tree.insert('', 'end', values=(
                r.get('gstin', ''), r.get('party_name', ''), r.get('voucher_no', ''),
                r.get('date', ''), format_inr(r.get('taxable_amount', 0)),
                format_inr(r.get('cgst_amount', 0)), format_inr(r.get('sgst_amount', 0)),
                format_inr(r.get('igst_amount', 0)), format_inr(r.get('total_amount', 0))))
        # HSN
        self.hsn_tree.delete(*self.hsn_tree.get_children())
        for r in get_gstr1_hsn_summary(m, y):
            self.hsn_tree.insert('', 'end', values=(
                r.get('hsn_code', ''), r.get('description', ''), r.get('unit', ''),
                r.get('total_qty', 0), format_inr(r.get('total_value', 0)),
                format_inr(r.get('total_taxable', 0)), format_inr(r.get('cgst', 0)),
                format_inr(r.get('sgst', 0)), format_inr(r.get('igst', 0))))

    def _export_gstr1(self):
        m = int(self.g1_month.get()); y = int(self.g1_year.get())
        ok, path = export_gstr1_excel(m, y)
        if ok:
            CTkMessagebox(title="Success", message=f"Exported: {path}", icon="check")
        else:
            CTkMessagebox(title="Error", message=path, icon="cancel")

    # ══════════════════════════════════════════════════════════
    #  TAB 2 — GSTR-3B
    # ══════════════════════════════════════════════════════════
    def _build_gstr3b(self, tab):
        f = ctk.CTkFrame(tab, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(f, text="Month:").pack(side="left")
        now = datetime.now()
        self.g3_month = ctk.StringVar(value=str(now.month))
        ctk.CTkComboBox(f, variable=self.g3_month,
                        values=[str(i) for i in range(1, 13)], width=70).pack(side="left", padx=5)
        ctk.CTkLabel(f, text="Year:").pack(side="left")
        self.g3_year = ctk.StringVar(value=str(now.year))
        ctk.CTkEntry(f, textvariable=self.g3_year, width=70).pack(side="left", padx=5)
        ctk.CTkButton(f, text="Generate", fg_color=ACCENT, width=100,
                       command=self._load_gstr3b).pack(side="left", padx=10)
        ctk.CTkButton(f, text="Export PDF", fg_color=BLUE, width=100,
                       command=self._export_gstr3b).pack(side="left", padx=5)

        cols = ('head', 'cgst', 'sgst', 'igst', 'total')
        self.g3_tree = ttk.Treeview(tab, columns=cols, show='headings', height=6)
        for c, t, w in [('head', 'Description', 220), ('cgst', 'CGST', 100),
                         ('sgst', 'SGST', 100), ('igst', 'IGST', 100), ('total', 'Total', 110)]:
            self.g3_tree.heading(c, text=t)
            self.g3_tree.column(c, width=w, anchor='e' if c != 'head' else 'w')
        self.g3_tree.pack(fill="both", expand=True, padx=10, pady=5)

    def _load_gstr3b(self):
        m = int(self.g3_month.get()); y = int(self.g3_year.get())
        data = get_gstr3b_summary(m, y)
        self.g3_tree.delete(*self.g3_tree.get_children())
        self._g3_data = data

        o = data.get('outward', {})
        i = data.get('itc', {})
        n = data.get('net_payable', {})

        self.g3_tree.insert('', 'end', values=(
            'Outward Supplies (Tax Payable)',
            format_inr(o.get('cgst', 0)), format_inr(o.get('sgst', 0)),
            format_inr(o.get('igst', 0)),
            format_inr(sum(o.get(k, 0) for k in ('cgst', 'sgst', 'igst')))))
        self.g3_tree.insert('', 'end', values=(
            'Input Tax Credit (ITC)',
            format_inr(i.get('cgst', 0)), format_inr(i.get('sgst', 0)),
            format_inr(i.get('igst', 0)),
            format_inr(sum(i.get(k, 0) for k in ('cgst', 'sgst', 'igst')))))
        self.g3_tree.insert('', 'end', values=(
            'NET TAX PAYABLE',
            format_inr(n.get('cgst', 0)), format_inr(n.get('sgst', 0)),
            format_inr(n.get('igst', 0)), format_inr(n.get('total', 0))))

    def _export_gstr3b(self):
        from utils.pdf_export import export_trial_balance_pdf as _unused
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        import os
        from pathlib import Path

        m = int(self.g3_month.get()); y = int(self.g3_year.get())
        data = get_gstr3b_summary(m, y)
        try:
            export_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "exports"
            export_dir.mkdir(exist_ok=True)
            path = str(export_dir / f"GSTR3B_{y}_{m:02d}.pdf")

            styles = getSampleStyleSheet()
            story = [Paragraph(f"GSTR-3B Summary — {m:02d}/{y}", styles['Title']), Spacer(1, 5 * mm)]

            o = data.get('outward', {}); i = data.get('itc', {}); n = data.get('net_payable', {})
            tbl = [['Description', 'CGST', 'SGST', 'IGST', 'Total'],
                   ['Outward Supplies', o.get('cgst', 0), o.get('sgst', 0), o.get('igst', 0),
                    sum(o.get(k, 0) for k in ('cgst', 'sgst', 'igst'))],
                   ['ITC Available', i.get('cgst', 0), i.get('sgst', 0), i.get('igst', 0),
                    sum(i.get(k, 0) for k in ('cgst', 'sgst', 'igst'))],
                   ['NET PAYABLE', n.get('cgst', 0), n.get('sgst', 0), n.get('igst', 0), n.get('total', 0)]]

            t = Table(tbl, colWidths=[160, 80, 80, 80, 90])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            story.append(t)
            doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm)
            doc.build(story)
            CTkMessagebox(title="Success", message=f"PDF: {path}", icon="check")
        except Exception as e:
            CTkMessagebox(title="Error", message=str(e), icon="cancel")

    # ══════════════════════════════════════════════════════════
    #  TAB 3 — ITC REGISTER
    # ══════════════════════════════════════════════════════════
    def _build_itc(self, tab):
        f = ctk.CTkFrame(tab, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(f, text="From:").pack(side="left")
        self.itc_from = ctk.StringVar()
        ctk.CTkEntry(f, textvariable=self.itc_from, width=100, placeholder_text="YYYY-MM-DD").pack(side="left", padx=5)
        ctk.CTkLabel(f, text="To:").pack(side="left")
        self.itc_to = ctk.StringVar()
        ctk.CTkEntry(f, textvariable=self.itc_to, width=100, placeholder_text="YYYY-MM-DD").pack(side="left", padx=5)
        ctk.CTkButton(f, text="Load", fg_color=ACCENT, width=80, command=self._load_itc).pack(side="left", padx=10)
        ctk.CTkButton(f, text="Export Excel", fg_color=BLUE, width=110, command=self._export_itc).pack(side="left")

        cols = ('invoice', 'date', 'party', 'gstin', 'taxable', 'cgst', 'sgst', 'igst', 'status')
        tc = ctk.CTkFrame(tab, fg_color="transparent")
        tc.pack(fill="both", expand=True, padx=10, pady=5)
        self.itc_tree = ttk.Treeview(tc, columns=cols, show='headings', height=10)
        for c, t, w in [('invoice', 'Invoice', 90), ('date', 'Date', 80), ('party', 'Party', 150),
                         ('gstin', 'GSTIN', 130), ('taxable', 'Taxable', 80), ('cgst', 'CGST', 70),
                         ('sgst', 'SGST', 70), ('igst', 'IGST', 70), ('status', 'Status', 70)]:
            self.itc_tree.heading(c, text=t)
            self.itc_tree.column(c, width=w, anchor='e' if c in ('taxable', 'cgst', 'sgst', 'igst') else 'w')
        self.itc_tree.pack(side="left", fill="both", expand=True)

        self.itc_total = ctk.StringVar(value="Total Eligible ITC: --")
        ctk.CTkLabel(tab, textvariable=self.itc_total, font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=ACCENT).pack(padx=10, pady=5, anchor="e")

    def _load_itc(self):
        self.itc_tree.delete(*self.itc_tree.get_children())
        data = get_itc_register(self.itc_from.get(), self.itc_to.get())
        for r in data['entries']:
            self.itc_tree.insert('', 'end', values=(
                r.get('voucher_no', ''), r.get('date', ''), r.get('party_name', ''),
                r.get('gstin', ''), format_inr(r.get('taxable_amount', 0)),
                format_inr(r.get('cgst_amount', 0)), format_inr(r.get('sgst_amount', 0)),
                format_inr(r.get('igst_amount', 0)), r.get('status', '')))
        self.itc_total.set(f"Total Eligible ITC: {format_inr(data['total_eligible_itc'])}")

    def _export_itc(self):
        ok, path = export_itc_register_excel(self.itc_from.get(), self.itc_to.get())
        if ok:
            CTkMessagebox(title="Success", message=f"Exported: {path}", icon="check")
        else:
            CTkMessagebox(title="Error", message=path, icon="cancel")

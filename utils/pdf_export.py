"""
PDF Export utility for PlywoodPro.
Builds GST Tax Invoice PDFs using ReportLab with all 11 legally required fields
from Section 12 of the spec. Saves to exports/ folder and opens with os.startfile().
"""

import os
import traceback
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from db.connection import get_connection
from modules.masters import get_company
from utils.helpers import format_inr, amount_in_words


# ═══════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'exports')
ACCENT = colors.HexColor("#2E7D32")
LIGHT_GREEN = colors.HexColor("#E8F5E9")
DARK_BG = colors.HexColor("#1B5E20")


def _d(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _r2(val: Decimal) -> float:
    return float(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _ask_save_location(default_filename: str, filetype: str = "pdf") -> str | None:
    """Show file save dialog. Returns chosen path or None if cancelled."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    if filetype == "pdf":
        filetypes = [("PDF Files", "*.pdf"), ("All Files", "*.*")]
        ext = ".pdf"
    else:
        filetypes = [("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        ext = ".xlsx"

    initial_dir = os.path.expanduser("~/Documents")

    path = filedialog.asksaveasfilename(
        title="Save File",
        initialdir=initial_dir,
        initialfile=default_filename,
        defaultextension=ext,
        filetypes=filetypes,
        parent=root
    )
    root.destroy()
    return path if path else None


# ═══════════════════════════════════════════════════════════════════════
#  BUILD INVOICE PDF
# ═══════════════════════════════════════════════════════════════════════

def export_invoice_pdf(voucher_id: int) -> tuple[bool, str]:
    """
    Generate a GST Tax Invoice PDF for the given voucher_id.
    Returns (success, filepath_or_error_message).
    """
    conn = get_connection()
    try:
        # Fetch voucher
        v = conn.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,)).fetchone()
        if not v:
            return False, "Voucher not found."
        v = dict(v)

        # Fetch party
        party_row = conn.execute(
            "SELECT * FROM parties WHERE id = ?", (v['party_id'],)
        ).fetchone()
        party = dict(party_row) if party_row else None

        # Fetch line items
        item_rows = conn.execute(
            "SELECT * FROM voucher_items WHERE voucher_id = ?", (voucher_id,)
        ).fetchall()
        items = [dict(r) for r in item_rows]

        # Fetch company
        company = get_company()
        if not company:
            return False, "Company details not set up."

        # Build default filename
        safe_no = v['voucher_no'].replace('/', '-').replace('\\', '-')
        filename = f"{safe_no}.pdf"

        filepath = _ask_save_location(filename, "pdf")
        if not filepath:
            return False, "Export cancelled."

        # Build the PDF
        _build_pdf(filepath, v, party, items, company)

        # Open the file
        try:
            os.startfile(filepath)
        except Exception:
            pass  # Might not be on Windows or might fail in some environments

        return True, filepath

    except Exception as e:
        print(f"[PlywoodPro] Error exporting PDF: {e}")
        traceback.print_exc()
        return False, f"PDF export error: {e}"
    finally:
        conn.close()


def _build_pdf(filepath: str, voucher, party, items, company):
    """Construct the PDF document with all legally required fields."""
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    # Custom styles
    styles.add(ParagraphStyle(
        'InvoiceTitle', parent=styles['Title'],
        fontSize=18, textColor=DARK_BG, spaceAfter=2 * mm,
        alignment=TA_CENTER, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'CompanyName', parent=styles['Heading1'],
        fontSize=14, textColor=DARK_BG, spaceAfter=1 * mm,
        alignment=TA_CENTER, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'SmallCenter', parent=styles['Normal'],
        fontSize=8, alignment=TA_CENTER, textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        'SmallLeft', parent=styles['Normal'],
        fontSize=8, textColor=colors.black,
    ))
    styles.add(ParagraphStyle(
        'BoldLeft', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'SmallRight', parent=styles['Normal'],
        fontSize=8, alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'AmountWords', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Oblique', textColor=DARK_BG,
    ))

    story = []

    # ── 1. TITLE ────────────────────────────────────────────
    invoice_type = voucher['voucher_type'].upper()
    if invoice_type == 'SALES INVOICE':
        invoice_type = 'TAX INVOICE'
    story.append(Paragraph(invoice_type, styles['InvoiceTitle']))

    # ── 2. COMPANY / SUPPLIER DETAILS ───────────────────────
    story.append(Paragraph(company['name'], styles['CompanyName']))

    addr_parts = [
        company.get('address_line1', ''), company.get('address_line2', ''),
        company.get('city', ''),
        f"{company.get('state', '')} - {company.get('pincode', '')}",
    ]
    addr_str = ', '.join([p for p in addr_parts if p and p.strip() and p.strip() != '-'])
    story.append(Paragraph(addr_str, styles['SmallCenter']))

    details = []
    if company.get('gstin'):
        details.append(f"GSTIN: {company['gstin']}")
    if company.get('phone'):
        details.append(f"Phone: {company['phone']}")
    if company.get('email'):
        details.append(f"Email: {company['email']}")
    story.append(Paragraph(' | '.join(details), styles['SmallCenter']))

    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT))
    story.append(Spacer(1, 3 * mm))

    # ── 3/4. BUYER DETAILS + INVOICE NO/DATE ────────────────
    buyer_label = "Bill To:" if voucher['voucher_type'] == 'Sales Invoice' else "Supplier:"
    party_name = party['name'] if party else 'N/A'
    party_addr = ', '.join([
        p for p in [
            party.get('address_line1', '') if party else '',
            party.get('city', '') if party else '',
            party.get('state', '') if party else '',
        ] if p
    ])
    party_gstin = party.get('gstin', '') if party else ''
    party_state = party.get('state', '') if party else ''

    # Format date for display
    raw_date = voucher.get('date', '')
    display_date = raw_date
    if raw_date and len(raw_date) >= 10:
        try:
            parts = raw_date.split('-')
            display_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass

    due_date = voucher.get('due_date', '')
    if due_date and len(due_date) >= 10:
        try:
            parts = due_date.split('-')
            due_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass

    info_data = [
        [Paragraph(f"<b>{buyer_label}</b>", styles['SmallLeft']),
         Paragraph(f"<b>Invoice No:</b> {voucher['voucher_no']}", styles['SmallRight'])],
        [Paragraph(f"<b>{party_name}</b>", styles['BoldLeft']),
         Paragraph(f"<b>Date:</b> {display_date}", styles['SmallRight'])],
        [Paragraph(party_addr, styles['SmallLeft']),
         Paragraph(f"<b>Due Date:</b> {due_date}", styles['SmallRight'])],
        [Paragraph(f"GSTIN: {party_gstin}", styles['SmallLeft']),
         Paragraph(f"<b>Ref:</b> {voucher.get('reference_no', '')}", styles['SmallRight'])],
        [Paragraph(f"State: {party_state}", styles['SmallLeft']),
         Paragraph('', styles['SmallRight'])],
    ]

    info_table = Table(info_data, colWidths=[doc.width * 0.55, doc.width * 0.45])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # ── 5. ITEMS TABLE ──────────────────────────────────────
    header_row = ['#', 'Description', 'HSN', 'Qty', 'Unit', 'Rate',
                  'Disc%', 'Taxable', 'GST%', 'CGST', 'SGST', 'IGST', 'Total']

    table_data = [header_row]
    for idx, item in enumerate(items, 1):
        desc = item.get('description', '') or ''
        table_data.append([
            str(idx),
            desc[:30],
            item.get('hsn_code', ''),
            f"{item['qty']:.2f}",
            item.get('unit', ''),
            f"{item['rate']:.2f}",
            f"{item.get('discount_pct', 0):.1f}",
            format_inr(item.get('taxable_amount', 0)),
            f"{item.get('gst_rate', 0):.0f}%",
            format_inr(item.get('cgst_amount', 0)),
            format_inr(item.get('sgst_amount', 0)),
            format_inr(item.get('igst_amount', 0)),
            format_inr(item.get('total_amount', 0)),
        ])

    col_widths = [
        doc.width * w for w in
        [0.03, 0.16, 0.06, 0.05, 0.05, 0.07, 0.05, 0.1, 0.05, 0.09, 0.09, 0.09, 0.11]
    ]

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREEN]),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # ── 6. TOTALS ───────────────────────────────────────────
    subtotal = _d(voucher.get('total_amount', 0))
    discount = _d(voucher.get('discount_amount', 0))
    total_cgst = sum(_d(i.get('cgst_amount', 0)) for i in items)
    total_sgst = sum(_d(i.get('sgst_amount', 0)) for i in items)
    total_igst = sum(_d(i.get('igst_amount', 0)) for i in items)
    grand_total = _d(voucher.get('grand_total', 0))

    totals_data = [
        ['', 'Subtotal:', format_inr(_r2(subtotal))],
    ]
    if discount > 0:
        totals_data.append(['', 'Discount:', f"(-) {format_inr(_r2(discount))}"])
    totals_data.append(['', 'Taxable Amount:', format_inr(_r2(subtotal - discount))])
    if total_cgst > 0:
        totals_data.append(['', 'CGST:', format_inr(_r2(total_cgst))])
    if total_sgst > 0:
        totals_data.append(['', 'SGST:', format_inr(_r2(total_sgst))])
    if total_igst > 0:
        totals_data.append(['', 'IGST:', format_inr(_r2(total_igst))])
    totals_data.append(['', Paragraph('<b>Grand Total:</b>', styles['SmallRight']),
                         Paragraph(f'<b>{format_inr(_r2(grand_total))}</b>', styles['SmallRight'])])

    totals_table = Table(totals_data, colWidths=[doc.width * 0.55, doc.width * 0.25, doc.width * 0.2])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEABOVE', (1, -1), (-1, -1), 1, ACCENT),
    ]))
    story.append(totals_table)

    # ── 7. AMOUNT IN WORDS ──────────────────────────────────
    story.append(Spacer(1, 3 * mm))
    words = amount_in_words(_r2(grand_total))
    story.append(Paragraph(f"<b>Amount in Words:</b> {words}", styles['AmountWords']))

    # ── 8. PAYMENT TERMS ────────────────────────────────────
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 2 * mm))

    if voucher.get('due_date'):
        story.append(Paragraph(
            f"<b>Payment Due:</b> {due_date}", styles['SmallLeft']
        ))

    # ── 9. BANK DETAILS ─────────────────────────────────────
    if company.get('bank_name'):
        bank_info = (
            f"<b>Bank Details:</b> {company['bank_name']}"
            f" | A/c: {company.get('bank_account', '')}"
            f" | IFSC: {company.get('bank_ifsc', '')}"
        )
        story.append(Paragraph(bank_info, styles['SmallLeft']))

    # ── NARRATION ───────────────────────────────────────────
    if voucher.get('narration'):
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Narration:</b> {voucher['narration']}", styles['SmallLeft']))

    # ── 10. AUTHORIZED SIGNATORY ────────────────────────────
    story.append(Spacer(1, 15 * mm))
    sig_data = [
        ['', ''],
        [Paragraph('Received By', styles['SmallCenter']),
         Paragraph(f"For <b>{company['name']}</b><br/>Authorized Signatory", styles['SmallRight'])],
    ]
    sig_table = Table(sig_data, colWidths=[doc.width * 0.5, doc.width * 0.5])
    sig_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 1), (0, 1), 0.5, colors.grey),
        ('LINEABOVE', (1, 1), (1, 1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)

    # ── 11. COMPUTER GENERATED NOTE ─────────────────────────
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=colors.grey))
    story.append(Paragraph(
        "This is a computer generated invoice and does not require a physical signature.",
        styles['SmallCenter']
    ))

    # Build the PDF
    doc.build(story)


# ═══════════════════════════════════════════════════════════════════════
#  ACCOUNTING REPORT EXPORTS
# ═══════════════════════════════════════════════════════════════════════

def _report_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('ReportTitle', parent=styles['Title'], fontSize=16, spaceAfter=10))
    styles.add(ParagraphStyle('ReportSub', parent=styles['Normal'], fontSize=10, textColor=colors.grey))
    return styles


def _save_and_open(story, filename):
    path = _ask_save_location(filename, "pdf")
    if not path:
        return None
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    doc.build(story)
    return path


def _fmt(val):
    try:
        return f"{float(val):,.2f}"
    except:
        return str(val)


def export_ledger_pdf(account_id, account_name, date_from='', date_to=''):
    """Export account ledger to PDF."""
    from modules.accounting import get_ledger
    try:
        rows = get_ledger(account_id, date_from, date_to)
        styles = _report_styles()
        story = []

        story.append(Paragraph(f"Ledger: {account_name}", styles['ReportTitle']))
        period = f"Period: {date_from or 'Start'} to {date_to or 'Today'}"
        story.append(Paragraph(period, styles['ReportSub']))
        story.append(Spacer(1, 5*mm))

        data = [['Date', 'Voucher', 'Type', 'Narration', 'Debit', 'Credit', 'Balance']]
        for r in rows:
            data.append([
                r['date'], r['voucher_no'], r['voucher_type'],
                r['narration'][:30], _fmt(r['debit']) if r['debit'] else '',
                _fmt(r['credit']) if r['credit'] else '', _fmt(r['running_balance'])
            ])

        t = Table(data, colWidths=[55, 60, 65, 110, 60, 60, 70])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E7D32')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('ALIGN', (4,0), (-1,-1), 'RIGHT'),
        ]))
        story.append(t)
        path = _save_and_open(story, f"Ledger_{account_name.replace(' ','_')}.pdf")
        if not path:
            return False, "Export cancelled."
        return True, path
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def export_trial_balance_pdf(date_from='', date_to=''):
    """Export trial balance to PDF."""
    from modules.accounting import get_trial_balance
    try:
        tb = get_trial_balance(date_from, date_to)
        styles = _report_styles()
        story = []

        bal_text = "BALANCED" if tb['balanced'] else "NOT BALANCED"
        story.append(Paragraph(f"Trial Balance ({bal_text})", styles['ReportTitle']))
        story.append(Spacer(1, 5*mm))

        data = [['Group', 'Account', 'Debit', 'Credit', 'Closing Dr', 'Closing Cr']]
        for r in tb['rows']:
            data.append([r['group_name'], r['account_name'],
                _fmt(r['total_debit']), _fmt(r['total_credit']),
                _fmt(r['closing_dr']) if r['closing_dr'] else '',
                _fmt(r['closing_cr']) if r['closing_cr'] else ''])
        data.append(['', 'TOTAL', _fmt(tb['total_debit']), _fmt(tb['total_credit']), '', ''])

        t = Table(data, colWidths=[90, 130, 70, 70, 70, 70])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E7D32')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ]))
        story.append(t)
        path = _save_and_open(story, "Trial_Balance.pdf")
        if not path:
            return False, "Export cancelled."
        return True, path
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def export_pl_pdf(date_from='', date_to=''):
    """Export Profit & Loss to PDF."""
    from modules.accounting import get_profit_and_loss
    try:
        pl = get_profit_and_loss(date_from, date_to)
        styles = _report_styles()
        story = []

        story.append(Paragraph("Profit & Loss Statement", styles['ReportTitle']))
        story.append(Spacer(1, 5*mm))

        data = [['Type', 'Account', 'Group', 'Amount']]
        for r in pl['income']:
            data.append(['Income', r['name'], r['group'], _fmt(r['amount'])])
        data.append(['', 'Total Income', '', _fmt(pl['total_income'])])
        for r in pl['expenses']:
            data.append(['Expense', r['name'], r['group'], _fmt(r['amount'])])
        data.append(['', 'Total Expenses', '', _fmt(pl['total_expense'])])
        data.append(['', 'NET PROFIT/LOSS', '', _fmt(pl['net_profit'])])

        t = Table(data, colWidths=[60, 180, 120, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1565C0')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('ALIGN', (3,0), (3,-1), 'RIGHT'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ]))
        story.append(t)
        path = _save_and_open(story, "Profit_and_Loss.pdf")
        if not path:
            return False, "Export cancelled."
        return True, path
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def export_bs_pdf(as_of=''):
    """Export Balance Sheet to PDF."""
    from modules.accounting import get_balance_sheet
    try:
        bs = get_balance_sheet(as_of)
        styles = _report_styles()
        story = []

        bal = "BALANCED" if bs['balanced'] else "NOT BALANCED"
        story.append(Paragraph(f"Balance Sheet ({bal})", styles['ReportTitle']))
        story.append(Spacer(1, 5*mm))

        data = [['Side', 'Account', 'Group', 'Amount']]
        for r in bs['assets']:
            data.append(['Asset', r['name'], r['group'], _fmt(r['amount'])])
        data.append(['', 'Total Assets', '', _fmt(bs['total_assets'])])
        for r in bs['liabilities']:
            data.append(['Liability', r['name'], r['group'], _fmt(r['amount'])])
        data.append(['', 'Total Liabilities', '', _fmt(bs['total_liabilities'])])

        t = Table(data, colWidths=[60, 180, 120, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7B1FA2')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('ALIGN', (3,0), (3,-1), 'RIGHT'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ]))
        story.append(t)
        path = _save_and_open(story, "Balance_Sheet.pdf")
        if not path:
            return False, "Export cancelled."
        return True, path
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def export_sales_register_pdf(date_from='', date_to=''):
    """Export Sales Register to PDF."""
    from modules.reports import get_sales_register
    try:
        rows = get_sales_register(date_from, date_to)
        styles = _report_styles()
        story = []
        story.append(Paragraph("Sales Register", styles['ReportTitle']))
        story.append(Paragraph(f"Period: {date_from or 'Start'} to {date_to or 'Today'}", styles['ReportSub']))
        story.append(Spacer(1, 5*mm))

        data = [['Date', 'Invoice', 'Party', 'Taxable', 'CGST', 'SGST', 'IGST', 'Total']]
        for r in rows:
            data.append([r.get('date',''), r.get('voucher_no',''), r.get('party_name','')[:20],
                _fmt(r.get('taxable_amount')), _fmt(r.get('cgst_amount')),
                _fmt(r.get('sgst_amount')), _fmt(r.get('igst_amount')), _fmt(r.get('grand_total'))])
        if rows:
            data.append(['','','TOTAL',
                _fmt(sum(float(r.get('taxable_amount',0) or 0) for r in rows)),
                _fmt(sum(float(r.get('cgst_amount',0) or 0) for r in rows)),
                _fmt(sum(float(r.get('sgst_amount',0) or 0) for r in rows)),
                _fmt(sum(float(r.get('igst_amount',0) or 0) for r in rows)),
                _fmt(sum(float(r.get('grand_total',0) or 0) for r in rows))])

        t = Table(data, colWidths=[55, 65, 90, 60, 55, 55, 55, 65])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E7D32')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ]))
        story.append(t)
        path = _save_and_open(story, "Sales_Register.pdf")
        if not path:
            return False, "Export cancelled."
        return True, path
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def export_purchase_register_pdf(date_from='', date_to=''):
    """Export Purchase Register to PDF."""
    from modules.reports import get_purchase_register
    try:
        rows = get_purchase_register(date_from, date_to)
        styles = _report_styles()
        story = []
        story.append(Paragraph("Purchase Register", styles['ReportTitle']))
        story.append(Paragraph(f"Period: {date_from or 'Start'} to {date_to or 'Today'}", styles['ReportSub']))
        story.append(Spacer(1, 5*mm))

        data = [['Date', 'Invoice', 'Party', 'Taxable', 'CGST', 'SGST', 'IGST', 'Total']]
        for r in rows:
            data.append([r.get('date',''), r.get('voucher_no',''), r.get('party_name','')[:20],
                _fmt(r.get('taxable_amount')), _fmt(r.get('cgst_amount')),
                _fmt(r.get('sgst_amount')), _fmt(r.get('igst_amount')), _fmt(r.get('grand_total'))])

        t = Table(data, colWidths=[55, 65, 90, 60, 55, 55, 55, 65])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1565C0')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ]))
        story.append(t)
        path = _save_and_open(story, "Purchase_Register.pdf")
        if not path:
            return False, "Export cancelled."
        return True, path
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def export_party_outstanding_pdf(party_type=''):
    """Export Party Outstanding to PDF."""
    from modules.reports import get_party_outstanding
    try:
        rows = get_party_outstanding(party_type)
        styles = _report_styles()
        story = []
        story.append(Paragraph("Party Outstanding Report", styles['ReportTitle']))
        story.append(Spacer(1, 5*mm))

        data = [['Party', 'Type', 'Invoiced', 'Paid', 'Balance', 'Oldest']]
        for r in rows:
            data.append([r.get('party_name','')[:25], r.get('type',''),
                _fmt(r.get('total_invoiced')), _fmt(r.get('total_paid')),
                _fmt(r.get('balance')), r.get('oldest_invoice_date','')])

        t = Table(data, colWidths=[120, 60, 75, 75, 75, 70])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7B1FA2')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('ALIGN', (2,0), (4,-1), 'RIGHT'),
        ]))
        story.append(t)
        path = _save_and_open(story, "Party_Outstanding.pdf")
        if not path:
            return False, "Export cancelled."
        return True, path
    except Exception as e:
        traceback.print_exc()
        return False, str(e)

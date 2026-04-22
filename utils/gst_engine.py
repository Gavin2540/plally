"""
GST Calculation Engine for PlywoodPro.
Handles GST rate lookup by HSN code, intra-state vs inter-state tax split
(CGST/SGST vs IGST), and per-line-item tax calculation.
"""

from decimal import Decimal, ROUND_HALF_UP


# ── Common HSN Codes for Plywood Trade ─────────────────────────────
HSN_GST_MAP = {
    '4412': {'description': 'Plywood, veneered panels, blockboard', 'gst_rate': 18.0},
    '4418': {'description': 'Flush doors, builders joinery, wood panel products', 'gst_rate': 18.0},
    '4421': {'description': 'Particle board, MDF, fibreboard', 'gst_rate': 18.0},
    '4415': {'description': 'Packing cases, wooden boxes', 'gst_rate': 12.0},
    '4414': {'description': 'Wooden frames for paintings, photos', 'gst_rate': 12.0},
    '3214': {'description': 'Wood putty, fillers', 'gst_rate': 18.0},
    '7317': {'description': 'Nails, tacks, staples (hardware)', 'gst_rate': 18.0},
}

# For dropdown in item creation UI
HSN_CODES_LIST = [
    ('4412', 'Plywood, veneered panels, blockboard', 18.0),
    ('4418', 'Flush doors, builders joinery, wood panel products', 18.0),
    ('4421', 'Particle board, MDF, fibreboard', 18.0),
    ('4415', 'Packing cases, wooden boxes', 12.0),
    ('4414', 'Wooden frames for paintings, photos', 12.0),
    ('3214', 'Wood putty, fillers', 18.0),
    ('7317', 'Nails, tacks, staples (hardware)', 18.0),
]


def get_gst_rate_for_hsn(hsn_code: str) -> float:
    """
    Look up the default GST rate for a given HSN code.
    Returns 18.0 as default if HSN code is not found in the map.
    """
    info = HSN_GST_MAP.get(hsn_code.strip())
    if info:
        return info['gst_rate']
    return 18.0  # default rate for plywood trade


def is_intra_state(company_state_code: str, party_state_code: str) -> bool:
    """
    Determine if a transaction is intra-state (same state) or inter-state.
    Returns True if both state codes match (intra-state → CGST + SGST).
    Returns False if different (inter-state → IGST).
    """
    if not company_state_code or not party_state_code:
        return True  # default to intra-state if state info is missing
    return company_state_code.strip() == party_state_code.strip()


def calculate_tax_split(gst_rate: float, company_state_code: str, party_state_code: str) -> dict:
    """
    Given a GST rate and state codes, return the tax rate split.

    Returns dict with keys:
        cgst_rate, sgst_rate, igst_rate (all as float percentages)
    """
    gst = Decimal(str(gst_rate))
    half = (gst / 2).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    if is_intra_state(company_state_code, party_state_code):
        return {
            'cgst_rate': float(half),
            'sgst_rate': float(half),
            'igst_rate': 0.0,
        }
    else:
        return {
            'cgst_rate': 0.0,
            'sgst_rate': 0.0,
            'igst_rate': float(gst),
        }


def calculate_line_item_tax(
    qty: float,
    rate: float,
    discount_pct: float,
    gst_rate: float,
    company_state_code: str,
    party_state_code: str,
) -> dict:
    """
    Calculate complete tax breakdown for a single line item.

    Calculation per spec Section 6.4:
        taxable_amount  = (qty × rate) - discount_amount
        discount_amount = (qty × rate) × (discount_pct / 100)
        cgst/sgst/igst amounts based on intra/inter state

    Returns dict with:
        discount_amount, taxable_amount,
        cgst_rate, cgst_amount, sgst_rate, sgst_amount,
        igst_rate, igst_amount, total_amount
    """
    d_qty = Decimal(str(qty))
    d_rate = Decimal(str(rate))
    d_disc_pct = Decimal(str(discount_pct))

    gross = d_qty * d_rate
    discount_amount = (gross * d_disc_pct / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    taxable_amount = (gross - discount_amount).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    split = calculate_tax_split(gst_rate, company_state_code, party_state_code)

    cgst_amount = (taxable_amount * Decimal(str(split['cgst_rate'])) / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    sgst_amount = (taxable_amount * Decimal(str(split['sgst_rate'])) / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    igst_amount = (taxable_amount * Decimal(str(split['igst_rate'])) / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    total_amount = taxable_amount + cgst_amount + sgst_amount + igst_amount

    return {
        'discount_amount': float(discount_amount),
        'taxable_amount': float(taxable_amount),
        'cgst_rate': split['cgst_rate'],
        'cgst_amount': float(cgst_amount),
        'sgst_rate': split['sgst_rate'],
        'sgst_amount': float(sgst_amount),
        'igst_rate': split['igst_rate'],
        'igst_amount': float(igst_amount),
        'total_amount': float(total_amount),
    }

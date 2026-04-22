"""
Validation functions for PlywoodPro.
GSTIN, PAN, and HSN code validation following Indian government formats.
"""

import re


# ── Indian GST State Codes ──────────────────────────────────────────
GST_STATE_CODES = {
    '01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab',
    '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana',
    '07': 'Delhi', '08': 'Rajasthan', '09': 'Uttar Pradesh',
    '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
    '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram',
    '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam',
    '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha',
    '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
    '26': 'Dadra & Nagar Haveli and Daman & Diu',
    '27': 'Maharashtra', '29': 'Karnataka', '30': 'Goa',
    '31': 'Lakshadweep', '32': 'Kerala', '33': 'Tamil Nadu',
    '34': 'Puducherry', '35': 'Andaman & Nicobar Islands',
    '36': 'Telangana', '37': 'Andhra Pradesh', '38': 'Ladakh',
    '97': 'Other Territory',
}

# ── Indian State Name => State Code ─────────────────────────────────
STATE_NAME_TO_CODE = {v: k for k, v in GST_STATE_CODES.items()}

# ── List of Indian states for dropdowns ────────────────────────────
INDIAN_STATES = sorted(GST_STATE_CODES.values())

# ── Valid GST Rate Slabs ───────────────────────────────────────────
VALID_GST_RATES = [0.0, 5.0, 12.0, 18.0, 28.0]


def validate_gstin(gstin: str) -> tuple[bool, str]:
    """
    Validate a 15-character Indian GSTIN.
    Format: 2-digit state code + 10-char PAN + 1 entity + 1 default 'Z' + 1 check digit.
    Returns (is_valid, error_message).
    """
    if not gstin:
        return True, ''  # GSTIN is optional

    gstin = gstin.strip().upper()

    if len(gstin) != 15:
        return False, 'GSTIN must be exactly 15 characters'

    # Pattern: 2 digits, 5 uppercase, 4 digits, 1 uppercase, 1 alphanumeric, Z, 1 alphanumeric
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$'
    if not re.match(pattern, gstin):
        return False, 'Invalid GSTIN format'

    # Validate state code
    state_code = gstin[:2]
    if state_code not in GST_STATE_CODES:
        return False, f'Invalid state code: {state_code}'

    return True, ''


def validate_pan(pan: str) -> tuple[bool, str]:
    """
    Validate a 10-character Indian PAN.
    Format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F).
    Returns (is_valid, error_message).
    """
    if not pan:
        return True, ''  # PAN is optional

    pan = pan.strip().upper()

    if len(pan) != 10:
        return False, 'PAN must be exactly 10 characters'

    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    if not re.match(pattern, pan):
        return False, 'Invalid PAN format (expected: ABCDE1234F)'

    return True, ''


def validate_hsn(hsn_code: str) -> tuple[bool, str]:
    """
    Validate an HSN code (4, 6, or 8 digit numeric code).
    Returns (is_valid, error_message).
    """
    if not hsn_code:
        return False, 'HSN Code is required'

    hsn_code = hsn_code.strip()

    if not hsn_code.isdigit():
        return False, 'HSN Code must contain only digits'

    if len(hsn_code) not in (4, 6, 8):
        return False, 'HSN Code must be 4, 6, or 8 digits'

    return True, ''


def validate_pincode(pincode: str) -> tuple[bool, str]:
    """
    Validate an Indian pincode (6 digits, first digit not 0).
    Returns (is_valid, error_message).
    """
    if not pincode:
        return True, ''  # Pincode is optional

    pincode = pincode.strip()

    if not pincode.isdigit() or len(pincode) != 6:
        return False, 'Pincode must be exactly 6 digits'

    if pincode[0] == '0':
        return False, 'Pincode cannot start with 0'

    return True, ''


def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Validate an Indian phone number (10 digits, optionally prefixed with +91 or 0).
    Returns (is_valid, error_message).
    """
    if not phone:
        return True, ''  # Phone is optional

    phone = phone.strip().replace(' ', '').replace('-', '')

    # Remove country code prefix
    if phone.startswith('+91'):
        phone = phone[3:]
    elif phone.startswith('0'):
        phone = phone[1:]

    if not phone.isdigit() or len(phone) != 10:
        return False, 'Phone must be a valid 10-digit number'

    return True, ''


def validate_email(email: str) -> tuple[bool, str]:
    """
    Basic email format validation.
    Returns (is_valid, error_message).
    """
    if not email:
        return True, ''  # Email is optional

    email = email.strip()

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, 'Invalid email format'

    return True, ''


def validate_gst_rate(rate) -> tuple[bool, str]:
    """
    Validate that the GST rate is one of the allowed slabs: 0, 5, 12, 18, 28.
    Returns (is_valid, error_message).
    """
    try:
        rate_val = float(rate)
    except (ValueError, TypeError):
        return False, 'GST Rate must be a number'

    if rate_val not in VALID_GST_RATES:
        return False, f'GST Rate must be one of: {", ".join(str(int(r)) + "%" for r in VALID_GST_RATES)}'

    return True, ''

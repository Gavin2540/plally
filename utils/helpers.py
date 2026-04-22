"""
Helper utilities for PlywoodPro.
Date formatting, number formatting, Indian Rupee currency formatter,
and number-to-words converter for invoice amounts.
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP


def format_date_display(date_str: str) -> str:
    """
    Convert database date 'YYYY-MM-DD' to Indian display format 'DD/MM/YYYY'.
    Returns the original string unchanged if parsing fails.
    """
    if not date_str:
        return ''
    try:
        dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return str(date_str)


def format_date_db(display_date: str) -> str:
    """
    Convert Indian display date 'DD/MM/YYYY' to database format 'YYYY-MM-DD'.
    Returns the original string unchanged if parsing fails.
    """
    if not display_date:
        return ''
    try:
        dt = datetime.strptime(display_date.strip(), '%d/%m/%Y')
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return str(display_date)


def today_db() -> str:
    """Return today's date in database format 'YYYY-MM-DD'."""
    return date.today().strftime('%Y-%m-%d')


def today_display() -> str:
    """Return today's date in Indian display format 'DD/MM/YYYY'."""
    return date.today().strftime('%d/%m/%Y')


def format_inr(amount) -> str:
    """
    Format a numeric value as Indian Rupees: ₹ 1,23,456.00
    Uses the Indian numbering system (lakhs and crores).
    """
    if amount is None:
        return '₹ 0.00'

    try:
        value = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return '₹ 0.00'

    is_negative = value < 0
    value = abs(value)

    integer_part = int(value)
    decimal_part = f"{value - integer_part:.2f}"[1:]  # ".XX"

    # Indian grouping: last 3 digits, then groups of 2
    s = str(integer_part)
    if len(s) <= 3:
        formatted = s
    else:
        last_three = s[-3:]
        remaining = s[:-3]
        # Group remaining digits in pairs from right
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        formatted = ','.join(groups) + ',' + last_three

    sign = '-' if is_negative else ''
    return f"₹ {sign}{formatted}{decimal_part}"


def round_amount(value) -> float:
    """Round a monetary value to 2 decimal places."""
    try:
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    except Exception:
        return 0.00


def _get_word_single(n: int) -> str:
    """Return the English word for a single digit (1-9)."""
    words = {
        1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five',
        6: 'Six', 7: 'Seven', 8: 'Eight', 9: 'Nine',
    }
    return words.get(n, '')


def _get_word_teens(n: int) -> str:
    """Return the English word for teens (10-19)."""
    words = {
        10: 'Ten', 11: 'Eleven', 12: 'Twelve', 13: 'Thirteen',
        14: 'Fourteen', 15: 'Fifteen', 16: 'Sixteen', 17: 'Seventeen',
        18: 'Eighteen', 19: 'Nineteen',
    }
    return words.get(n, '')


def _get_word_tens(n: int) -> str:
    """Return the English word for tens (20, 30, ..., 90)."""
    words = {
        2: 'Twenty', 3: 'Thirty', 4: 'Forty', 5: 'Fifty',
        6: 'Sixty', 7: 'Seventy', 8: 'Eighty', 9: 'Ninety',
    }
    return words.get(n, '')


def _two_digit_words(n: int) -> str:
    """Convert a number 0-99 to words."""
    if n == 0:
        return ''
    if n < 10:
        return _get_word_single(n)
    if n < 20:
        return _get_word_teens(n)
    tens = n // 10
    ones = n % 10
    result = _get_word_tens(tens)
    if ones:
        result += ' ' + _get_word_single(ones)
    return result


def _three_digit_words(n: int) -> str:
    """Convert a number 0-999 to words."""
    if n == 0:
        return ''
    hundred = n // 100
    remainder = n % 100
    parts = []
    if hundred:
        parts.append(_get_word_single(hundred) + ' Hundred')
    if remainder:
        parts.append(_two_digit_words(remainder))
    return ' and '.join(parts) if hundred and remainder else ' '.join(parts)


def amount_in_words(amount) -> str:
    """
    Convert a numeric amount to Indian Rupee words.
    Example: 123456.50 -> 'Rupees One Lakh Twenty Three Thousand Four Hundred and Fifty Six and Fifty Paise Only'
    Uses the Indian numbering system: Crore, Lakh, Thousand, Hundred.
    """
    if amount is None:
        return 'Rupees Zero Only'

    try:
        value = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return 'Rupees Zero Only'

    value = abs(value)
    integer_part = int(value)
    paise = int(round((float(value) - integer_part) * 100))

    if integer_part == 0 and paise == 0:
        return 'Rupees Zero Only'

    parts = []

    # Crore (1,00,00,000)
    crore = integer_part // 10000000
    integer_part %= 10000000
    if crore:
        parts.append(_two_digit_words(crore) + ' Crore')

    # Lakh (1,00,000)
    lakh = integer_part // 100000
    integer_part %= 100000
    if lakh:
        parts.append(_two_digit_words(lakh) + ' Lakh')

    # Thousand (1,000)
    thousand = integer_part // 1000
    integer_part %= 1000
    if thousand:
        parts.append(_two_digit_words(thousand) + ' Thousand')

    # Hundreds and remainder
    if integer_part:
        parts.append(_three_digit_words(integer_part))

    rupee_words = 'Rupees ' + ' '.join(parts) if parts else 'Rupees Zero'

    if paise > 0:
        paise_words = _two_digit_words(paise)
        return f"{rupee_words} and {paise_words} Paise Only"
    else:
        return f"{rupee_words} Only"


def get_financial_year(date_str: str = None) -> str:
    """
    Return the financial year string 'YYYY-YY' for a given date.
    Indian FY: April to March. E.g., 2024-25 for dates from Apr 2024 to Mar 2025.
    If date_str is None, uses today's date.
    """
    if date_str:
        try:
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
        except (ValueError, TypeError):
            dt = datetime.now()
    else:
        dt = datetime.now()

    if dt.month >= 4:
        start_year = dt.year
    else:
        start_year = dt.year - 1

    end_year_suffix = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year_suffix}"

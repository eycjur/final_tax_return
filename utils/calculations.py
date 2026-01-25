"""Calculation utilities for the tax return application."""

# 源泉徴収税率（所得税+復興特別所得税）
WITHHOLDING_TAX_RATE_STANDARD = 0.1021  # 10.21%（100万円以下）
WITHHOLDING_TAX_RATE_HIGH = 0.2042      # 20.42%（100万円超）
WITHHOLDING_TAX_THRESHOLD = 1000000     # 100万円

# 許可された通貨
VALID_CURRENCIES = ('JPY', 'USD')


def calculate_jpy_amount(amount: float, currency: str, ttm: float | None = None) -> float:
    """Calculate JPY amount from original currency."""
    if amount < 0:
        raise ValueError('Amount must be non-negative')

    if currency not in VALID_CURRENCIES:
        raise ValueError(f'Unsupported currency: {currency}')

    if currency == 'JPY':
        return amount

    # USD
    if ttm is None or ttm <= 0:
        raise ValueError('TTM is required and must be positive for USD conversion')
    return round(amount * ttm, 0)


def calculate_withholding_tax(amount: float, rate: float | None = None) -> float:
    """
    Calculate withholding tax amount.

    Standard rates (2023年時点):
    - 10.21% for amounts up to 1,000,000 yen
    - 20.42% for amounts over 1,000,000 yen (on the excess)
    """
    if amount < 0:
        raise ValueError("Amount must be non-negative")

    if rate is not None:
        if rate < 0 or rate > 100:
            raise ValueError("Rate must be between 0 and 100")
        return round(amount * rate / 100, 0)

    if amount <= WITHHOLDING_TAX_THRESHOLD:
        return round(amount * WITHHOLDING_TAX_RATE_STANDARD, 0)
    else:
        base_tax = round(WITHHOLDING_TAX_THRESHOLD * WITHHOLDING_TAX_RATE_STANDARD, 0)
        excess_tax = round((amount - WITHHOLDING_TAX_THRESHOLD) * WITHHOLDING_TAX_RATE_HIGH, 0)
        return base_tax + excess_tax


def calculate_prorated_amount(amount: float, proration_rate: float) -> float:
    """Calculate prorated amount based on the proration rate."""
    if amount < 0:
        raise ValueError("Amount must be non-negative")
    if proration_rate < 0 or proration_rate > 100:
        raise ValueError("Proration rate must be between 0 and 100")
    return round(amount * proration_rate / 100, 0)


def get_fiscal_year(date_str: str) -> int:
    """
    Determine fiscal year from date string.

    For Japanese tax purposes, the fiscal year is the calendar year.
    """
    from datetime import datetime
    date = datetime.strptime(date_str, '%Y-%m-%d')
    return date.year


def format_currency(amount: float, show_symbol: bool = True) -> str:
    """Format amount as Japanese yen."""
    formatted = f"{int(amount):,}"
    if show_symbol:
        return f"¥{formatted}"
    return formatted

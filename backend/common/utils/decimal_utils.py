from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


ZERO = Decimal("0")
CENT = Decimal("0.01")
SATOSHI = Decimal("0.00000001")


def money_round(value: Decimal | str | float, places: int = 2) -> Decimal:
    """Round a financial value using ROUND_HALF_UP (standard accounting rounding)."""
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"Cannot convert {value!r} to Decimal")
    quantize_str = Decimal(10) ** -places
    return d.quantize(quantize_str, rounding=ROUND_HALF_UP)


def safe_divide(numerator: Decimal, denominator: Decimal, default: Decimal = ZERO) -> Decimal:
    """Divide two Decimals, returning default when denominator is zero."""
    if denominator == ZERO:
        return default
    return numerator / denominator


def percentage(part: Decimal, total: Decimal, places: int = 2) -> Decimal:
    """Calculate part/total as a percentage, rounded to given decimal places."""
    if total == ZERO:
        return ZERO
    return money_round(safe_divide(part, total) * Decimal("100"), places)

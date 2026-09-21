"""Decimal helpers. Money never touches ``float`` in this codebase."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MONEY = Decimal("0.0001")
RATE = Decimal("0.00000001")
ZERO = Decimal("0")


def to_decimal(value: object) -> Decimal:
    """Coerce a value to :class:`Decimal` without ever passing through float."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value))


def money(value: object) -> Decimal:
    """Quantize to 4 decimal places: the precision used for all monetary values."""
    return to_decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def rate(value: object) -> Decimal:
    """Quantize to 8 decimal places, used for average and unit costs.

    The workbook stores average cost at full division precision (for example
    25500 / 790 = 32.27848101), so costs keep more places than money totals.
    """
    return to_decimal(value).quantize(RATE, rounding=ROUND_HALF_UP)


def is_zero(value: object) -> bool:
    """True when a value quantizes to zero at money precision."""
    return money(value) == ZERO

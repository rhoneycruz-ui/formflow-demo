"""Strict parsing rules for FormFlow numeric fields."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_QUANTITY_PATTERN = re.compile(r"^\d{1,3}$")
_PRICE_PATTERN = re.compile(r"^\d{1,4}(?:[,.]\d{1,2})?$")
_CENT = Decimal("0.01")


def parse_quantity(text: str) -> int:
    normalized = text.strip()
    if not _QUANTITY_PATTERN.fullmatch(normalized):
        raise ValueError("quantity must be an integer from 0 to 999")
    return int(normalized)


def parse_unit_price(text: str) -> Decimal:
    normalized = text.strip()
    if normalized.startswith("R$"):
        normalized = normalized[2:].strip()
    if "," in normalized and "." in normalized:
        raise ValueError("thousands separators are not accepted")
    if not _PRICE_PATTERN.fullmatch(normalized):
        raise ValueError("unit price must be between 0.00 and 9999.99")

    try:
        value = Decimal(normalized.replace(",", ".")).quantize(_CENT)
    except InvalidOperation as error:
        raise ValueError("invalid unit price") from error
    if not Decimal("0.00") <= value <= Decimal("9999.99"):
        raise ValueError("unit price must be between 0.00 and 9999.99")
    return value

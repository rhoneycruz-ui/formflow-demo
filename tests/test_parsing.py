from decimal import Decimal

import pytest

from formflow.parsing import parse_quantity, parse_unit_price


@pytest.mark.parametrize(
    ("text", "expected"),
    [("0", 0), ("007", 7), ("999", 999), (" 42 ", 42)],
)
def test_parse_quantity_accepts_only_bounded_whole_numbers(text: str, expected: int) -> None:
    assert parse_quantity(text) == expected


@pytest.mark.parametrize("text", ["", "-1", "1000", "1.0", "1,0", "1e2", "1 000"])
def test_parse_quantity_rejects_invalid_or_out_of_range_values(text: str) -> None:
    with pytest.raises(ValueError):
        parse_quantity(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("R$ 12,34", Decimal("12.34")),
        ("12.34", Decimal("12.34")),
        ("0,00", Decimal("0.00")),
        ("9999,99", Decimal("9999.99")),
        (" 7 ", Decimal("7.00")),
    ],
)
def test_parse_unit_price_accepts_brazilian_or_point_decimal(
    text: str, expected: Decimal
) -> None:
    assert parse_unit_price(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "R$", "-1,00", "10000", "12,345", "1e2", "1.234,56", "1,234.56"],
)
def test_parse_unit_price_rejects_ambiguous_or_out_of_range_values(text: str) -> None:
    with pytest.raises(ValueError):
        parse_unit_price(text)

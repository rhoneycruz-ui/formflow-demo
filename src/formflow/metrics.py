"""Trustworthy metrics derived exclusively from finalized review state."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from formflow.domain import FieldKey, FieldName, FieldSource
from formflow.template import PRODUCTS
from formflow.validation import ValidatedDocument


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    total_units: int
    order_total: Decimal
    automated_count: int
    reviewed_count: int
    automatic_blank_count: int
    automation_rate: float
    total_time_ms: float


def calculate_summary(document: ValidatedDocument) -> DocumentSummary:
    if not isinstance(document, ValidatedDocument):
        raise TypeError("Metrics require a ValidatedDocument.")

    fields = {field.key: field for field in document.fields}
    total_units = 0
    order_total = Decimal("0.00")
    for product in PRODUCTS:
        quantity = fields[FieldKey(product.product_id, FieldName.QUANTITY)].value
        unit_price = fields[FieldKey(product.product_id, FieldName.UNIT_PRICE)].value
        if quantity is None and unit_price is None:
            continue
        if not isinstance(quantity, int) or not isinstance(unit_price, Decimal):
            raise TypeError("Validated item pairs must contain integer quantity and Decimal price.")
        total_units += quantity
        order_total += Decimal(quantity) * unit_price

    automated_count = sum(field.automated for field in document.fields)
    reviewed_count = sum(field.human_interacted for field in document.fields)
    automatic_blank_count = sum(
        field.automated and field.initial_source is FieldSource.BLANK_AUTO
        for field in document.fields
    )
    return DocumentSummary(
        total_units=total_units,
        order_total=order_total.quantize(Decimal("0.01")),
        automated_count=automated_count,
        reviewed_count=reviewed_count,
        automatic_blank_count=automatic_blank_count,
        automation_rate=automated_count / len(document.fields),
        total_time_ms=float(document.timings_ms.get("total", 0.0)),
    )

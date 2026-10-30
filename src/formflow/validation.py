"""Coverage, pair-completeness and numeric validation for reviewed documents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Protocol

from formflow.domain import EditEvent, FieldKey, FieldName, FieldSource, FieldStatus, FieldValue
from formflow.template import FIELD_LAYOUT, PRODUCTS


class ReviewFieldLike(Protocol):
    key: FieldKey
    raw_text: str
    value: FieldValue
    confidence: float | None
    status: FieldStatus
    initial_source: FieldSource
    final_source: FieldSource
    human_interacted: bool


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    key: FieldKey | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    represented: int
    resolved: int
    pending: int
    unknown: int
    duplicates: int
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return (
            self.represented == len(FIELD_LAYOUT)
            and self.resolved == len(FIELD_LAYOUT)
            and self.pending == 0
            and self.unknown == 0
            and self.duplicates == 0
            and not self.issues
        )


@dataclass(frozen=True, slots=True)
class ValidatedField:
    key: FieldKey
    raw_text: str
    value: FieldValue
    confidence: float | None
    initial_source: FieldSource
    final_source: FieldSource
    human_interacted: bool

    @property
    def automated(self) -> bool:
        return (
            not self.human_interacted
            and self.initial_source in {FieldSource.AUTO, FieldSource.BLANK_AUTO}
        )


@dataclass(frozen=True, slots=True)
class ValidatedDocument:
    document_id: str
    image_sha256: str
    fields: tuple[ValidatedField, ...]
    events: tuple[EditEvent, ...]
    timings_ms: Mapping[str, float]
    finalized_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "timings_ms", MappingProxyType(dict(self.timings_ms)))


class UnresolvedDocumentError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        super().__init__("Document still has unresolved validation issues.")
        self.report = report


def validate_fields(fields: Mapping[FieldKey, ReviewFieldLike]) -> ValidationReport:
    expected = set(FIELD_LAYOUT)
    supplied = set(fields)
    represented = len(expected & supplied)
    unknown_keys = supplied - expected
    issues: list[ValidationIssue] = []

    def order(item: FieldKey) -> tuple[str, str]:
        return item.product_id, item.field_name.value

    for key in sorted(expected - supplied, key=order):
        issues.append(ValidationIssue("missing_field", "Expected field is missing.", key))
    for key in sorted(unknown_keys, key=order):
        issues.append(ValidationIssue("unknown_field", "Unexpected field is present.", key))

    pending = 0
    resolved = 0
    for key in expected & supplied:
        field = fields[key]
        if field.status is FieldStatus.PENDING:
            pending += 1
            issues.append(ValidationIssue("pending", "Field requires human review.", key))
            continue
        resolved += 1
        if field.value is None:
            continue
        if key.field_name is FieldName.QUANTITY:
            invalid_quantity = (
                isinstance(field.value, bool)
                or not isinstance(field.value, int)
                or not 0 <= field.value <= 999
            )
            if invalid_quantity:
                issues.append(
                    ValidationIssue("invalid_quantity", "Quantity is outside 0..999.", key)
                )
        elif not isinstance(field.value, Decimal) or not Decimal("0.00") <= field.value <= Decimal(
            "9999.99"
        ):
            issues.append(
                ValidationIssue(
                    "invalid_price", "Unit price is outside 0.00..9999.99.", key
                )
            )

    for product in PRODUCTS:
        quantity_key = FieldKey(product.product_id, FieldName.QUANTITY)
        price_key = FieldKey(product.product_id, FieldName.UNIT_PRICE)
        if quantity_key not in fields or price_key not in fields:
            continue
        quantity = fields[quantity_key].value
        price = fields[price_key].value
        if (quantity is None) != (price is None):
            issues.append(
                ValidationIssue(
                    "incomplete_pair",
                    "Quantity and unit price must both be filled or both be blank.",
                    quantity_key if quantity is None else price_key,
                )
            )

    return ValidationReport(
        represented=represented,
        resolved=resolved,
        pending=pending,
        unknown=len(unknown_keys),
        duplicates=0,
        issues=tuple(issues),
    )

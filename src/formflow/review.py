"""Auditable human-review mutation boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from types import MappingProxyType

from formflow.domain import (
    DocumentResult,
    EditEvent,
    FieldKey,
    FieldName,
    FieldSource,
    FieldStatus,
    FieldValue,
)
from formflow.parsing import parse_quantity, parse_unit_price
from formflow.template import FIELD_LAYOUT
from formflow.validation import (
    UnresolvedDocumentError,
    ValidatedDocument,
    ValidatedField,
    ValidationReport,
    validate_fields,
)


class UnknownFieldError(KeyError):
    """Raised when a review action targets a field outside the current document."""


class StaleReviewError(RuntimeError):
    """Raised when a caller attempts to mutate an old review revision."""


@dataclass(frozen=True, slots=True)
class ReviewedField:
    key: FieldKey
    raw_text: str
    value: FieldValue
    confidence: float | None
    status: FieldStatus
    initial_source: FieldSource
    final_source: FieldSource
    human_interacted: bool = False
    interactions: int = 0


class ReviewSession:
    def __init__(self, result: DocumentResult) -> None:
        self.document_id = result.document_id
        self.image_sha256 = result.image_sha256
        self.timings_ms = result.timings_ms
        self._fields = {
            observation.key: ReviewedField(
                key=observation.key,
                raw_text=observation.raw_text,
                value=observation.value,
                confidence=observation.confidence,
                status=observation.status,
                initial_source=observation.source,
                final_source=observation.source,
            )
            for observation in result.observations
        }
        self._events: list[EditEvent] = []
        self.revision = 0

    @classmethod
    def from_result(cls, result: DocumentResult) -> ReviewSession:
        return cls(result)

    @property
    def fields(self):
        return MappingProxyType(self._fields)

    @property
    def events(self) -> tuple[EditEvent, ...]:
        return tuple(self._events)

    def _field(self, key: FieldKey, expected_revision: int | None) -> ReviewedField:
        if key not in self._fields or key not in FIELD_LAYOUT:
            raise UnknownFieldError(key)
        if expected_revision is not None and expected_revision != self.revision:
            raise StaleReviewError(
                f"Expected revision {expected_revision}, current revision is {self.revision}."
            )
        return self._fields[key]

    def apply_edit(
        self,
        key: FieldKey,
        text: str,
        at: datetime,
        *,
        expected_revision: int | None = None,
    ) -> None:
        current = self._field(key, expected_revision)
        stripped = text.strip()
        if not stripped:
            value: FieldValue = None
        elif key.field_name is FieldName.QUANTITY:
            value = parse_quantity(stripped)
        else:
            value = parse_unit_price(stripped)
        self._replace_with_human_value(current, value, text, at, "edit")

    def confirm(
        self,
        key: FieldKey,
        at: datetime,
        *,
        expected_revision: int | None = None,
    ) -> None:
        current = self._field(key, expected_revision)
        self._replace_with_human_value(current, current.value, current.raw_text, at, "confirm")

    def _replace_with_human_value(
        self,
        current: ReviewedField,
        value: FieldValue,
        raw_text: str,
        at: datetime,
        action: str,
    ) -> None:
        updated = replace(
            current,
            raw_text=raw_text,
            value=value,
            status=FieldStatus.REVIEWED,
            final_source=FieldSource.HUMAN,
            human_interacted=True,
            interactions=current.interactions + 1,
        )
        self._fields[current.key] = updated
        self._events.append(
            EditEvent(
                key=current.key,
                previous_value=current.value,
                new_value=value,
                at=at,
                action=action,
                initial_source=current.initial_source,
                final_source=FieldSource.HUMAN,
            )
        )
        self.revision += 1

    def validation_report(self) -> ValidationReport:
        return validate_fields(self._fields)

    def finalize(self, at: datetime) -> ValidatedDocument:
        report = self.validation_report()
        if not report.is_valid:
            raise UnresolvedDocumentError(report)
        fields = tuple(
            ValidatedField(
                key=field.key,
                raw_text=field.raw_text,
                value=field.value,
                confidence=field.confidence,
                initial_source=field.initial_source,
                final_source=field.final_source,
                human_interacted=field.human_interacted,
            )
            for key in FIELD_LAYOUT
            for field in (self._fields[key],)
        )
        return ValidatedDocument(
            document_id=self.document_id,
            image_sha256=self.image_sha256,
            fields=fields,
            events=self.events,
            timings_ms=self.timings_ms,
            finalized_at=at,
        )

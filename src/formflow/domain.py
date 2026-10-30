"""Immutable domain types shared by the FormFlow pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import TypeAlias


class FieldName(StrEnum):
    QUANTITY = "quantity"
    UNIT_PRICE = "unit_price"


class FieldStatus(StrEnum):
    AUTO = "auto"
    PENDING = "pending"
    BLANK = "blank"
    REVIEWED = "reviewed"


class FieldSource(StrEnum):
    AUTO = "auto"
    HUMAN = "human"
    BLANK_AUTO = "blank_auto"
    UNRESOLVED = "unresolved"


FieldValue: TypeAlias = int | Decimal | None


@dataclass(frozen=True, slots=True)
class FieldKey:
    product_id: str
    field_name: FieldName

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise ValueError("product_id must not be blank")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("bounding-box origin must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("bounding-box size must be positive")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class OcrReading:
    raw_text: str
    confidence: float

    def __post_init__(self) -> None:
        _validate_confidence(self.confidence)


@dataclass(frozen=True, slots=True)
class FieldObservation:
    key: FieldKey
    bbox: BoundingBox
    raw_text: str
    value: FieldValue
    confidence: float | None
    status: FieldStatus
    source: FieldSource

    def __post_init__(self) -> None:
        if self.confidence is not None:
            _validate_confidence(self.confidence)
        if self.status is FieldStatus.BLANK and self.value is not None:
            raise ValueError("blank fields must preserve value=None")
        if self.source is FieldSource.BLANK_AUTO and self.value is not None:
            raise ValueError("automatic blanks must preserve value=None")


@dataclass(frozen=True, slots=True)
class DocumentResult:
    document_id: str
    image_sha256: str
    observations: tuple[FieldObservation, ...]
    timings_ms: Mapping[str, float]

    def __post_init__(self) -> None:
        keys = [observation.key for observation in self.observations]
        if len(keys) != len(set(keys)):
            raise ValueError("document observations must have unique keys")
        if any(duration < 0 for duration in self.timings_ms.values()):
            raise ValueError("timings must be non-negative")
        object.__setattr__(self, "timings_ms", MappingProxyType(dict(self.timings_ms)))


@dataclass(frozen=True, slots=True)
class EditEvent:
    key: FieldKey
    previous_value: FieldValue
    new_value: FieldValue
    at: datetime
    action: str
    initial_source: FieldSource
    final_source: FieldSource


def _validate_confidence(confidence: float) -> None:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be within 0.0..1.0")

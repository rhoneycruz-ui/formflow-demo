from dataclasses import FrozenInstanceError

import pytest

from formflow.domain import (
    BoundingBox,
    FieldKey,
    FieldName,
    FieldObservation,
    FieldSource,
    FieldStatus,
    OcrReading,
)


def test_bounding_box_rejects_negative_origin_or_empty_size() -> None:
    for args in [(-1, 0, 10, 10), (0, -1, 10, 10), (0, 0, 0, 10), (0, 0, 10, 0)]:
        with pytest.raises(ValueError):
            BoundingBox(*args)


def test_field_key_is_immutable_and_distinguishes_field_names() -> None:
    quantity = FieldKey("P01", FieldName.QUANTITY)
    price = FieldKey("P01", FieldName.UNIT_PRICE)

    assert quantity != price
    with pytest.raises(FrozenInstanceError):
        quantity.product_id = "P02"  # type: ignore[misc]


def test_blank_observation_preserves_none_instead_of_zero() -> None:
    observation = FieldObservation(
        key=FieldKey("P01", FieldName.QUANTITY),
        bbox=BoundingBox(10, 20, 30, 40),
        raw_text="",
        value=None,
        confidence=None,
        status=FieldStatus.BLANK,
        source=FieldSource.BLANK_AUTO,
    )

    assert observation.value is None


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_ocr_reading_rejects_confidence_outside_unit_interval(confidence: float) -> None:
    with pytest.raises(ValueError):
        OcrReading(raw_text="12", confidence=confidence)


def test_field_observation_rejects_confidence_outside_unit_interval() -> None:
    with pytest.raises(ValueError):
        FieldObservation(
            key=FieldKey("P01", FieldName.QUANTITY),
            bbox=BoundingBox(10, 20, 30, 40),
            raw_text="12",
            value=12,
            confidence=2.0,
            status=FieldStatus.AUTO,
            source=FieldSource.AUTO,
        )

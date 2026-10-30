from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from formflow.domain import FieldKey, FieldName, FieldSource, FieldStatus, OcrReading
from formflow.ocr import (
    TesseractNumericOcr,
    TesseractUnavailableError,
    classify_crop,
    ink_occupancy,
)


def _crop_with_ink(value: int = 20) -> np.ndarray:
    crop = np.full((72, 140, 3), 255, dtype=np.uint8)
    crop[24:48, 45:95] = value
    return crop


def test_tesseract_adapter_uses_numeric_configuration_and_normalizes_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_image_to_data(image, **kwargs):
        captured.update(kwargs)
        return {"text": ["", "12,34"], "conf": ["-1", "87"]}

    monkeypatch.setattr("formflow.ocr.pytesseract.image_to_data", fake_image_to_data)
    engine = TesseractNumericOcr(executable="tesseract")

    reading = engine.read(_crop_with_ink(), FieldName.UNIT_PRICE)

    assert reading == OcrReading(raw_text="12,34", confidence=0.87)
    assert "--psm" in str(captured["config"])
    assert "tessedit_char_whitelist" in str(captured["config"])
    assert captured["output_type"] == "dict"


def test_tesseract_adapter_raises_clear_error_when_executable_is_missing() -> None:
    with pytest.raises(TesseractUnavailableError, match="Tesseract"):
        TesseractNumericOcr(executable="Z:/missing/tesseract.exe")


@pytest.mark.parametrize(
    "key,text,expected",
    [
        (FieldKey("P01", FieldName.QUANTITY), "007", 7),
        (FieldKey("P01", FieldName.UNIT_PRICE), "R$ 12,34", Decimal("12.34")),
    ],
)
def test_high_confidence_parseable_ink_becomes_auto(key, text, expected) -> None:
    observation = classify_crop(key, _crop_with_ink(), OcrReading(text, 0.92))

    assert observation.value == expected
    assert observation.status is FieldStatus.AUTO
    assert observation.source is FieldSource.AUTO


def test_true_empty_crop_becomes_automatic_blank_without_zero_coercion() -> None:
    crop = np.full((72, 140, 3), 255, dtype=np.uint8)

    observation = classify_crop(
        FieldKey("P01", FieldName.QUANTITY), crop, OcrReading("", 0.0)
    )

    assert ink_occupancy(crop) == 0.0
    assert observation.value is None
    assert observation.status is FieldStatus.BLANK
    assert observation.source is FieldSource.BLANK_AUTO


@pytest.mark.parametrize(
    "crop,reading",
    [
        (_crop_with_ink(225), OcrReading("", 0.0)),
        (_crop_with_ink(), OcrReading("12", 0.30)),
        (_crop_with_ink(), OcrReading("abc", 0.95)),
        (_crop_with_ink(), OcrReading("", 0.0)),
    ],
)
def test_uncertain_nonempty_crop_becomes_pending(crop, reading) -> None:
    observation = classify_crop(FieldKey("P01", FieldName.QUANTITY), crop, reading)

    assert observation.value is None
    assert observation.status is FieldStatus.PENDING
    assert observation.source is FieldSource.UNRESOLVED

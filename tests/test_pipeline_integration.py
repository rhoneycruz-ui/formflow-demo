from __future__ import annotations

from pathlib import Path

from formflow.domain import FieldName, FieldStatus, OcrReading
from formflow.ocr import TesseractNumericOcr, process_document
from formflow.sample_factory import SampleKind, render_sample


class CountingEngine:
    def __init__(self) -> None:
        self.calls = 0

    def read(self, crop, field_name: FieldName) -> OcrReading:
        del crop
        self.calls += 1
        if self.calls == 4:
            return OcrReading("?", 0.05)
        return OcrReading("2" if field_name is FieldName.QUANTITY else "12,34", 0.98)


def test_clean_sample_produces_sixteen_represented_fields_with_real_tesseract() -> None:
    sample = render_sample(SampleKind.CLEAN, seed=2026)

    result = process_document(sample.image, TesseractNumericOcr())

    assert len(result.observations) == 16
    assert len({observation.key for observation in result.observations}) == 16
    assert all(duration >= 0 for duration in result.timings_ms.values())


def test_injected_ambiguous_reading_is_preserved_as_pending() -> None:
    sample = render_sample(SampleKind.CLEAN, seed=2026)

    result = process_document(sample.image, CountingEngine())

    assert len(result.observations) == 16
    assert any(observation.status is FieldStatus.PENDING for observation in result.observations)


def test_production_modules_do_not_import_sample_ground_truth() -> None:
    source_root = Path(__file__).parents[1] / "src" / "formflow"
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_root.glob("*.py"))

    assert "sample_ground_truth.json" not in source
    assert "tests/fixtures" not in source

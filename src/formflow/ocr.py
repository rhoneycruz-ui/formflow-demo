"""Local numeric OCR and conservative routing for the independent demo."""

from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import pytesseract

from formflow.domain import (
    DocumentResult,
    FieldKey,
    FieldName,
    FieldObservation,
    FieldSource,
    FieldStatus,
    OcrReading,
)
from formflow.image_pipeline import extract_fields, register_form
from formflow.parsing import parse_quantity, parse_unit_price
from formflow.template import FIELD_LAYOUT

# Demo-only thresholds, independently selected for the synthetic FormFlow layout.
AUTO_CONFIDENCE = 0.75
BLANK_INK_OCCUPANCY = 0.003


class TesseractUnavailableError(RuntimeError):
    """Raised when the local OCR executable cannot be found."""


class OcrEngine(Protocol):
    def read(self, crop: np.ndarray, field_name: FieldName) -> OcrReading: ...


def _resolve_tesseract(executable: str | None) -> str:
    if executable:
        requested = Path(executable)
        if requested.is_absolute() or requested.parent != Path("."):
            if requested.is_file():
                return str(requested)
            raise TesseractUnavailableError(f"Tesseract executable not found: {executable}")
        discovered = shutil.which(executable)
        if discovered:
            return discovered

    discovered = shutil.which("tesseract")
    if discovered:
        return discovered
    windows_default = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if windows_default.is_file() and executable in {None, "tesseract"}:
        return str(windows_default)
    raise TesseractUnavailableError(
        "Tesseract OCR is not installed or is unavailable on PATH."
    )


class TesseractNumericOcr:
    """Thin local-only Tesseract adapter with a numeric whitelist."""

    def __init__(self, executable: str | None = None) -> None:
        self.executable = _resolve_tesseract(executable)

    def read(self, crop: np.ndarray, field_name: FieldName) -> OcrReading:
        del field_name  # Both public demo fields share the strict numeric alphabet.
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY) if crop.ndim == 3 else crop
        inner = gray[7:-7, 7:-7] if min(gray.shape[:2]) > 20 else gray
        enlarged = cv2.resize(inner, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        binary = cv2.threshold(enlarged, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        config = "--psm 7 -c tessedit_char_whitelist=0123456789,.$R "
        pytesseract.pytesseract.tesseract_cmd = self.executable
        data = pytesseract.image_to_data(
            binary,
            config=config,
            output_type=pytesseract.Output.DICT,
        )

        tokens: list[str] = []
        confidences: list[float] = []
        for text, raw_confidence in zip(data.get("text", []), data.get("conf", []), strict=False):
            token = str(text).strip()
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                confidence = -1.0
            if token:
                tokens.append(token)
                if confidence >= 0:
                    confidences.append(confidence)

        raw_text = " ".join(tokens).strip()
        normalized = max(confidences, default=0.0) / 100.0
        return OcrReading(raw_text=raw_text, confidence=min(max(normalized, 0.0), 1.0))


def ink_occupancy(crop: np.ndarray) -> float:
    """Estimate visible marks while excluding the synthetic field border."""
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY) if crop.ndim == 3 else crop
    inner = gray[8:-8, 8:-8] if min(gray.shape[:2]) > 20 else gray
    if inner.size == 0:
        return 0.0
    return float(np.count_nonzero(inner < 245) / inner.size)


def classify_crop(
    key: FieldKey,
    crop: np.ndarray,
    reading: OcrReading,
) -> FieldObservation:
    """Represent every field as automatic, blank or explicitly pending."""
    occupancy = ink_occupancy(crop)
    if occupancy <= BLANK_INK_OCCUPANCY and not reading.raw_text.strip():
        return FieldObservation(
            key=key,
            bbox=FIELD_LAYOUT[key],
            raw_text=reading.raw_text,
            value=None,
            confidence=reading.confidence,
            status=FieldStatus.BLANK,
            source=FieldSource.BLANK_AUTO,
        )

    parser = parse_quantity if key.field_name is FieldName.QUANTITY else parse_unit_price
    try:
        value = parser(reading.raw_text)
    except ValueError:
        value = None

    if value is not None and reading.confidence >= AUTO_CONFIDENCE:
        return FieldObservation(
            key=key,
            bbox=FIELD_LAYOUT[key],
            raw_text=reading.raw_text,
            value=value,
            confidence=reading.confidence,
            status=FieldStatus.AUTO,
            source=FieldSource.AUTO,
        )
    return FieldObservation(
        key=key,
        bbox=FIELD_LAYOUT[key],
        raw_text=reading.raw_text,
        value=None,
        confidence=reading.confidence,
        status=FieldStatus.PENDING,
        source=FieldSource.UNRESOLVED,
    )


def process_document(image, engine: OcrEngine) -> DocumentResult:
    """Register, extract and classify all fields without consulting Ground Truth."""
    started = time.perf_counter()
    registration_started = time.perf_counter()
    registered = register_form(image)
    registration_ms = (time.perf_counter() - registration_started) * 1000

    crops = extract_fields(registered)
    ocr_started = time.perf_counter()
    observations = tuple(
        classify_crop(key, crop, engine.read(crop, key.field_name))
        for key, crop in crops.items()
    )
    ocr_ms = (time.perf_counter() - ocr_started) * 1000
    total_ms = (time.perf_counter() - started) * 1000
    digest = hashlib.sha256(np.asarray(image.convert("RGB")).tobytes()).hexdigest()
    return DocumentResult(
        document_id=f"ff-{digest[:12]}",
        image_sha256=digest,
        observations=observations,
        timings_ms={
            "registration": registration_ms,
            "ocr": ocr_ms,
            "total": total_ms,
        },
    )

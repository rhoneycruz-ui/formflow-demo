"""Bounded image decoding, synthetic marker registration and field extraction."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from formflow.domain import FieldKey
from formflow.template import FIELD_LAYOUT, FORM_SIZE, REGISTRATION_MARKERS

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class InvalidUploadError(ValueError):
    """Raised when uploaded bytes violate the public input contract."""


class IncompatibleFormError(ValueError):
    """Raised when the independent FormFlow markers cannot be registered."""


@dataclass(frozen=True, slots=True)
class RegisteredForm:
    image: Image.Image
    marker_centers: tuple[tuple[float, float], ...]


def validate_upload(data: bytes, filename: str) -> Image.Image:
    """Decode one bounded JPEG/PNG from content, normalize EXIF and return RGB pixels."""
    del filename  # File names are untrusted metadata; content is authoritative.
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise InvalidUploadError("Upload must be no larger than 10 MB.")
    if not (data.startswith(_PNG_SIGNATURE) or data.startswith(b"\xff\xd8\xff")):
        raise InvalidUploadError("Only JPEG and PNG images are supported.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source = Image.open(BytesIO(data))
            if source.format not in {"JPEG", "PNG"}:
                raise InvalidUploadError("Only JPEG and PNG images are supported.")
            if getattr(source, "n_frames", 1) != 1:
                raise InvalidUploadError("Upload must be a single-frame image.")

            normalized = ImageOps.exif_transpose(source)
            width, height = normalized.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise InvalidUploadError("Image must contain at most 20 megapixels.")
            normalized.load()
            return normalized.convert("RGB")
    except InvalidUploadError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise InvalidUploadError("Image dimensions are unsafe.") from exc
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise InvalidUploadError("Image bytes are invalid or incomplete.") from exc


def _marker_candidates(image: Image.Image) -> list[tuple[float, float]]:
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    dark = cv2.inRange(gray, 0, 105)
    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[tuple[float, float]] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if not (35 <= width <= 95 and 35 <= height <= 95):
            continue
        if not 0.72 <= width / height <= 1.28:
            continue
        if cv2.contourArea(contour) < 1_250:
            continue
        candidates.append((x + width / 2.0, y + height / 2.0))
    return candidates


def _ordered_markers(image: Image.Image) -> tuple[tuple[float, float], ...]:
    width, height = image.size
    buckets: list[list[tuple[float, float]]] = [[], [], [], []]
    for center in _marker_candidates(image):
        x, y = center
        if x < width * 0.25 and y < height * 0.25:
            buckets[0].append(center)
        elif x > width * 0.75 and y < height * 0.25:
            buckets[1].append(center)
        elif x < width * 0.25 and y > height * 0.75:
            buckets[2].append(center)
        elif x > width * 0.75 and y > height * 0.75:
            buckets[3].append(center)

    if any(len(bucket) != 1 for bucket in buckets):
        raise IncompatibleFormError("Expected four unique FormFlow registration markers.")
    return tuple(bucket[0] for bucket in buckets)


def register_form(image: Image.Image) -> RegisteredForm:
    """Rectify a FormFlow image using its four independent square markers."""
    if image.width < 200 or image.height < 200:
        raise IncompatibleFormError("Image is too small to contain the FormFlow template.")

    source_centers = _ordered_markers(image)
    target_centers = tuple(
        (
            marker.x + marker.width / 2.0,
            marker.y + marker.height / 2.0,
        )
        for marker in REGISTRATION_MARKERS.values()
    )
    transform = cv2.getPerspectiveTransform(
        np.asarray(source_centers, dtype=np.float32),
        np.asarray(target_centers, dtype=np.float32),
    )
    registered = cv2.warpPerspective(
        np.asarray(image.convert("RGB")),
        transform,
        FORM_SIZE,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(248, 250, 252),
    )
    return RegisteredForm(Image.fromarray(registered, mode="RGB"), source_centers)


def extract_fields(form: RegisteredForm) -> dict[FieldKey, np.ndarray]:
    """Return independent copies of all 16 registered field crops."""
    pixels = np.asarray(form.image.convert("RGB"))
    return {
        key: pixels[box.y : box.bottom, box.x : box.right].copy()
        for key, box in FIELD_LAYOUT.items()
    }

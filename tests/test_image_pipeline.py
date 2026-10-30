from __future__ import annotations

import struct
import zlib
from io import BytesIO

import numpy as np
import pytest
from PIL import Image, ImageDraw

from formflow.image_pipeline import (
    IncompatibleFormError,
    InvalidUploadError,
    extract_fields,
    register_form,
    validate_upload,
)
from formflow.sample_factory import SampleKind, render_sample
from formflow.template import FIELD_LAYOUT, FORM_SIZE, REGISTRATION_MARKERS, render_blank_form


def _encoded(image: Image.Image, format_name: str, **kwargs: object) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=format_name, **kwargs)
    return buffer.getvalue()


def _png_with_dimensions(width: int, height: int) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return signature + chunk(b"IHDR", header) + chunk(b"IEND", b"")


@pytest.mark.parametrize("format_name", ["PNG", "JPEG"])
def test_validate_upload_accepts_png_and_jpeg_by_content(format_name: str) -> None:
    data = _encoded(Image.new("RGB", (40, 30), "white"), format_name)

    image = validate_upload(data, "misleading-name.bin")

    assert image.mode == "RGB"
    assert image.size == (40, 30)


@pytest.mark.parametrize(
    "data,filename",
    [
        (b"not an image", "photo.png"),
        (_encoded(Image.new("RGB", (20, 20)), "GIF"), "photo.gif"),
        (b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024), "large.png"),
        (_png_with_dimensions(5000, 4001), "oversized.png"),
    ],
)
def test_validate_upload_rejects_invalid_type_or_size(data: bytes, filename: str) -> None:
    with pytest.raises(InvalidUploadError):
        validate_upload(data, filename)


def test_validate_upload_rejects_multiframe_png() -> None:
    first = Image.new("RGB", (20, 20), "white")
    second = Image.new("RGB", (20, 20), "black")
    data = _encoded(first, "PNG", save_all=True, append_images=[second], duration=100)

    with pytest.raises(InvalidUploadError, match="single-frame"):
        validate_upload(data, "animated.png")


def test_validate_upload_applies_exif_orientation() -> None:
    image = Image.new("RGB", (40, 20), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 19, 19), fill="red")
    exif = Image.Exif()
    exif[274] = 6

    normalized = validate_upload(_encoded(image, "JPEG", exif=exif), "rotated.jpg")

    assert normalized.size == (20, 40)
    pixels = np.asarray(normalized)
    assert pixels[:20, :, 1].mean() < pixels[20:, :, 1].mean()


@pytest.mark.parametrize("kind", [SampleKind.CLEAN, SampleKind.NOISY])
def test_register_form_and_extract_all_fields(kind: SampleKind) -> None:
    sample = render_sample(kind, seed=2026)

    registered = register_form(sample.image)
    crops = extract_fields(registered)

    assert registered.image.size == FORM_SIZE
    assert set(crops) == set(FIELD_LAYOUT)
    assert len(crops) == 16
    assert all(crop.size > 0 for crop in crops.values())


def test_register_form_handles_small_rotation() -> None:
    rotated = render_sample(SampleKind.CLEAN, seed=2026).image.rotate(1.5, fillcolor="#e2e8f0")

    registered = register_form(rotated)

    assert registered.image.size == FORM_SIZE


def test_register_form_rejects_missing_marker_without_partial_result() -> None:
    image = render_blank_form()
    draw = ImageDraw.Draw(image)
    marker = REGISTRATION_MARKERS["top_left"]
    draw.rectangle((marker.x - 2, marker.y - 2, marker.right + 2, marker.bottom + 2), fill="white")

    with pytest.raises(IncompatibleFormError, match="four unique"):
        register_form(image)


def test_register_form_rejects_duplicate_marker_in_corner() -> None:
    image = render_blank_form()
    marker = REGISTRATION_MARKERS["top_left"]
    duplicate = image.crop((marker.x, marker.y, marker.right, marker.bottom))
    image.paste(duplicate, (40, 200))

    with pytest.raises(IncompatibleFormError, match="four unique"):
        register_form(image)

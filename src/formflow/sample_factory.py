"""Deterministic generator for the public synthetic FormFlow samples."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from formflow.domain import FieldKey, FieldName
from formflow.template import FIELD_LAYOUT, FORM_SIZE, PRODUCTS, render_blank_form


class SampleKind(StrEnum):
    CLEAN = "clean"
    NOISY = "noisy"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class GeneratedSample:
    image: Image.Image
    ground_truth: Mapping[FieldKey, str | None]
    ambiguous_keys: tuple[FieldKey, ...]


def _value_font(size: int = 38) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _draw_centered_value(draw: ImageDraw.ImageDraw, key: FieldKey, value: str) -> None:
    box = FIELD_LAYOUT[key]
    font = _value_font()
    bounds = draw.textbbox((0, 0), value, font=font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    x = box.x + (box.width - width) // 2
    y = box.y + (box.height - height) // 2 - 3
    draw.text((x, y), value, font=font, fill="#111827")


def _apply_noisy_photo(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    source = np.asarray(image)
    width, height = FORM_SIZE
    shift = rng.integers(12, 30, size=8).astype(np.float32)
    source_points = np.float32([[0, 0], [width - 1, 0], [0, height - 1], [width - 1, height - 1]])
    target_points = np.float32(
        [
            [shift[0], shift[1]],
            [width - 1 - shift[2], shift[3]],
            [shift[4], height - 1 - shift[5]],
            [width - 1 - shift[6], height - 1 - shift[7]],
        ]
    )
    matrix = cv2.getPerspectiveTransform(source_points, target_points)
    warped = cv2.warpPerspective(source, matrix, (width, height), borderValue=(226, 232, 240))

    gradient = np.linspace(0.88, 1.04, width, dtype=np.float32)[None, :, None]
    shaded = np.clip(warped.astype(np.float32) * gradient, 0, 255).astype(np.uint8)
    noise = rng.normal(0, 2.2, shaded.shape).astype(np.int16)
    noisy = np.clip(shaded.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy, mode="RGB").filter(ImageFilter.GaussianBlur(radius=0.35))


def render_sample(kind: SampleKind, seed: int) -> GeneratedSample:
    rng = np.random.default_rng(seed)
    image = render_blank_form()
    draw = ImageDraw.Draw(image)
    ground_truth: dict[FieldKey, str | None] = {}

    for product in PRODUCTS:
        quantity_key = FieldKey(product.product_id, FieldName.QUANTITY)
        price_key = FieldKey(product.product_id, FieldName.UNIT_PRICE)
        quantity = str(int(rng.integers(1, 80)))
        price = f"{int(rng.integers(125, 8999)) / 100:.2f}".replace(".", ",")
        ground_truth[quantity_key] = quantity
        ground_truth[price_key] = price
        _draw_centered_value(draw, quantity_key, quantity)
        _draw_centered_value(draw, price_key, price)

    ambiguous_keys: tuple[FieldKey, ...] = ()
    if kind is SampleKind.NOISY:
        image = _apply_noisy_photo(image, rng)
    elif kind is SampleKind.REVIEW:
        ambiguous_key = FieldKey("P04", FieldName.QUANTITY)
        ambiguous_keys = (ambiguous_key,)
        box = FIELD_LAYOUT[ambiguous_key]
        draw = ImageDraw.Draw(image)
        draw.line(
            (box.x + 20, box.y + box.height // 2, box.right - 18, box.y + box.height // 2 + 5),
            fill="#334e68",
            width=9,
        )
        draw.line((box.x + 42, box.y + 10, box.x + 88, box.bottom - 8), fill="#111827", width=7)

    return GeneratedSample(
        image=image,
        ground_truth=MappingProxyType(ground_truth),
        ambiguous_keys=ambiguous_keys,
    )

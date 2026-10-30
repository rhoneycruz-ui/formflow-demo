from itertools import combinations

import numpy as np
from PIL import ImageFont

from formflow.domain import FieldName
from formflow.template import (
    FIELD_LAYOUT,
    FONT_PATH,
    FORM_SIZE,
    PRODUCTS,
    REGISTRATION_MARKERS,
    render_blank_form,
)


def test_bundled_font_supports_portuguese_accents() -> None:
    font = ImageFont.truetype(str(FONT_PATH), 24)

    assert FONT_PATH.is_file()
    assert bytes(font.getmask("çãé")) != bytes(font.getmask("□□□"))


def _overlap_area(first, second) -> int:
    width = max(0, min(first.right, second.right) - max(first.x, second.x))
    height = max(0, min(first.bottom, second.bottom) - max(first.y, second.y))
    return width * height


def test_template_has_eight_unique_fictional_products_and_sixteen_fields() -> None:
    assert len(PRODUCTS) == 8
    assert len({product.product_id for product in PRODUCTS}) == 8
    assert len({product.name for product in PRODUCTS}) == 8
    expected_ids = [f"P{number:02d}" for number in range(1, 9)]
    assert [product.product_id for product in PRODUCTS] == expected_ids
    assert set(key.field_name for key in FIELD_LAYOUT) == {
        FieldName.QUANTITY,
        FieldName.UNIT_PRICE,
    }
    assert len(FIELD_LAYOUT) == 16


def test_template_fields_are_inside_canvas_and_do_not_overlap() -> None:
    canvas_width, canvas_height = FORM_SIZE
    boxes = list(FIELD_LAYOUT.values())

    assert all(box.right <= canvas_width and box.bottom <= canvas_height for box in boxes)
    assert all(_overlap_area(first, second) == 0 for first, second in combinations(boxes, 2))


def test_template_has_four_unique_corner_markers() -> None:
    assert set(REGISTRATION_MARKERS) == {"top_left", "top_right", "bottom_left", "bottom_right"}
    assert len(set(REGISTRATION_MARKERS.values())) == 4


def test_blank_form_uses_the_declared_canvas_size() -> None:
    image = render_blank_form()

    assert image.mode == "RGB"
    assert image.size == FORM_SIZE


def test_blank_form_header_uses_readable_large_type_when_system_fonts_are_missing() -> None:
    pixels = np.asarray(render_blank_form())
    header_text = pixels[80:190, 150:900]
    bright_rows = np.flatnonzero((header_text > 225).all(axis=2).sum(axis=1) >= 5)

    assert bright_rows[-1] - bright_rows[0] >= 24

"""Independent synthetic FormFlow order-form template."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from PIL import Image, ImageDraw, ImageFont

from formflow.domain import BoundingBox, FieldKey, FieldName

FORM_SIZE = (1240, 1754)
FONT_PATH = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Inter-Variable.ttf"


@dataclass(frozen=True, slots=True)
class Product:
    product_id: str
    name: str
    unit: str


PRODUCTS = (
    Product("P01", "Café Horizonte", "250 g"),
    Product("P02", "Chá Brisa", "20 sachês"),
    Product("P03", "Biscoito Pétala", "180 g"),
    Product("P04", "Farinha Campo Azul", "1 kg"),
    Product("P05", "Açúcar Estelar", "1 kg"),
    Product("P06", "Óleo Dourado", "900 ml"),
    Product("P07", "Arroz Serra Clara", "1 kg"),
    Product("P08", "Feijão Colina", "1 kg"),
)

REGISTRATION_MARKERS = MappingProxyType(
    {
        "top_left": BoundingBox(56, 56, 54, 54),
        "top_right": BoundingBox(1130, 56, 54, 54),
        "bottom_left": BoundingBox(56, 1644, 54, 54),
        "bottom_right": BoundingBox(1130, 1644, 54, 54),
    }
)

_ROW_TOP = 510
_ROW_HEIGHT = 118
_QUANTITY_X = 800
_PRICE_X = 980
_FIELD_HEIGHT = 72

FIELD_LAYOUT = MappingProxyType(
    {
        FieldKey(product.product_id, field_name): BoundingBox(
            _QUANTITY_X if field_name is FieldName.QUANTITY else _PRICE_X,
            _ROW_TOP + index * _ROW_HEIGHT + 20,
            140 if field_name is FieldName.QUANTITY else 180,
            _FIELD_HEIGHT,
        )
        for index, product in enumerate(PRODUCTS)
        for field_name in (FieldName.QUANTITY, FieldName.UNIT_PRICE)
    }
)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        font = ImageFont.truetype(str(FONT_PATH), size)
        if bold:
            font.set_variation_by_name("Bold")
        return font
    except OSError:
        return ImageFont.load_default(size=size)


def _draw_marker(draw: ImageDraw.ImageDraw, box: BoundingBox, *, anchor: bool) -> None:
    draw.rectangle((box.x, box.y, box.right, box.bottom), fill="#102a43")
    draw.rectangle((box.x + 11, box.y + 11, box.right - 11, box.bottom - 11), fill="white")
    inset = 14 if anchor else 20
    draw.rectangle(
        (box.x + inset, box.y + inset, box.right - inset, box.bottom - inset),
        fill="#102a43",
    )


def render_blank_form() -> Image.Image:
    image = Image.new("RGB", FORM_SIZE, "#f8fafc")
    draw = ImageDraw.Draw(image)

    for name, marker in REGISTRATION_MARKERS.items():
        _draw_marker(draw, marker, anchor=name == "top_left")

    draw.rounded_rectangle((145, 65, 1095, 210), radius=24, fill="#0f4c5c")
    draw.text((190, 92), "FORMFLOW", font=_font(44, bold=True), fill="white")
    draw.text((190, 150), "PEDIDO OPERACIONAL — DADOS SINTÉTICOS", font=_font(22), fill="#d8f3dc")

    draw.text((145, 255), "Distribuidora Aurora Demo", font=_font(30, bold=True), fill="#102a43")
    draw.text(
        (145, 305),
        "Documento fictício criado exclusivamente para demonstração.",
        font=_font(20),
        fill="#486581",
    )
    draw.rounded_rectangle((145, 360, 1095, 438), radius=12, outline="#9fb3c8", width=3)
    draw.text((170, 384), "PEDIDO Nº: FF-2026-001", font=_font(20, bold=True), fill="#243b53")
    draw.text((650, 384), "DATA: ____ / ____ / ______", font=_font(20), fill="#243b53")

    draw.rectangle((145, 470, 1095, 510), fill="#d9e2ec")
    draw.text((170, 478), "PRODUTO", font=_font(18, bold=True), fill="#102a43")
    draw.text((810, 478), "QUANT.", font=_font(18, bold=True), fill="#102a43")
    draw.text((990, 478), "PREÇO UNIT.", font=_font(18, bold=True), fill="#102a43")

    for index, product in enumerate(PRODUCTS):
        row_y = _ROW_TOP + index * _ROW_HEIGHT
        fill = "white" if index % 2 == 0 else "#f0f4f8"
        draw.rectangle(
            (145, row_y, 1095, row_y + _ROW_HEIGHT),
            fill=fill,
            outline="#bcccdc",
            width=2,
        )
        draw.text((170, row_y + 30), product.name, font=_font(22, bold=True), fill="#102a43")
        draw.text((540, row_y + 34), product.unit, font=_font(18), fill="#486581")
        for field_name in (FieldName.QUANTITY, FieldName.UNIT_PRICE):
            box = FIELD_LAYOUT[FieldKey(product.product_id, field_name)]
            draw.rounded_rectangle(
                (box.x, box.y, box.right, box.bottom),
                radius=8,
                fill="white",
                outline="#829ab1",
                width=3,
            )

    footer_y = _ROW_TOP + len(PRODUCTS) * _ROW_HEIGHT + 38
    draw.text(
        (145, footer_y),
        "Conferido por: ______________________________",
        font=_font(20),
        fill="#486581",
    )
    draw.text(
        (145, footer_y + 54),
        "FormFlow Demo · Nenhum dado real é utilizado",
        font=_font(18),
        fill="#627d98",
    )
    return image

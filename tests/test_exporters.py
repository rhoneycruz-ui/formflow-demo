from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO, StringIO

import openpyxl
import pytest

from formflow.domain import FieldKey, FieldName
from formflow.exporters import to_audit_json, to_csv, to_xlsx
from formflow.review import ReviewSession
from tests.test_review import make_result

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _document_with_blank_and_edit():
    session = ReviewSession.from_result(make_result())
    session.apply_edit(FieldKey("P01", FieldName.QUANTITY), "7", NOW)
    session.apply_edit(FieldKey("P08", FieldName.QUANTITY), "", NOW)
    session.apply_edit(FieldKey("P08", FieldName.UNIT_PRICE), "", NOW)
    return session.finalize(NOW)


def test_csv_round_trip_preserves_order_numbers_and_absent_blanks() -> None:
    payload = to_csv(_document_with_blank_and_edit())
    rows = list(csv.DictReader(StringIO(payload.decode("utf-8"))))

    assert len(rows) == 8
    assert [row["product_id"] for row in rows] == [f"P{index:02d}" for index in range(1, 9)]
    assert rows[0]["quantity"] == "7"
    assert Decimal(rows[0]["unit_price"]) == Decimal("3.50")
    assert rows[-1]["quantity"] == ""
    assert rows[-1]["unit_price"] == ""


def test_xlsx_round_trip_has_numeric_cells_and_money_formats() -> None:
    workbook = openpyxl.load_workbook(BytesIO(to_xlsx(_document_with_blank_and_edit())))
    sheet = workbook["Itens"]

    assert sheet.max_row == 9
    assert sheet["D2"].value == 7
    assert sheet["E2"].value == 3.5
    assert sheet["E2"].number_format == 'R$ #,##0.00'
    assert sheet["D9"].value is None
    assert sheet["E9"].value is None


def test_audit_json_preserves_nulls_sources_events_and_timestamps() -> None:
    payload = to_audit_json(_document_with_blank_and_edit())
    decoded = json.loads(payload.decode("utf-8"))
    fields = {(field["product_id"], field["field_name"]): field for field in decoded["fields"]}

    assert len(fields) == 16
    assert fields[("P08", "quantity")]["value"] is None
    assert fields[("P01", "quantity")]["initial_source"] == "auto"
    assert fields[("P01", "quantity")]["final_source"] == "human"
    assert decoded["events"][0]["at"] == NOW.isoformat()
    serialized = payload.decode("utf-8")
    assert "image_bytes" not in serialized
    assert "C:\\" not in serialized


@pytest.mark.parametrize("exporter", [to_csv, to_xlsx, to_audit_json])
def test_exporters_refuse_mutable_sessions(exporter) -> None:
    with pytest.raises(TypeError, match="ValidatedDocument"):
        exporter(ReviewSession.from_result(make_result()))

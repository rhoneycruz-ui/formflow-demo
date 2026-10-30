from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from formflow.domain import FieldKey, FieldName, FieldSource
from formflow.review import ReviewSession
from formflow.validation import UnresolvedDocumentError, ValidatedDocument, ValidatedField
from tests.test_review import make_result

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def test_complete_document_has_full_coverage_and_can_finalize() -> None:
    session = ReviewSession.from_result(make_result())

    report = session.validation_report()
    document = session.finalize(NOW)

    assert report.represented == 16
    assert report.resolved == 16
    assert report.pending == 0
    assert report.is_valid
    assert len(document.fields) == 16


def test_pending_field_blocks_finalization() -> None:
    key = FieldKey("P03", FieldName.QUANTITY)
    session = ReviewSession.from_result(make_result(pending_key=key))

    report = session.validation_report()

    assert report.pending == 1
    assert not report.is_valid
    with pytest.raises(UnresolvedDocumentError):
        session.finalize(NOW)


def test_half_filled_item_blocks_finalization_and_totals() -> None:
    session = ReviewSession.from_result(make_result())
    session.apply_edit(FieldKey("P04", FieldName.UNIT_PRICE), "", NOW)

    report = session.validation_report()

    assert not report.is_valid
    assert any(issue.code == "incomplete_pair" for issue in report.issues)
    with pytest.raises(UnresolvedDocumentError):
        session.finalize(NOW)


def test_both_blank_item_remains_none_and_is_valid() -> None:
    session = ReviewSession.from_result(make_result())
    quantity = FieldKey("P05", FieldName.QUANTITY)
    price = FieldKey("P05", FieldName.UNIT_PRICE)

    session.apply_edit(quantity, "", NOW)
    session.apply_edit(price, "", NOW)
    document = session.finalize(NOW)
    values = {field.key: field.value for field in document.fields}

    assert values[quantity] is None
    assert values[price] is None


def test_unknown_field_is_reported_and_blocks_finalization() -> None:
    result = make_result()
    session = ReviewSession.from_result(result)
    session._fields[FieldKey("P99", FieldName.QUANTITY)] = next(iter(session._fields.values()))

    report = session.validation_report()

    assert report.unknown == 1
    assert not report.is_valid


def test_validated_document_rejects_incomplete_direct_construction() -> None:
    field = ValidatedField(
        key=FieldKey("P01", FieldName.QUANTITY),
        raw_text="2",
        value=2,
        confidence=0.99,
        initial_source=FieldSource.AUTO,
        final_source=FieldSource.AUTO,
        human_interacted=False,
    )

    with pytest.raises(ValueError, match="exactly 16"):
        ValidatedDocument(
            document_id="invalid",
            image_sha256="a" * 64,
            fields=(field,),
            events=(),
            timings_ms=MappingProxyType({"total": 1.0}),
            finalized_at=NOW,
        )

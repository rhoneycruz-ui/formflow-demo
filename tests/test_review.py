from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from formflow.domain import (
    DocumentResult,
    FieldKey,
    FieldName,
    FieldObservation,
    FieldSource,
    FieldStatus,
)
from formflow.review import ReviewSession, StaleReviewError, UnknownFieldError
from formflow.template import FIELD_LAYOUT

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def make_result(*, pending_key: FieldKey | None = None) -> DocumentResult:
    observations = []
    for key, bbox in FIELD_LAYOUT.items():
        pending = key == pending_key
        value = None if pending else (
            2 if key.field_name is FieldName.QUANTITY else Decimal("3.50")
        )
        observations.append(
            FieldObservation(
                key=key,
                bbox=bbox,
                raw_text="?" if pending else str(value),
                value=value,
                confidence=0.1 if pending else 0.98,
                status=FieldStatus.PENDING if pending else FieldStatus.AUTO,
                source=FieldSource.UNRESOLVED if pending else FieldSource.AUTO,
            )
        )
    return DocumentResult("doc-1", "a" * 64, tuple(observations), {"total": 10.0})


def test_session_keeps_all_fields_and_allows_editing_automatic_values() -> None:
    session = ReviewSession.from_result(make_result())
    key = FieldKey("P01", FieldName.QUANTITY)

    session.apply_edit(key, "7", NOW)

    field = session.fields[key]
    assert len(session.fields) == 16
    assert field.value == 7
    assert field.initial_source is FieldSource.AUTO
    assert field.final_source is FieldSource.HUMAN
    assert field.status is FieldStatus.REVIEWED
    assert session.events[-1].previous_value == 2
    assert session.events[-1].new_value == 7
    assert session.events[-1].initial_source is FieldSource.AUTO
    assert session.events[-1].final_source is FieldSource.HUMAN


def test_confirm_records_human_interaction_for_pending_or_blank() -> None:
    key = FieldKey("P02", FieldName.UNIT_PRICE)
    session = ReviewSession.from_result(make_result(pending_key=key))

    session.confirm(key, NOW)

    assert session.fields[key].value is None
    assert session.fields[key].human_interacted
    assert session.fields[key].status is FieldStatus.REVIEWED
    assert session.events[-1].action == "confirm"


def test_unknown_and_stale_edits_are_rejected() -> None:
    session = ReviewSession.from_result(make_result())
    key = FieldKey("P01", FieldName.QUANTITY)

    with pytest.raises(UnknownFieldError):
        session.apply_edit(FieldKey("P99", FieldName.QUANTITY), "1", NOW)
    with pytest.raises(StaleReviewError):
        session.apply_edit(key, "1", NOW, expected_revision=5)


def test_new_session_resets_revision_and_does_not_share_mutation() -> None:
    result = make_result()
    first = ReviewSession.from_result(result)
    second = ReviewSession.from_result(result)
    key = FieldKey("P01", FieldName.QUANTITY)

    first.apply_edit(key, "8", NOW)

    assert first.revision == 1
    assert second.revision == 0
    assert second.fields[key].value == 2


def test_editing_auto_field_removes_it_from_automation_but_preserves_provenance() -> None:
    session = ReviewSession.from_result(make_result())
    untouched = FieldKey("P01", FieldName.QUANTITY)
    edited = FieldKey("P02", FieldName.QUANTITY)

    session.apply_edit(edited, "9", NOW)
    document = session.finalize(NOW)
    fields = {field.key: field for field in document.fields}

    assert fields[untouched].automated
    assert not fields[edited].automated
    assert fields[edited].initial_source is FieldSource.AUTO
    assert fields[edited].final_source is FieldSource.HUMAN

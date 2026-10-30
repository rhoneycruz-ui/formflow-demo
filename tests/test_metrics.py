from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from formflow.domain import FieldKey, FieldName
from formflow.metrics import calculate_summary
from formflow.review import ReviewSession
from tests.test_review import make_result

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def test_summary_uses_only_finalized_values_and_provenance() -> None:
    session = ReviewSession.from_result(make_result())
    session.apply_edit(FieldKey("P01", FieldName.QUANTITY), "4", NOW)
    session.apply_edit(FieldKey("P02", FieldName.QUANTITY), "", NOW)
    session.apply_edit(FieldKey("P02", FieldName.UNIT_PRICE), "", NOW)
    document = session.finalize(NOW)

    summary = calculate_summary(document)

    assert summary.total_units == 16
    assert summary.order_total == Decimal("56.00")
    assert summary.automated_count == 13
    assert summary.reviewed_count == 3
    assert summary.automatic_blank_count == 0
    assert summary.automation_rate == pytest.approx(13 / 16)
    assert summary.total_time_ms == 10.0


def test_metrics_refuse_mutable_review_sessions() -> None:
    session = ReviewSession.from_result(make_result())

    with pytest.raises(TypeError, match="ValidatedDocument"):
        calculate_summary(session)  # type: ignore[arg-type]


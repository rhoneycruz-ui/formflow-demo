from __future__ import annotations

from datetime import UTC, datetime

import pytest

from formflow.app_state import AppPhase, InvalidPhaseTransition, SessionController
from formflow.review import ReviewSession
from tests.test_review import make_result

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def test_controller_allows_only_select_process_review_result_progression() -> None:
    state: dict[str, object] = {}
    controller = SessionController(state)

    assert controller.phase is AppPhase.SELECT
    controller.begin_processing(b"ephemeral-image")
    assert controller.phase is AppPhase.PROCESS
    session = ReviewSession.from_result(make_result())
    controller.set_review(session, image=b"ephemeral-image")
    assert controller.phase is AppPhase.REVIEW
    controller.set_result(session.finalize(NOW))
    assert controller.phase is AppPhase.RESULT


def test_controller_rejects_result_before_successful_review() -> None:
    controller = SessionController({})
    document = ReviewSession.from_result(make_result()).finalize(NOW)

    with pytest.raises(InvalidPhaseTransition):
        controller.set_result(document)


def test_explicit_reset_removes_ephemeral_document_state() -> None:
    state: dict[str, object] = {"unrelated": "keep"}
    controller = SessionController(state)
    controller.begin_processing(b"private-upload")
    controller.set_review(ReviewSession.from_result(make_result()), image=b"private-upload")

    controller.reset()

    assert controller.phase is AppPhase.SELECT
    assert controller.image is None
    assert controller.review is None
    assert controller.result is None
    assert state["unrelated"] == "keep"


def test_controller_exposes_no_result_while_review_is_invalid() -> None:
    controller = SessionController({})
    controller.begin_processing(b"image")
    pending = ReviewSession.from_result(make_result())
    controller.set_review(pending, image=b"image")

    assert controller.result is None

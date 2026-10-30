"""Single-session state controller used by the Streamlit composition layer."""

from __future__ import annotations

from collections.abc import MutableMapping
from enum import StrEnum
from typing import Any

from formflow.review import ReviewSession
from formflow.validation import ValidatedDocument


class AppPhase(StrEnum):
    SELECT = "select"
    PROCESS = "process"
    REVIEW = "review"
    RESULT = "result"


class InvalidPhaseTransition(RuntimeError):
    """Raised when the UI attempts to skip a required workflow phase."""


class SessionController:
    PREFIX = "formflow."
    PHASE = f"{PREFIX}phase"
    IMAGE = f"{PREFIX}image"
    REVIEW = f"{PREFIX}review"
    RESULT = f"{PREFIX}result"

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self._state = state
        self._state.setdefault(self.PHASE, AppPhase.SELECT.value)

    @property
    def phase(self) -> AppPhase:
        return AppPhase(self._state[self.PHASE])

    @property
    def image(self) -> Any | None:
        return self._state.get(self.IMAGE)

    @property
    def review(self) -> ReviewSession | None:
        value = self._state.get(self.REVIEW)
        return value if isinstance(value, ReviewSession) else None

    @property
    def result(self) -> ValidatedDocument | None:
        value = self._state.get(self.RESULT)
        return value if isinstance(value, ValidatedDocument) else None

    def begin_processing(self, image: Any) -> None:
        self._require(AppPhase.SELECT)
        self._state[self.IMAGE] = image
        self._state[self.PHASE] = AppPhase.PROCESS.value

    def set_review(self, review: ReviewSession, *, image: Any | None = None) -> None:
        self._require(AppPhase.PROCESS)
        if image is not None:
            self._state[self.IMAGE] = image
        self._state[self.REVIEW] = review
        self._state[self.PHASE] = AppPhase.REVIEW.value

    def set_result(self, result: ValidatedDocument) -> None:
        self._require(AppPhase.REVIEW)
        if not isinstance(result, ValidatedDocument):
            raise TypeError("Result must be a ValidatedDocument.")
        self._state[self.RESULT] = result
        self._state[self.PHASE] = AppPhase.RESULT.value

    def reset(self) -> None:
        for key in (self.IMAGE, self.REVIEW, self.RESULT):
            self._state.pop(key, None)
        self._state[self.PHASE] = AppPhase.SELECT.value

    def _require(self, expected: AppPhase) -> None:
        if self.phase is not expected:
            raise InvalidPhaseTransition(
                f"Expected phase {expected.value}, current phase is {self.phase.value}."
            )

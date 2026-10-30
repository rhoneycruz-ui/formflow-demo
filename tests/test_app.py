from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

from formflow.domain import FieldName, OcrReading

ROOT = Path(__file__).parents[1]


class DeterministicEngine:
    def __init__(self, pending_count: int = 0) -> None:
        self.pending_count = pending_count
        self.calls = 0

    def read(self, crop, field_name: FieldName) -> OcrReading:
        del crop
        self.calls += 1
        if self.calls <= self.pending_count:
            return OcrReading("?", 0.05)
        text = "2" if field_name is FieldName.QUANTITY else "12,34"
        return OcrReading(text, 0.99)


def _button(at: AppTest, label: str):
    return next(button for button in at.button if button.label == label)


def _processed_app(engine: DeterministicEngine) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    at.session_state["formflow.engine"] = engine
    at.radio[0].set_value("Limpo")
    at = at.run(timeout=30)
    _button(at, "Processar documento").click()
    return at.run(timeout=30)


def test_initial_view_discloses_synthetic_data() -> None:
    at = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)

    copy = " ".join(element.value for element in at.markdown)
    assert "Dados 100% sintéticos" in copy
    assert len(at.radio) == 1
    assert len(at.file_uploader) == 1


def test_clean_sample_shows_full_form_sixteen_rows_and_result_downloads() -> None:
    at = _processed_app(DeterministicEngine())

    assert len(at.image) >= 1
    assert len(at.dataframe[0].value) == 16
    finalize = _button(at, "Concluir revisão")
    assert not finalize.disabled

    finalize.click()
    at = at.run(timeout=30)

    assert len(at.metric) == 6
    assert len(at.download_button) == 3


def test_pending_field_blocks_then_accepts_human_edit() -> None:
    at = _processed_app(DeterministicEngine(pending_count=2))

    finalize = _button(at, "Concluir revisão")
    assert finalize.disabled

    _button(at, "Confirmar vazio · Café Horizonte · Quantidade").click()
    at = at.run(timeout=30)
    assert _button(at, "Concluir revisão").disabled

    _button(at, "Confirmar vazio · Café Horizonte · Preço unitário").click()
    at = at.run(timeout=30)

    assert not _button(at, "Concluir revisão").disabled


def test_application_modules_have_no_network_or_external_api_clients() -> None:
    paths = [ROOT / "app.py", *(ROOT / "src" / "formflow").glob("*.py")]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    for forbidden in ("import requests", "import httpx", "import openai", "googleapiclient"):
        assert forbidden not in source


def test_app_entrypoint_imports_without_pytest_pythonpath() -> None:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)

    completed = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

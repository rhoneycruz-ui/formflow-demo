from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from formflow.app_state import AppPhase, SessionController
from formflow.exporters import to_audit_json, to_csv, to_xlsx
from formflow.image_pipeline import IncompatibleFormError, InvalidUploadError, validate_upload
from formflow.metrics import calculate_summary
from formflow.ocr import TesseractNumericOcr, TesseractUnavailableError, process_document
from formflow.review import ReviewSession
from formflow.sample_factory import SampleKind, render_sample
from formflow.template import render_blank_form
from formflow.ui import (
    inject_design_system,
    render_full_form_review,
    render_header,
    render_progress,
)

ROOT = Path(__file__).parent
SAMPLE_LABELS = {
    "Limpo": SampleKind.CLEAN,
    "Ruído": SampleKind.NOISY,
    "Revisão": SampleKind.REVIEW,
}


def _blank_template_bytes() -> bytes:
    from io import BytesIO

    output = BytesIO()
    render_blank_form().save(output, format="PNG")
    return output.getvalue()


def _render_select(controller: SessionController) -> None:
    render_progress(AppPhase.SELECT.value)
    st.markdown("## Escolha um documento")
    st.write(
        "Comece por uma amostra pronta ou envie uma foto do template FormFlow. "
        "Uploads permanecem somente nesta sessão."
    )
    selected = st.radio(
        "Documento de demonstração",
        options=list(SAMPLE_LABELS),
        horizontal=True,
        help="A amostra Revisão contém uma marca intencionalmente ambígua.",
    )
    upload = st.file_uploader("Ou envie JPEG/PNG", type=["jpg", "jpeg", "png"])
    st.download_button(
        "Baixar formulário em branco",
        data=_blank_template_bytes(),
        file_name="formflow-template.png",
        mime="image/png",
        width="content",
    )
    if st.button("Processar documento", type="primary", width="stretch"):
        try:
            image = (
                validate_upload(upload.getvalue(), upload.name)
                if upload is not None
                else render_sample(SAMPLE_LABELS[selected], seed=2026).image
            )
            controller.begin_processing(image)
            render_progress(AppPhase.PROCESS.value)
            with st.spinner("Registrando folha, extraindo 16 campos e executando OCR local..."):
                engine = st.session_state.get("formflow.engine") or TesseractNumericOcr()
                result = process_document(image, engine)
            controller.set_review(ReviewSession.from_result(result), image=image)
            st.rerun()
        except (InvalidUploadError, IncompatibleFormError, TesseractUnavailableError) as exc:
            controller.reset()
            st.error(str(exc))


def _render_review(controller: SessionController) -> None:
    render_progress(AppPhase.REVIEW.value)
    session = controller.review
    image = controller.image
    if session is None or image is None:
        controller.reset()
        st.rerun()
    st.markdown("## Revise antes de concluir")
    st.write("A leitura automática ajuda; a conclusão depende de cobertura e revisão explícitas.")
    render_full_form_review(session, image)
    report = session.validation_report()
    if report.issues:
        with st.expander(f"Ver {len(report.issues)} validações pendentes"):
            for issue in report.issues:
                st.write(f"• {issue.message}")
    action, reset = st.columns([0.72, 0.28])
    with action:
        if st.button(
            "Concluir revisão",
            type="primary",
            disabled=not report.is_valid,
            width="stretch",
        ):
            controller.set_result(session.finalize(datetime.now(UTC)))
            st.rerun()
    with reset:
        if st.button("Reprocessar", width="stretch"):
            controller.reset()
            st.rerun()


def _br_money(value) -> str:
    formatted = f"{value:,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _render_result(controller: SessionController) -> None:
    render_progress(AppPhase.RESULT.value)
    document = controller.result
    if document is None:
        controller.reset()
        st.rerun()
    summary = calculate_summary(document)
    st.markdown("## Registro validado e pronto para uso")
    st.success("16/16 campos representados · 16/16 resolvidos · 0 pendências")
    columns = st.columns(3)
    metrics = (
        ("Unidades", str(summary.total_units)),
        ("Valor estimado", _br_money(summary.order_total)),
        ("Aceitos automaticamente", f"{summary.automated_count}/16"),
        ("Revisados", str(summary.reviewed_count)),
        ("Taxa de automação", f"{summary.automation_rate:.0%}"),
        ("Tempo medido", f"{summary.total_time_ms / 1000:.2f} s"),
    )
    for index, (label, value) in enumerate(metrics):
        columns[index % 3].metric(label, value)
    st.markdown("### Exportações auditáveis")
    csv_column, xlsx_column, json_column = st.columns(3)
    csv_column.download_button(
        "Baixar CSV", to_csv(document), "formflow-itens.csv", "text/csv", width="stretch"
    )
    xlsx_column.download_button(
        "Baixar XLSX",
        to_xlsx(document),
        "formflow-itens.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    json_column.download_button(
        "Baixar auditoria JSON",
        to_audit_json(document),
        "formflow-auditoria.json",
        "application/json",
        width="stretch",
    )
    st.caption("Gerado em memória. Nenhuma imagem, valor ou exportação é persistida.")
    if st.button("Processar outro documento"):
        controller.reset()
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="FormFlow · OCR e revisão humana",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_design_system()
    render_header()
    controller = SessionController(st.session_state)
    if controller.phase is AppPhase.SELECT:
        _render_select(controller)
    elif controller.phase is AppPhase.REVIEW:
        _render_review(controller)
    elif controller.phase is AppPhase.RESULT:
        _render_result(controller)
    else:
        controller.reset()
        st.rerun()


if __name__ == "__main__":
    main()

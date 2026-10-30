"""Streamlit presentation helpers for the FormFlow review experience."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

from formflow.domain import FieldName, FieldStatus
from formflow.image_pipeline import register_form
from formflow.review import ReviewSession
from formflow.template import FIELD_LAYOUT, PRODUCTS

_STATUS_COLORS = {
    FieldStatus.AUTO: (35, 154, 109, 58),
    FieldStatus.PENDING: (245, 158, 11, 78),
    FieldStatus.REVIEWED: (37, 99, 235, 68),
    FieldStatus.BLANK: (100, 116, 139, 48),
}


def inject_design_system() -> None:
    st.markdown(
        """
        <style>
        :root {
          --desk: #eef2f1; --paper: #fbfcfa; --carbon: #142b35;
          --petrol: #0f5965; --petrol-soft: #dcebed; --graphite: #587079;
          --highlighter: #d89516; --proof: #23855d; --line: rgba(20,43,53,.12);
        }
        .stApp { background: var(--desk); color: var(--carbon); }
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
        h1, h2, h3 { color: var(--carbon); letter-spacing: -.025em; text-wrap: balance; }
        p { text-wrap: pretty; }
        .ff-hero { padding: 24px 0 20px; }
        .ff-eyebrow { color: var(--petrol); font-size: .78rem; font-weight: 750;
          letter-spacing: .11em; text-transform: uppercase; margin-bottom: 8px; }
        .ff-hero h1 { font-size: clamp(2.2rem, 5vw, 4rem); line-height: .98; margin: 0;
          max-width: 820px; }
        .ff-hero p { color: var(--graphite); max-width: 720px; font-size: 1.05rem;
          line-height: 1.6; margin: 18px 0 0; }
        .ff-badge { display: inline-flex; align-items: center; gap: 8px; margin-top: 18px;
          padding: 7px 11px; border-radius: 8px; background: #e1f2e9; color: #176846;
          font-size: .78rem; font-weight: 700; }
        .ff-badge:before { content: ''; width: 7px; height: 7px; border-radius: 50%;
          background: var(--proof); }
        .ff-rail { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
          margin: 8px 0 30px; }
        .ff-step { padding: 10px 12px; border-top: 3px solid rgba(20,43,53,.13);
          color: #75878d; font-size: .76rem; font-weight: 650; }
        .ff-step.active { border-color: var(--petrol); color: var(--petrol); }
        .ff-step.done { border-color: var(--proof); color: #176846; }
        .ff-sheet { background: var(--paper); border-radius: 14px; padding: 18px;
          box-shadow: 0 0 0 1px rgba(20,43,53,.05), 0 8px 30px rgba(20,43,53,.07); }
        .ff-coverage { display:flex; justify-content:space-between; gap:16px; align-items:end;
          padding: 14px 0 18px; border-bottom: 1px solid var(--line); margin-bottom: 18px; }
        .ff-coverage strong { font-size: 1.8rem; font-variant-numeric: tabular-nums; }
        .ff-coverage span { color: var(--graphite); font-size: .82rem; }
        .stButton > button, .stDownloadButton > button { min-height: 44px; border-radius: 8px;
          font-weight: 680; transition: transform 120ms cubic-bezier(.23,1,.32,1),
          box-shadow 150ms cubic-bezier(.23,1,.32,1); }
        .stButton > button:active, .stDownloadButton > button:active { transform: scale(.97); }
        [data-testid="stMetric"] { background: var(--paper); padding: 16px; border-radius: 10px;
          box-shadow: 0 0 0 1px rgba(20,43,53,.07); }
        [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
        [data-testid="stFileUploader"] { background: var(--paper); border-radius: 12px;
          padding: 8px; box-shadow: 0 0 0 1px rgba(20,43,53,.06); }
        @media (max-width: 640px) {
          .block-container { padding: 1rem 1rem 3rem; }
          .ff-rail { grid-template-columns: repeat(2, 1fr); }
          .ff-hero h1 { font-size: 2.35rem; }
        }
        @media (prefers-reduced-motion: reduce) {
          .stButton > button, .stDownloadButton > button { transition: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <section class="ff-hero">
          <div class="ff-eyebrow">Python · OCR local · revisão humana</div>
          <h1>Do formulário fotografado ao dado confiável.</h1>
          <p>Uma demonstração interativa de processamento documental: correção de perspectiva,
          leitura numérica, revisão assistida, validação e exportação auditável.</p>
          <div class="ff-badge">Dados 100% sintéticos</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_progress(active: str) -> None:
    steps = (("select", "01 · Escolher"), ("process", "02 · Processar"),
             ("review", "03 · Revisar"), ("result", "04 · Exportar"))
    order = [name for name, _ in steps]
    active_index = order.index(active)
    items = []
    for index, (name, label) in enumerate(steps):
        state = "done" if index < active_index else "active" if name == active else ""
        items.append(f'<div class="ff-step {state}">{label}</div>')
    st.markdown(f'<nav class="ff-rail">{"".join(items)}</nav>', unsafe_allow_html=True)


def _annotated_form(image: Image.Image, session: ReviewSession) -> Image.Image:
    registered = register_form(image).image.convert("RGBA")
    overlay = Image.new("RGBA", registered.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for key, field in session.fields.items():
        if key not in FIELD_LAYOUT:
            continue
        box = FIELD_LAYOUT[key]
        color = _STATUS_COLORS[field.status]
        draw.rounded_rectangle(
            (box.x, box.y, box.right, box.bottom),
            radius=8,
            fill=color,
            outline=(*color[:3], 210),
            width=4,
        )
    return Image.alpha_composite(registered, overlay).convert("RGB")


def _display_value(value: int | Decimal | None) -> str:
    if value is None:
        return ""
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def _review_rows(session: ReviewSession) -> list[dict[str, str]]:
    product_names = {product.product_id: product.name for product in PRODUCTS}
    labels = {FieldName.QUANTITY: "Quantidade", FieldName.UNIT_PRICE: "Preço unitário"}
    status_labels = {
        FieldStatus.AUTO: "Aceito",
        FieldStatus.PENDING: "Revisar",
        FieldStatus.REVIEWED: "Revisado",
        FieldStatus.BLANK: "Vazio",
    }
    return [
        {
            "ID": key.product_id,
            "Produto": product_names[key.product_id],
            "Campo": labels[key.field_name],
            "Valor": _display_value(field.value),
            "Estado": status_labels[field.status],
        }
        for key, field in session.fields.items()
        if key in FIELD_LAYOUT
    ]


def render_full_form_review(session: ReviewSession, image: Image.Image) -> None:
    report = session.validation_report()
    st.markdown(
        f"""
        <div class="ff-coverage">
          <div><span>COBERTURA ESTRUTURAL</span><br><strong>{report.represented}/16</strong></div>
          <div><span>RESOLVIDOS</span><br><strong>{report.resolved}/16</strong></div>
          <div><span>PENDÊNCIAS</span><br><strong>{report.pending}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    image_column, editor_column = st.columns([1.06, 0.94], gap="large")
    with image_column:
        st.markdown("### Folha completa")
        st.caption("Verde automático · amarelo pendente · azul revisado · cinza vazio")
        st.image(_annotated_form(image, session), width="stretch")
    with editor_column:
        st.markdown("### Conferência dos 16 campos")
        st.caption("Todos os campos permanecem visíveis e editáveis.")
        rows = _review_rows(session)
        frame = pd.DataFrame(rows, dtype=object)
        edited = st.data_editor(
            frame,
            hide_index=True,
            width="stretch",
            height=620,
            disabled=["ID", "Produto", "Campo", "Estado"],
            column_config={
                "Valor": st.column_config.TextColumn(
                    "Valor", help="Use inteiro para quantidade e 12,34 para preço."
                )
            },
            key=f"review_editor_{session.revision}",
        )
        changed = False
        errors: list[str] = []
        keys = [key for key in session.fields if key in FIELD_LAYOUT]
        for index, key in enumerate(keys):
            proposed = str(edited.iloc[index]["Valor"] or "").strip()
            current = rows[index]["Valor"]
            if proposed == current:
                continue
            try:
                session.apply_edit(key, proposed, datetime.now(UTC))
                changed = True
            except ValueError as exc:
                errors.append(f"{rows[index]['Produto']} · {rows[index]['Campo']}: {exc}")
        for error in errors:
            st.error(error)
        if changed:
            st.rerun()

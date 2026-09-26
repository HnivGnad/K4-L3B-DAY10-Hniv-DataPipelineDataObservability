"""Reusable Streamlit building blocks (cards, badges, side-by-side panels)."""
from __future__ import annotations

from typing import Any

import streamlit as st


def metric_card(title: str, value: Any, delta: str | None = None) -> None:
    """Compact labelled value card."""
    with st.container(border=True):
        st.caption(title)
        st.markdown(f"<h3 style='margin:0'>{value}</h3>", unsafe_allow_html=True)
        if delta:
            st.caption(delta)


def state_card(title: str, body: str, color: str = "#2563eb") -> None:
    """Side-by-side state summary card."""
    bg = "rgba(37, 99, 235, 0.08)" if color == "#2563eb" else "rgba(220, 38, 38, 0.08)"
    with st.container(border=True):
        st.markdown(
            f"<div style='background:{bg}; padding:12px; border-radius:8px;'>"
            f"<strong>{title}</strong></div>",
            unsafe_allow_html=True,
        )
        st.markdown(body)


def hit_badge(score: float) -> str:
    """Render a score badge string with colour cue."""
    if score >= 0.6:
        return f"<span style='background:#16a34a;color:white;padding:2px 6px;border-radius:4px'>{score:.2f}</span>"
    if score >= 0.3:
        return f"<span style='background:#eab308;color:black;padding:2px 6px;border-radius:4px'>{score:.2f}</span>"
    return f"<span style='background:#dc2626;color:white;padding:2px 6px;border-radius:4px'>{score:.2f}</span>"


def kpi_row(metrics: list[tuple[str, Any]]) -> None:
    """Render a row of evenly distributed metric tiles."""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        with col:
            metric_card(label, value)

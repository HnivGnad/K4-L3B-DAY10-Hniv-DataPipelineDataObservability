"""So sánh các chỉ số retrieval / answer-quality giữa 3 trạng thái pipeline.

Quy ước ngôn ngữ:
- **Tiếng Anh giữ nguyên**: tên metric (``retrieval_hit_rate``, ``mean_token_f1``,
  ``judge_accuracy``, ``mean_judge_score``), state keys (``baseline`` /
  ``corrupted`` / ``repaired``), ChromaDB collection names.
- **Tiếng Việt**: tiêu đề phần, caption, câu giải thích nghiệp vụ.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from app.state import STATE_COLORS, STATE_LABELS_VI, STATES
from core.config import load_settings
from core.utils import read_json


# Order hiển thị metric trên bảng và biểu đồ (key tiếng Anh ↔ nhãn hiển thị).
METRIC_KEYS: tuple[str, ...] = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)

# Nhãn tiếng Việt cho từng metric — đặt trong ngoặc đơn tên tiếng Anh để tra cứu.
METRIC_LABELS_VI: dict[str, str] = {
    "retrieval_hit_rate": "Tỉ lệ truy hồi đúng (retrieval_hit_rate)",
    "mean_token_f1": "F1 trung bình (mean_token_f1)",
    "judge_accuracy": "Độ chính xác judge (judge_accuracy)",
    "mean_judge_score": "Điểm judge TB (mean_judge_score)",
}


@st.cache_data
def load_metrics() -> dict[str, dict[str, Any]]:
    """Đọc 3 file metrics.json do pipeline ``run_phase1.py`` / ``run_corruption_flow.py`` sinh ra."""
    settings = load_settings()
    return {
        "baseline": read_json(Path(settings.paths.baseline_metrics)),
        "corrupted": read_json(Path(settings.paths.corrupted_metrics)),
        "repaired": read_json(Path(settings.paths.repaired_metrics)),
    }


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _signed(value: float) -> str:
    """Δ có dấu và màu: dương xanh, âm đỏ, không đổi xám."""
    if value > 0:
        return f"🟢 +{value:.4f}"
    if value < 0:
        return f"🔴 {value:.4f}"
    return "⚪ 0.0000"


def _row_color(value: str) -> str:
    if value.startswith("🟢"):
        return "color: #16a34a; font-weight: bold"
    if value.startswith("🔴"):
        return "color: #dc2626; font-weight: bold"
    return ""


def _build_comparison_table(data: dict[str, dict]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for metric_key in METRIC_KEYS:
        baseline = float(data["baseline"].get(metric_key, 0.0))
        corrupted = float(data["corrupted"].get(metric_key, 0.0))
        repaired = float(data["repaired"].get(metric_key, 0.0))
        rows.append(
            {
                "Metric": METRIC_LABELS_VI[metric_key],
                "baseline": _format_number(baseline),
                "corrupted": _format_number(corrupted),
                "repaired": _format_number(repaired),
                "Δ corrupted − baseline": _signed(corrupted - baseline),
                "Δ repaired − baseline": _signed(repaired - baseline),
                "Δ repaired − corrupted": _signed(repaired - corrupted),
            }
        )
    return pd.DataFrame(rows)


def _build_long_chart_data(data: dict[str, dict]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for metric_key in METRIC_KEYS:
        for state in STATES:
            rows.append(
                {
                    "Metric": METRIC_LABELS_VI[metric_key],
                    "state_key": state,
                    "Trạng thái": STATE_LABELS_VI[state],
                    "Giá trị": float(data[state].get(metric_key, 0.0)),
                }
            )
    return pd.DataFrame(rows)


def render() -> None:
    """Render toàn bộ tab so sánh — UI tiếng Việt, thuật ngữ chuyên ngành giữ Anh."""
    st.title("🔀 So sánh 3 trạng thái pipeline")
    st.caption(
        "Cùng một bộ test gồm **10 câu hỏi** — đo trên cả 3 ChromaDB collection "
        "(`papers-baseline`, `papers-corrupted`, `papers-repaired`)."
    )
    data = load_metrics()

    # 1. Bảng so sánh ------------------------------------------------------------
    st.subheader("Bảng chỉ số theo 3 trạng thái")
    st.caption(
        "Cột `Δ` hiển thị delta giữa các cặp trạng thái — "
        "🟢 dương = cải thiện, 🔴 âm = suy giảm, ⚪ 0 = không đổi."
    )
    table = _build_comparison_table(data)
    styled = table.style.map(
        _row_color,
        subset=[
            "Δ corrupted − baseline",
            "Δ repaired − baseline",
            "Δ repaired − corrupted",
        ],
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.divider()

    # 2. Biểu đồ line/facet ------------------------------------------------------
    st.subheader("Đường đi của 4 metric qua 3 trạng thái")
    st.caption(
        "Mỗi ô nhỏ là một metric; đường nối 3 trạng thái cho thấy mức suy giảm "
        "do dữ liệu lỗi và khả năng phục hồi sau repair."
    )
    long_df = _build_long_chart_data(data)
    color_scale = alt.Scale(
        domain=[STATE_LABELS_VI[s] for s in STATES],
        range=[STATE_COLORS[s] for s in STATES],
    )
    line = (
        alt.Chart(long_df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=90), strokeWidth=3)
        .encode(
            x=alt.X(
                "state_key:N",
                sort=list(STATES),
                title="trạng thái",
                axis=alt.Axis(
                    labelAngle=0,
                    labelExpr="datum.value == 'baseline' ? 'baseline' : "
                    "datum.value == 'corrupted' ? 'corrupted' : 'repaired'",
                ),
            ),
            y=alt.Y("Giá trị:Q", title="giá trị"),
            color=alt.Color("Trạng thái:N", scale=color_scale, legend=None),
            tooltip=[
                alt.Tooltip("Metric:N"),
                alt.Tooltip("state_key:N"),
                alt.Tooltip("Giá trị:Q", format=".4f"),
            ],
        )
    )
    facet = line.facet(column=alt.Column("Metric:N", title=None))
    st.altair_chart(facet, use_container_width=True)

    st.divider()

    # 3. Diễn giải tự động --------------------------------------------------------
    st.subheader("Diễn giải tự động (auto-generated narrative)")
    base_metrics = data["baseline"]
    corr_metrics = data["corrupted"]
    rep_metrics = data["repaired"]
    st.markdown(
        "\n".join(
            [
                f"- **retrieval_hit_rate**: từ "
                f"`{_format_number(base_metrics['retrieval_hit_rate'])}` "
                f"(baseline) xuống `{_format_number(corr_metrics['retrieval_hit_rate'])}` "
                f"(corrupted), phục hồi về `{_format_number(rep_metrics['retrieval_hit_rate'])}` "
                f"(repaired).",
                f"- **mean_token_f1**: tụt "
                f"`{base_metrics['mean_token_f1'] - corr_metrics['mean_token_f1']:.4f}` "
                f"sau khi corrupt; repair bù lại "
                f"`{rep_metrics['mean_token_f1'] - corr_metrics['mean_token_f1']:.4f}`.",
                f"- **judge_accuracy**: giảm "
                f"`{base_metrics['judge_accuracy'] - corr_metrics['judge_accuracy']:.4f}` "
                f"khi bị lỗi; phục hồi "
                f"`{rep_metrics['judge_accuracy'] - corr_metrics['judge_accuracy']:.4f}` sau repair.",
                f"- **mean_judge_score** (thang 1–5): "
                f"`{_format_number(base_metrics['mean_judge_score'])}` → "
                f"`{_format_number(corr_metrics['mean_judge_score'])}` → "
                f"`{_format_number(rep_metrics['mean_judge_score'])}`.",
            ]
        )
    )

    st.divider()

    # 4. Tóm tắt dạng thẻ KPI ----------------------------------------------------
    st.subheader("Tóm tắt KPI")
    st.caption("Mỗi ô là 1 metric: giá trị baseline, Δ so với baseline, và chuỗi `corrupted → repaired`.")
    kpi_cols = st.columns(4)
    kpi_payload = [
        (METRIC_LABELS_VI["retrieval_hit_rate"], base_metrics, corr_metrics, rep_metrics, "retrieval_hit_rate"),
        (METRIC_LABELS_VI["mean_token_f1"], base_metrics, corr_metrics, rep_metrics, "mean_token_f1"),
        (METRIC_LABELS_VI["judge_accuracy"], base_metrics, corr_metrics, rep_metrics, "judge_accuracy"),
        (METRIC_LABELS_VI["mean_judge_score"], base_metrics, corr_metrics, rep_metrics, "mean_judge_score"),
    ]
    for col, (label, b, c, r, key) in zip(kpi_cols, kpi_payload):
        with col:
            st.metric(
                label,
                value=f"{_format_number(b[key])}",
                delta=_signed(r[key] - b[key]),
                delta_color="normal",
            )
            st.caption(f"corrupted: {_format_number(c[key])} → repaired: {_format_number(r[key])}")

    st.divider()

    # 5. Báo cáo Markdown gốc ----------------------------------------------------
    report_md = Path(load_settings().paths.comparison_report)
    if report_md.exists():
        with st.expander("Xem file Markdown gốc: `data/reports/corruption_report.md`"):
            st.markdown(report_md.read_text(encoding="utf-8"))

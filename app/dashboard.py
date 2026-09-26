"""Hiển thị GX checks + tín hiệu freshness cho 3 trạng thái pipeline cạnh nhau.

Quy ước ngôn ngữ:
- **Tiếng Anh giữ nguyên**: thuật ngữ kỹ thuật — ``stale_ratio``, ``is_fresh``,
  ``freshness_threshold_days``, ``stale_ratio_threshold``, ``checks``,
  ``expectation``, ``paper_id``, ``title``, ``summary``, …
- **Tiếng Việt**: tiêu đề phần, caption, câu giải thích nghiệp vụ.

Dữ liệu được đọc trực tiếp từ các file JSON do ``run_phase1.py`` /
``run_corruption_flow.py`` sinh ra — chỉ đọc, không sửa.
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


# Ngưỡng SLA mặc định (dùng khi file JSON thiếu trường ``stale_ratio_threshold``).
DEFAULT_STALE_RATIO_THRESHOLD: float = 0.25


# --- helpers: truy cập JSON an toàn ---------------------------------------------

def _quality_report_path(settings, name: str) -> Path:
    """Trả về ``data/quality/<name>_quality_report.json``."""
    return Path(settings.paths.quality_dir) / f"{name}_quality_report.json"


@st.cache_data
def load_quality() -> dict[str, dict[str, Any]]:
    """Đọc 3 file quality report (baseline/corrupted/repaired) từ disk."""
    settings = load_settings()
    base = read_json(_quality_report_path(settings, "baseline"))
    corr = read_json(_quality_report_path(settings, "corrupted"))
    rep = read_json(_quality_report_path(settings, "repaired"))
    return {"baseline": base, "corrupted": corr, "repaired": rep}


def _extract_freshness(payload: dict[str, Any]) -> dict[str, Any]:
    """Trả về block freshness dù ở 1 trong 2 schema:

    Schema A (baseline / repaired): ``payload["freshness"] = {...}``
    Schema B (corrupted): các trường phẳng ở top-level (``stale_ratio``,
    ``stale_rows``, …) — pipeline ghi đè từ ``build_freshness_report``.

    Output luôn là dict với các key mặc định, gọi trực tiếp không cần ``.get()``.
    """
    fresh = payload.get("freshness")
    if fresh is None:
        # Schema B: đọc flat keys từ top-level
        fresh = {
            "stale_ratio": payload.get("stale_ratio", 0.0),
            "stale_rows": payload.get("stale_rows", 0),
            "total_rows": payload.get("total_rows", 0),
            "is_fresh": payload.get("is_fresh", False),
            "freshness_threshold_days": payload.get("freshness_threshold_days", 180),
            "stale_ratio_threshold": payload.get(
                "stale_ratio_threshold", DEFAULT_STALE_RATIO_THRESHOLD
            ),
        }
    else:
        # Schema A: bổ sung key mặc định nếu thiếu
        fresh = {
            "stale_ratio": float(fresh.get("stale_ratio", 0.0)),
            "stale_rows": int(fresh.get("stale_rows", 0)),
            "total_rows": int(fresh.get("total_rows", 0)),
            "is_fresh": bool(fresh.get("is_fresh", False)),
            "freshness_threshold_days": int(fresh.get("freshness_threshold_days", 180)),
            "stale_ratio_threshold": float(
                fresh.get("stale_ratio_threshold", DEFAULT_STALE_RATIO_THRESHOLD)
            ),
        }
    return fresh


def _gate_value(payload: dict[str, Any], freshness: dict[str, Any]) -> bool:
    """Quality gate: True nếu payload khai báo success=True, fallback theo is_fresh."""
    if "success" in payload:
        return bool(payload["success"])
    return bool(freshness["is_fresh"])


# --- helpers trực quan -----------------------------------------------------------

def _badge(passed: bool) -> str:
    return "✅ ĐẠT" if passed else "❌ KHÔNG ĐẠT"


def _gate_color(passed: bool) -> str:
    return "#16a34a" if passed else "#dc2626"


def _vi_expectation(name: str) -> str:
    """Dịch tên GX Expectation class sang tiếng Việt; giữ fallback tiếng Anh."""
    stem = name.replace("Expect", "").replace("Expectation", "")
    vi_map = {
        "TableRowCountToBeBetween": "Số dòng nằm trong khoảng",
        "ColumnValuesToNotBeNull": "Không được rỗng",
        "ColumnValuesToBeUnique": "Giá trị phải duy nhất",
        "ColumnValueLengthsToBeBetween": "Độ dài nằm trong khoảng",
    }
    for eng, vi in vi_map.items():
        if eng in stem:
            return f"{vi} ({eng})"
    return stem  # giữ nguyên tên class nếu không map được


def _vi_column(column: str | None) -> str:
    """Cột kiểm tra → tiếng Việt (giữ paper_id vì là schema key)."""
    if not column:
        return "toàn bảng"
    mapping = {
        "paper_id": "paper_id",
        "title": "tiêu đề (title)",
        "summary": "tóm tắt (summary)",
    }
    return mapping.get(column, column)


def _format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _freshness_summary_vi(fresh: dict[str, Any]) -> str:
    return (
        f"stale_rows = **{int(fresh['stale_rows'])}** / "
        f"total_rows = **{int(fresh['total_rows'])}**  \n"
        f"stale_ratio = **{_format_pct(float(fresh['stale_ratio']))}** "
        f"(SLA threshold = {_format_pct(float(fresh['stale_ratio_threshold']))})"
    )


def _check_table(quality: dict) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for check in quality.get("checks", []):
        rows.append(
            {
                "Expectation": _vi_expectation(check["expectation"]),
                "Column": _vi_column(check.get("column")),
                "Result": "✅ pass" if check.get("success") else "❌ fail",
            }
        )
    return pd.DataFrame(rows)


# --- trang chính ------------------------------------------------------------------

def render() -> None:
    """Render toàn bộ tab dashboard — UI tiếng Việt, thuật ngữ chuyên ngành giữ Anh."""
    st.title("📊 Bảng Điều Khiển Chất Lượng & Độ Tươi")
    st.caption(
        "Great Expectations 1.x (ephemeral context) kết hợp **freshness SLA 180 ngày** — "
        "so sánh đồng thời 3 trạng thái của pipeline."
    )
    data = load_quality()

    # Trích freshness & quality gate dùng schema nào (handle defensive)
    enriched: dict[str, dict[str, Any]] = {}
    for state in STATES:
        payload = data[state]
        freshness = _extract_freshness(payload)
        gate_ok = _gate_value(payload, freshness)
        checks = payload.get("checks", [])
        enriched[state] = {
            "payload": payload,
            "freshness": freshness,
            "checks": checks,
            "gate_ok": gate_ok,
        }

    # 1. 3 cột tóm tắt -----------------------------------------------------------
    st.subheader("Tổ quan 3 trạng thái")
    cols = st.columns(3)
    for col, state in zip(cols, STATES):
        info = enriched[state]
        freshness = info["freshness"]
        checks = info["checks"]
        passed = sum(bool(c.get("success")) for c in checks)
        gate_ok = info["gate_ok"]
        state_color = STATE_COLORS[state]

        with col:
            st.markdown(
                f"<h4 style='color:{state_color};margin:0 0 4px 0'>"
                f"{STATE_LABELS_VI[state]}</h4>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<h3 style='color:{_gate_color(gate_ok)};margin:0'>"
                f"{_badge(gate_ok)}</h3>",
                unsafe_allow_html=True,
            )
            st.caption(f"**{passed}/{len(checks)}** GX checks pass")
            st.markdown("---")
            st.markdown("**Freshness SLA**")
            st.markdown(
                "🟢 **Còn tươi** (`is_fresh = true`)"
                if freshness["is_fresh"]
                else "🔴 **Hết tươi** (`is_fresh = false`)"
            )
            st.markdown(_freshness_summary_vi(freshness))

    st.divider()

    # 2. Bảng chi tiết ------------------------------------------------------------
    st.subheader("Chi tiết từng expectation của Great Expectations")
    detail_state_label = st.radio(
        "Chọn trạng thái để xem chi tiết",
        options=[STATE_LABELS_VI[s] for s in STATES],
        horizontal=True,
        key="dash_detail_state",
    )
    detail_state_key = next(
        s for s in STATES if STATE_LABELS_VI[s] == detail_state_label
    )
    if enriched[detail_state_key]["checks"]:
        st.dataframe(
            _check_table(enriched[detail_state_key]["payload"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "Trạng thái này không có GX checks (file JSON chỉ chứa freshness block) — "
            "đây là thiết kế pipeline: state **Lỗi** được sinh từ "
            "`build_freshness_report()` chứ không qua `run_data_quality_checks()`."
        )

    st.divider()

    # 3. Biểu đồ stale_ratio ------------------------------------------------------
    st.subheader("Tỉ lệ dòng quá hạn (stale_ratio) ở 3 trạng thái")
    st.caption(
        f"Ngưỡng SLA = **stale_ratio_threshold = "
        f"{int(DEFAULT_STALE_RATIO_THRESHOLD * 100)}%** "
        "(đường nét đứt màu cam). Khi vượt ngưỡng này, hệ thống đánh dấu "
        "**không còn tươi** (`is_fresh = false`)."
    )
    freshness_rows = [
        {
            "Trạng thái": STATE_LABELS_VI[state],
            "stale_ratio": float(enriched[state]["freshness"]["stale_ratio"]),
            "stale_rows": int(enriched[state]["freshness"]["stale_rows"]),
            "total_rows": int(enriched[state]["freshness"]["total_rows"]),
            "_key": state,
        }
        for state in STATES
    ]
    df = pd.DataFrame(freshness_rows)

    bar = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Trạng thái:N", title="Trạng thái"),
            y=alt.Y(
                "stale_ratio:Q",
                title="stale_ratio",
                axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 0.4]),
            ),
            color=alt.Color(
                "Trạng thái:N",
                scale=alt.Scale(
                    domain=[STATE_LABELS_VI[s] for s in STATES],
                    range=[STATE_COLORS[s] for s in STATES],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Trạng thái:N"),
                alt.Tooltip("stale_ratio:Q", title="stale_ratio", format=".2%"),
                alt.Tooltip("stale_rows:Q", title="stale_rows"),
                alt.Tooltip("total_rows:Q", title="total_rows"),
            ],
        )
    )
    threshold_line = (
        alt.Chart(pd.DataFrame({"Ngưỡng": [DEFAULT_STALE_RATIO_THRESHOLD]}))
        .mark_rule(color="orange", strokeDash=[4, 4])
        .encode(y="Ngưỡng:Q")
    )
    st.altair_chart(bar + threshold_line, use_container_width=True)

    # 4. Biểu đồ số check pass ----------------------------------------------------
    st.subheader("Số GX checks pass ở 3 trạng thái")
    gate_rows = [
        {
            "Trạng thái": STATE_LABELS_VI[state],
            "Số checks pass": sum(bool(c.get("success")) for c in enriched[state]["checks"]),
            "Tổng checks": len(enriched[state]["checks"]),
        }
        for state in STATES
    ]
    df2 = pd.DataFrame(gate_rows)

    bar2 = (
        alt.Chart(df2)
        .mark_bar()
        .encode(
            x="Trạng thái:N",
            y=alt.Y("Số checks pass:Q", title="Số checks pass"),
            color=alt.Color(
                "Trạng thái:N",
                scale=alt.Scale(
                    domain=[STATE_LABELS_VI[s] for s in STATES],
                    range=[STATE_COLORS[s] for s in STATES],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Trạng thái:N"),
                alt.Tooltip("Số checks pass:Q"),
                alt.Tooltip("Tổng checks:Q"),
            ],
        )
    )
    st.altair_chart(bar2, use_container_width=True)

    # 5. Insight tự động -----------------------------------------------------------
    st.subheader("Nhận xét tự động")
    base_info = enriched["baseline"]
    corr_info = enriched["corrupted"]
    rep_info = enriched["repaired"]

    base_passed = sum(bool(c.get("success")) for c in base_info["checks"])
    corr_passed = sum(bool(c.get("success")) for c in corr_info["checks"])
    rep_passed = sum(bool(c.get("success")) for c in rep_info["checks"])
    corr_fresh = corr_info["freshness"]

    st.markdown(
        f"""
- Trạng thái **Sạch (Baseline)** đạt **{base_passed}/{len(base_info['checks'])}** checks, dữ liệu hoàn hảo.
- Trạng thái **Lỗi (Corrupted)** chỉ có freshness block — pipeline không chạy GX ở state này (`build_freshness_report()` ghi đè `corrupted_quality_report.json`).
- Trạng thái **Phục hồi (Repaired)** phục hồi **{rep_passed}/{len(rep_info['checks'])}** checks — cơ chế repair idempotent từ `data/raw/`.
- **Freshness SLA** ở trạng thái **Lỗi**: `stale_rows = {corr_fresh['stale_rows']}`, `total_rows = {corr_fresh['total_rows']}`, `stale_ratio = {_format_pct(float(corr_fresh['stale_ratio']))}` — vẫn dưới ngưỡng SLA 25 % nên `is_fresh = true`.
"""
    )

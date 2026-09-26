from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import build_embedding_text


# Fixed RNG for reproducibility (PHAN_CONG_NHOM.md: "Không bịa đặt số liệu").
RNG = random.Random(42)


def _recompute_derived(df: pd.DataFrame, run_date: datetime) -> pd.DataFrame:
    """Recompute derived fields from the final corrupted source columns."""
    df = df.copy()
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    run_day = pd.Timestamp(run_date)
    run_day = run_day.tz_localize("UTC") if run_day.tzinfo is None else run_day.tz_convert("UTC")
    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df["age_days"] = (run_day.normalize() - published.dt.normalize()).dt.days
    if "text_for_embedding" in df.columns:
        df["text_for_embedding"] = df.apply(lambda row: build_embedding_text(row.to_dict()), axis=1)
    return df


def _apply_drop_latest(df: pd.DataFrame, log: dict) -> pd.DataFrame:
    """Scenario 1: Drop 20% records mới nhất (sort theo `published` desc)."""
    n_drop = min(len(df), max(1, math.ceil(len(df) * 0.2)))
    sorted_df = df.sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
    drop_ids = sorted_df.head(n_drop)["paper_id"].tolist()
    corrupted = df[~df["paper_id"].isin(drop_ids)].copy()
    log["scenarios"].append(
        {
            "type": "drop_latest_records",
            "params": {"drop_ratio": 0.2, "sort_key": "published", "n_drop": n_drop},
            "affected_paper_ids": drop_ids,
            "before_count": len(df),
            "after_count": len(corrupted),
            "expected_quality_signal": "row_count_below_min",
        }
    )
    return corrupted


def _apply_blank_summary(df: pd.DataFrame, log: dict) -> pd.DataFrame:
    """Scenario 2: Blank summary một số dòng."""
    target_count = min(3, len(df))
    target_indices = RNG.sample(range(len(df)), k=target_count)
    affected = df.iloc[target_indices]["paper_id"].tolist()
    corrupted = df.copy()
    corrupted.loc[corrupted["paper_id"].isin(affected), "summary"] = ""
    log["scenarios"].append(
        {
            "type": "blank_summary",
            "params": {"target_count": target_count},
            "affected_paper_ids": affected,
            "expected_quality_signal": "summary_length_below_min",
        }
    )
    return corrupted


def _apply_inject_noise(df: pd.DataFrame, log: dict) -> pd.DataFrame:
    """Scenario 3: Inject noise token vào summary."""
    target_count = min(3, len(df))
    target_indices = RNG.sample(range(len(df)), k=target_count)
    affected = df.iloc[target_indices]["paper_id"].tolist()
    corrupted = df.copy()
    noise = " ###CORRUPT### "
    mask = corrupted["paper_id"].isin(affected)
    corrupted.loc[mask, "summary"] = (
        noise + corrupted.loc[mask, "summary"].astype(str) + noise
    )
    log["scenarios"].append(
        {
            "type": "inject_noise",
            "params": {"token": noise, "target_count": target_count},
            "affected_paper_ids": affected,
            "expected_quality_signal": "noise_token_detected",
        }
    )
    return corrupted


def _apply_truncate_title(df: pd.DataFrame, log: dict) -> pd.DataFrame:
    """Scenario 4: Truncate title xuống dưới 8 ký tự (max=7)."""
    target_count = min(2, len(df))
    target_indices = RNG.sample(range(len(df)), k=target_count)
    affected = df.iloc[target_indices]["paper_id"].tolist()
    max_chars = 7
    corrupted = df.copy()
    mask = corrupted["paper_id"].isin(affected)
    corrupted.loc[mask, "title"] = (
        corrupted.loc[mask, "title"].astype(str).str[:max_chars]
    )
    log["scenarios"].append(
        {
            "type": "truncate_title",
            "params": {"max_chars": max_chars, "target_count": target_count},
            "affected_paper_ids": affected,
            "expected_quality_signal": "title_length_below_min",
        }
    )
    return corrupted


def _apply_stale_date(df: pd.DataFrame, log: dict, run_date: datetime) -> pd.DataFrame:
    """Scenario 5: Lùi `published` về quá khứ (>180 ngày) để trigger Freshness SLA.

    Args:
        run_date: thời điểm hiện tại để tính age_days.
    """
    # Duplicate corruption runs after this step and can add up to three rows.
    # Select enough stale source rows to keep the final stale ratio strictly
    # above the 25% SLA even if none of the duplicated rows is stale.
    expected_duplicate_rows = min(3, len(df))
    expected_final_rows = len(df) + expected_duplicate_rows
    target_count = min(len(df), int(expected_final_rows * 0.25) + 1)
    target_indices = RNG.sample(range(len(df)), k=target_count)
    affected = df.iloc[target_indices]["paper_id"].tolist()
    days_back = 400  # > 180 ngưỡng Freshness
    new_published = (run_date - timedelta(days=days_back)).date().isoformat()

    corrupted = df.copy()
    mask = corrupted["paper_id"].isin(affected)
    corrupted.loc[mask, "published"] = new_published

    log["scenarios"].append(
        {
            "type": "stale_date",
            "params": {
                "days_back": days_back,
                "target_count": target_count,
                "stale_ratio_threshold": 0.25,
                "new_published": new_published,
            },
            "affected_paper_ids": affected,
            "expected_quality_signal": "freshness_sla_violation",
        }
    )
    return corrupted


def _apply_duplicate_rows(df: pd.DataFrame, log: dict) -> pd.DataFrame:
    """Scenario 6: Nhân bản một số dòng (duplicate)."""
    n_dup = min(3, len(df))
    target_indices = RNG.sample(range(len(df)), k=n_dup)
    duplicated = df.iloc[target_indices].copy()
    corrupted = pd.concat([df, duplicated], ignore_index=True)
    log["scenarios"].append(
        {
            "type": "duplicate_rows",
            "params": {"n_duplicates": n_dup},
            "affected_paper_ids": duplicated["paper_id"].tolist(),
            "expected_quality_signal": "paper_id_unique_violation",
        }
    )
    return corrupted


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
    run_date: datetime | None = None,
) -> pd.DataFrame:
    """Orchestrator: chạy 6 scenario corruption trên clean dataframe.

    Args:
        df: clean dataframe từ `build_clean_dataframe()` của Đạt.
        output_log_path: đường dẫn ghi `corruption_log.json` (PHẢI dùng path từ Settings.paths).
        run_date: thời điểm chạy pipeline (để tính age_days cho stale_date).
            Mặc định None — sẽ lấy `datetime.now(UTC)` lúc runtime.

    Returns:
        Corrupted dataframe với đầy đủ 6 tác động đã được rebuild cột dẫn xuất.

    Notes:
        - Skeleton phase (Giai đoạn 1): 6 hàm con hiện chỉ ghi log entry, không sửa data.
        - Logic thật sẽ implement ở Giai đoạn 3 (sau khi Đạt xong cleaning.py).
        - Tham số `run_date` được truyền xuống `_apply_stale_date` để tính age_days chính xác.
    """
    if run_date is None:
        from core.utils import now_utc

        run_date = now_utc()

    # Reset RNG cho mỗi lần gọi để đảm bảo reproducibility/idempotency
    RNG.seed(42)

    log: dict = {
        "scenarios": [],
        "seed": 42,
        "baseline_rows": len(df),
    }

    corrupted = df.copy()

    # Áp dụng 6 kịch bản theo thứ tự PHAN_CONG_NHOM.md
    corrupted = _apply_drop_latest(corrupted, log)
    corrupted = _apply_blank_summary(corrupted, log)
    corrupted = _apply_inject_noise(corrupted, log)
    corrupted = _apply_truncate_title(corrupted, log)
    corrupted = _apply_stale_date(corrupted, log, run_date)
    corrupted = _apply_duplicate_rows(corrupted, log)

    # Rebuild cột dẫn xuất sau khi corrupt
    corrupted = _recompute_derived(corrupted, run_date)

    log["corrupted_rows"] = len(corrupted)
    log["unique_paper_ids"] = bool(corrupted["paper_id"].is_unique)

    # Ghi log artifact
    write_json(output_log_path, log)

    return corrupted

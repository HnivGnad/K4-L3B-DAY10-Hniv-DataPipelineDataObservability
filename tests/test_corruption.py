"""Pytest suite for src/ingestion/corruption.py (Thái — B3 bonus).

Chạy:
    pytest tests/test_corruption.py -v

Coverage:
- Schema & structure (2 tests)
- 6 corruption scenarios (6 tests)
- Idempotency & reproducibility (2 tests)
- Edge cases (2 tests)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd
import pytest

from ingestion.corruption import corrupt_clean_dataframe


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def run_date() -> datetime:
    return datetime(2026, 9, 26, tzinfo=timezone.utc)


@pytest.fixture
def clean_df() -> pd.DataFrame:
    """24-row fake clean dataframe matching Dat's cleaning.py schema."""
    base_date = datetime(2026, 9, 26, tzinfo=timezone.utc)
    return pd.DataFrame(
        {
            "paper_id": [f"10.1145/{i:04d}" for i in range(24)],
            "title": [f"Long Title Number {i} About Agentic RAG" for i in range(24)],
            "summary": [f"Summary content {i} " * 20 for i in range(24)],
            "authors_joined": [f"Author{i} A, Author{i} B" for i in range(24)],
            "categories_joined": [f"Cat{i}" for i in range(24)],
            "published": [
                (base_date - pd.Timedelta(days=i * 10)).date().isoformat()
                for i in range(24)
            ],
            "updated": ["2026-01-01"] * 24,
            "age_days": [i * 10 for i in range(24)],
            "summary_chars": [200] * 24,
            "text_for_embedding": ["placeholder"] * 24,
            "abs_url": ["http://abs"] * 24,
            "pdf_url": ["http://pdf"] * 24,
        }
    )


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "corruption_log.json"


# ---------------------------------------------------------------------------
# Schema & structure
# ---------------------------------------------------------------------------

def test_corrupt_returns_dataframe(clean_df, log_path, run_date):
    """corrupt_clean_dataframe phai tra ve DataFrame, khong phai None."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    assert isinstance(out, pd.DataFrame)


def test_corrupt_preserves_columns(clean_df, log_path, run_date):
    """Schema cac cot khong bi thay doi — chi gia tri thay doi."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    assert set(out.columns) == set(clean_df.columns)


# ---------------------------------------------------------------------------
# 6 corruption scenarios
# ---------------------------------------------------------------------------

def test_drop_latest(clean_df, log_path, run_date):
    """Scenario 1: Drop 20% records moi nhat (khoang 4-5 rows)."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    assert len(out) < len(clean_df), "drop_latest phai giam row count"
    drop_scenario = next(s for s in _read_log(log_path)["scenarios"] if s["type"] == "drop_latest_records")
    assert drop_scenario["before_count"] == 24
    assert len(drop_scenario["affected_paper_ids"]) >= 1


def test_blank_summary(clean_df, log_path, run_date):
    """Scenario 2: Co it nhat 1 row co summary = ''."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    assert (out["summary"] == "").sum() >= 1


def test_inject_noise(clean_df, log_path, run_date):
    """Scenario 3: Co it nhat 1 row co chua token CORRUPT trong summary."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    assert out["summary"].str.contains("CORRUPT", na=False).sum() >= 1


def test_truncate_title(clean_df, log_path, run_date):
    """Scenario 4: Co it nhat 1 row co title < 8 chars."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    assert (out["title"].str.len() < 8).sum() >= 1


def test_stale_date(clean_df, log_path, run_date):
    """Scenario 5: Ty le stale phai vuot nguong 25% cua freshness SLA."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    stale_ratio = (out["age_days"] > 180).sum() / len(out)
    assert stale_ratio > 0.25
    stale_scenario = next(s for s in _read_log(log_path)["scenarios"] if s["type"] == "stale_date")
    assert stale_scenario["expected_quality_signal"] == "freshness_sla_violation"


def test_duplicate_rows(clean_df, log_path, run_date):
    """Scenario 6: Row count tang va paper_id khong con unique."""
    out = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    # Sau drop_latest (giam) + duplicate (tang) -> net result co the >= hoac < 24
    assert not out["paper_id"].is_unique, "duplicate_rows phai lam mat unique"


# ---------------------------------------------------------------------------
# Idempotency & reproducibility
# ---------------------------------------------------------------------------

def test_seed_reproducibility(clean_df, log_path, run_date):
    """Hai lan goi voi cung input -> cung output (sorted by paper_id)."""
    out1 = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    out2 = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    ids1 = sorted(out1["paper_id"].tolist())
    ids2 = sorted(out2["paper_id"].tolist())
    assert ids1 == ids2, "Idempotency fail: paper_id set khac nhau"


def test_log_overwrite_each_call(clean_df, log_path, run_date):
    """Moi lan goi se overwrite log file voi 6 scenarios moi."""
    out1 = corrupt_clean_dataframe(clean_df, log_path, run_date=run_date)
    log = _read_log(log_path)
    assert len(log["scenarios"]) == 6
    assert log["baseline_rows"] == 24


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_dataframe(log_path, run_date):
    """Dataframe rong (0 rows) khong crash."""
    empty_df = pd.DataFrame(
        columns=[
            "paper_id", "title", "summary", "authors_joined", "categories_joined",
            "published", "updated", "age_days", "summary_chars",
            "text_for_embedding", "abs_url", "pdf_url",
        ]
    )
    out = corrupt_clean_dataframe(empty_df, log_path, run_date=run_date)
    assert len(out) == 0
    log = _read_log(log_path)
    assert log["baseline_rows"] == 0
    assert len(log["scenarios"]) == 6


def test_log_path_created(clean_df, tmp_path: Path, run_date):
    """Log file va parent dir duoc tao tu dong."""
    nested_log = tmp_path / "nested" / "deep" / "log.json"
    assert not nested_log.parent.exists()
    corrupt_clean_dataframe(clean_df, nested_log, run_date=run_date)
    assert nested_log.exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_log(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

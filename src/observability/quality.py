"""Validate cleaned paper data and record its freshness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def _freshness_stats(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Calculate age and publication-date signals shared by both reports."""
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    dates = pd.to_datetime(df["published"], errors="coerce", utc=True)
    total_rows = len(df)
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else None
    invalid_age_rows = int(ages.isna().sum())
    invalid_date_rows = int(dates.isna().sum())

    return {
        "latest_published": dates.max().date().isoformat() if dates.notna().any() else None,
        "oldest_published": dates.min().date().isoformat() if dates.notna().any() else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_ratio_threshold": 0.25,
        "invalid_age_rows": invalid_age_rows,
        "invalid_date_rows": invalid_date_rows,
        "is_fresh": bool(total_rows and not invalid_age_rows and not invalid_date_rows and stale_ratio <= 0.25),
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run GX 1.x checks and a freshness gate, then save their JSON evidence."""
    required = {"paper_id", "title", "summary", "published", "age_days"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Clean dataset is missing required columns: {', '.join(missing)}")

    # GX 1.x fluent API accepts the in-memory dataframe through batch parameters.
    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas(name="papers")
    asset = source.add_dataframe_asset(name="clean_papers")
    batch_definition = asset.add_batch_definition_whole_dataframe(name="all_papers")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=settings.max_results, max_value=settings.max_results
        ),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="summary"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=10),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=50),
    ]
    checks = []
    for expectation in expectations:
        result = batch.validate(expectation, result_format="SUMMARY")
        checks.append({
            "expectation": expectation.__class__.__name__,
            "column": getattr(expectation, "column", None),
            "success": bool(result.success),
            "result": result.result,
        })

    freshness = _freshness_stats(df, settings)
    payload = {
        "report_name": report_name,
        "success": all(check["success"] for check in checks) and freshness["is_fresh"],
        "checks": checks,
        "freshness": freshness,
    }
    output_path = settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json"
    write_json(output_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Save publication-date range and stale-paper counts as a JSON report."""
    required = {"published", "age_days"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Clean dataset is missing required columns: {', '.join(missing)}")
    payload = _freshness_stats(df, settings)
    write_json(Path(report_path), payload)
    return payload

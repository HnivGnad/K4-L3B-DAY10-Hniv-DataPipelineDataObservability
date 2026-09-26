"""Render pipeline measurements as Markdown without inventing results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


METRICS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _display(value: Any) -> str:
    """Format a measured value for a Markdown table cell."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _quality_summary(quality: dict[str, Any]) -> str:
    """Show the gate result and how many GX checks passed."""
    checks = quality.get("checks", [])
    passed = sum(bool(check.get("success")) for check in checks)
    return f"{_display(quality.get('success'))} ({passed}/{len(checks)} checks)"


def _failed_checks(quality: dict[str, Any]) -> str:
    """List failing checks so a report does not hide why a quality gate failed."""
    failed = [
        f"{check.get('expectation')} ({check.get('column') or 'table'})"
        for check in quality.get("checks", []) if not check.get("success")
    ]
    return ", ".join(failed) if failed else "None"


def _freshness_value(freshness: dict[str, Any], key: str) -> Any:
    """Read a freshness value from a direct report or an embedded quality report."""
    return freshness.get(key, freshness.get("freshness", {}).get(key))


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline source, evaluation, quality, and freshness results."""
    lines = ["# Baseline pipeline report", "", "## Source", "", "| Field | Value |", "| --- | --- |"]
    lines.extend(f"| {_display(key)} | {_display(value)} |" for key, value in source_summary.items())
    lines += ["", "## Evaluation", "", "| Metric | Value |", "| --- | ---: |"]
    lines.extend(f"| {name} | {_display(metrics.get(name))} |" for name in METRICS)
    lines += ["", "## Data quality", "", f"Overall gate: **{_display(quality.get('success'))}**", ""]
    lines += ["| Check | Column | Passed |", "| --- | --- | --- |"]
    for check in quality.get("checks", []):
        lines.append(
            f"| {_display(check.get('expectation'))} | {_display(check.get('column'))} | "
            f"{_display(check.get('success'))} |"
        )
    lines += ["", f"Failed checks: {_display(_failed_checks(quality))}"]
    lines += ["", "## Freshness", "", "| Signal | Value |", "| --- | ---: |"]
    for key in ("latest_published", "oldest_published", "stale_rows", "total_rows", "stale_ratio", "freshness_threshold_days", "stale_ratio_threshold", "is_fresh"):
        lines.append(f"| {key} | {_display(_freshness_value(freshness, key))} |")
    write_text(Path(report_path), "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Compare measured baseline, corrupted, and repaired outcomes in Markdown."""
    lines = [
        "# Corruption and repair report", "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name in METRICS:
        lines.append(
            f"| {name} | {_display(baseline_metrics.get(name))} | "
            f"{_display(corrupted_metrics.get(name))} | {_display(repaired_metrics.get(name))} |"
        )
    lines += ["", "## Quality and freshness", "", "| Signal | Corrupted | Repaired |", "| --- | ---: | ---: |"]
    lines.append(f"| Quality gate | {_quality_summary(corrupted_quality)} | {_quality_summary(repaired_quality)} |")
    lines.append(f"| Failed checks | {_display(_failed_checks(corrupted_quality))} | {_display(_failed_checks(repaired_quality))} |")
    for key in ("is_fresh", "stale_rows", "total_rows", "stale_ratio", "latest_published", "oldest_published"):
        lines.append(
            f"| {key} | {_display(_freshness_value(corrupted_freshness, key))} | "
            f"{_display(_freshness_value(repaired_freshness, key))} |"
        )
    lines += ["", "## Observed changes", ""]
    for name in METRICS:
        before, damaged, repaired = (item.get(name) for item in (baseline_metrics, corrupted_metrics, repaired_metrics))
        if all(isinstance(value, (int, float)) for value in (before, damaged, repaired)):
            lines.append(
                f"- {name}: corrupted − baseline = {_display(damaged - before)}; "
                f"repaired − corrupted = {_display(repaired - damaged)}."
            )
    if lines[-1] == "":
        lines.append("No comparable numeric metrics were provided.")
    write_text(Path(report_path), "\n".join(lines) + "\n")

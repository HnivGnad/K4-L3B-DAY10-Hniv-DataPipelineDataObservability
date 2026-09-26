"""Quality-gated repair from the trusted raw snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import read_json, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks


class AutoRepairError(RuntimeError):
    """The quality gate failed and the trusted raw snapshot could not restore it."""


@dataclass(frozen=True)
class AutoRepairOutcome:
    repaired_df: pd.DataFrame | None
    quality: dict[str, Any] | None
    freshness: dict[str, Any] | None
    event: dict[str, Any]


def _failure_reasons(quality: dict[str, Any]) -> list[str]:
    reasons = [
        f"{check['expectation']}:{check.get('column') or 'table'}"
        for check in quality.get("checks", [])
        if not check.get("success", False)
    ]
    if not quality.get("freshness", {}).get("is_fresh", False):
        reasons.append("freshness_sla")
    return reasons or ["quality_gate_failed"]


def auto_repair_if_needed(
    settings: Settings,
    baseline_df: pd.DataFrame,
    corrupted_quality: dict[str, Any],
    run_date: datetime,
) -> AutoRepairOutcome:
    """Rebuild once when the gate fails; publish evidence for every decision."""
    event: dict[str, Any] = {
        "triggered": not bool(corrupted_quality.get("success", False)),
        "trigger_reasons": _failure_reasons(corrupted_quality)
        if not corrupted_quality.get("success", False) else [],
        "source": str(settings.paths.raw_records_json.relative_to(settings.paths.project_dir)),
        "action": "rebuild_from_raw_snapshot",
        "before_quality_success": bool(corrupted_quality.get("success", False)),
        "status": "skipped",
    }
    if not event["triggered"]:
        write_json(settings.paths.auto_repair_event, event)
        return AutoRepairOutcome(None, None, None, event)

    try:
        raw_path = settings.paths.raw_records_json
        raw_hash_before = sha256(raw_path.read_bytes()).hexdigest()
        if settings.paths.active_state.exists():
            approved_hash = read_json(settings.paths.active_state).get("raw_sha256")
            if approved_hash and approved_hash != raw_hash_before:
                raise AutoRepairError("Trusted raw snapshot differs from the approved baseline")
        records = load_raw_records(raw_path)
        if not records:
            raise AutoRepairError("Trusted raw snapshot contains no records")
        repaired_df = build_clean_dataframe(records, run_date)
        if set(repaired_df.columns) != set(baseline_df.columns):
            raise AutoRepairError("Rebuilt schema differs from baseline")
        if len(repaired_df) != len(baseline_df) or set(repaired_df["paper_id"]) != set(baseline_df["paper_id"]):
            raise AutoRepairError("Rebuilt paper identities differ from baseline")

        repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
        repaired_freshness = build_freshness_report(
            repaired_df, settings, settings.paths.repaired_freshness_report
        )
        if not repaired_quality["success"]:
            raise AutoRepairError("Rebuilt data still fails the quality or freshness gate")
        raw_hash_after = sha256(raw_path.read_bytes()).hexdigest()
        if raw_hash_before != raw_hash_after:
            raise AutoRepairError("Trusted raw snapshot changed during repair")

        event.update({
            "status": "repaired",
            "raw_sha256": raw_hash_before,
            "after_quality_success": True,
            "before_rows": corrupted_quality.get("freshness", {}).get("total_rows"),
            "after_rows": len(repaired_df),
            "repaired_collection": settings.repaired_collection_name,
        })
        write_json(settings.paths.auto_repair_event, event)
        return AutoRepairOutcome(repaired_df, repaired_quality, repaired_freshness, event)
    except Exception as exc:
        event.update({"status": "failed", "error": str(exc), "after_quality_success": False})
        write_json(settings.paths.auto_repair_event, event)
        raise AutoRepairError(f"Automatic repair failed: {exc}") from exc

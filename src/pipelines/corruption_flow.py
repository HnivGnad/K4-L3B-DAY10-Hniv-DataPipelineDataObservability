from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _repair_from_raw(settings: Settings, run_date: datetime) -> pd.DataFrame:
    """Repair idempotent: rebuild dataframe from raw snapshot, KHONG sua truc tiep corrupted.

    Theo PHAN_CONG_NHOM.md muc 3.5 (Thai so huu):
    - Luon dung repaired dataframe lai tu `data/raw/crossref_records.json` qua cleaning pipeline.
    - Khong sua va truc tiep corrupted dataframe.
    - Chay repair nhieu lan cho ket qua tuong duong.
    """
    raw_records = load_raw_records(settings.paths.raw_records_json)
    if not raw_records:
        raise ValueError(
            "Repair failed: raw snapshot is empty at "
            f"{settings.paths.raw_records_json}"
        )
    repaired_df = build_clean_dataframe(raw_records, run_date)
    if not repaired_df["paper_id"].is_unique:
        raise ValueError("Repair failed: rebuilt dataframe has duplicate paper_id")
    return repaired_df


def _save_state(df: pd.DataFrame, settings: Settings, prefix: str) -> None:
    """Persist a dataframe state to CSV + JSON using the same paths for all three states."""
    write_csv(df, settings.paths.project_dir / "data" / "clean" / f"papers_clean_{prefix}.csv")
    json_records = json.loads(df.to_json(orient="records", date_format="iso"))
    write_json(
        settings.paths.project_dir / "data" / "clean" / f"papers_clean_{prefix}.json",
        json_records,
    )


def _evaluate_state(
    settings: Settings,
    df: pd.DataFrame,
    embeddings_path,
    metrics_path,
    answers_path,
    test_set_path,
) -> EvaluationBundle:
    """Build index for a dataframe state, then evaluate it against the shared test set."""
    index = LocalEmbeddingIndex.build(
        df,
        settings=settings,
        embeddings_output_path=embeddings_path,
    )
    return evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=test_set_path,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )


def run_corruption_flow(settings: Settings | None = None) -> dict[str, EvaluationBundle]:
    """Run the corruption -> evaluate -> repair -> compare flow and write all artifacts."""
    settings = settings or load_settings()
    run_started_at = now_utc()

    # 1. Load baseline clean dataframe (phai giong voi phase1)
    baseline_json = settings.paths.project_dir / "data" / "clean" / "papers_clean.json"
    if not baseline_json.exists():
        raise FileNotFoundError(
            "Baseline clean dataframe not found. Run `python script/run_phase1.py` first."
        )
    baseline_df = pd.read_json(baseline_json)
    if baseline_df.empty:
        raise ValueError("Baseline clean dataframe is empty; cannot run corruption flow.")

    # Doc baseline metrics tu phase1 (de so sanh 3 trang thai)
    if not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError(
            f"Baseline metrics not found at {settings.paths.baseline_metrics}. "
            "Run phase1 first."
        )
    baseline_metrics = json.loads(settings.paths.baseline_metrics.read_text(encoding="utf-8"))

    # 2. Corrupt (Thai so huu corrupt_clean_dataframe)
    corrupted_df = corrupt_clean_dataframe(
        baseline_df,
        output_log_path=settings.paths.corruption_log,
        run_date=run_started_at,
    )
    _save_state(corrupted_df, settings, prefix="corrupted")

    # 3. Rebuild index cho CORRUPTED va danh gia
    corrupted_eval = _evaluate_state(
        settings=settings,
        df=corrupted_df,
        embeddings_path=settings.paths.corrupted_embeddings_json,
        metrics_path=settings.paths.corrupted_metrics,
        answers_path=settings.paths.corrupted_answers,
        test_set_path=settings.paths.eval_testset,
    )

    # 4. Quality + Freshness tren CORRUPTED (Dung so huu)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.corrupted_freshness_report,
    )

    # 5. Repair IDEMPOTENT tu raw snapshot (Thai so huu quy tac repair)
    repaired_df = _repair_from_raw(settings, run_started_at)
    _save_state(repaired_df, settings, prefix="repaired")

    # 6. Rebuild index cho REPAIRED va danh gia
    repaired_eval = _evaluate_state(
        settings=settings,
        df=repaired_df,
        embeddings_path=settings.paths.repaired_embeddings_json,
        metrics_path=settings.paths.repaired_metrics,
        answers_path=settings.paths.repaired_answers,
        test_set_path=settings.paths.eval_testset,
    )

    # 7. Quality + Freshness tren REPAIRED (Dung so huu)
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.repaired_freshness_report,
    )

    # 8. So sanh 3 trang thai (Dung so huu reporting)
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    return {
        "baseline": baseline_metrics,
        "corrupted": corrupted_eval,
        "repaired": repaired_eval,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
    }


def main() -> None:
    """Run the corruption flow and print a comparison of the three states."""
    bundle = run_corruption_flow()

    print("\n=== Corruption flow completed ===")
    print("\nBaseline:")
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        val = bundle["baseline"].get(key)
        if isinstance(val, float):
            print(f"  {key}: {val:.4f}")

    print("\nCorrupted:")
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        val = bundle["corrupted"].summary.get(key)
        if isinstance(val, float):
            print(f"  {key}: {val:.4f}")
    print(f"  quality success: {bundle['corrupted_quality'].get('success')}")
    print(f"  is_fresh: {bundle['corrupted_quality']['freshness'].get('is_fresh')}")

    print("\nRepaired:")
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        val = bundle["repaired"].summary.get(key)
        if isinstance(val, float):
            print(f"  {key}: {val:.4f}")
    print(f"  quality success: {bundle['repaired_quality'].get('success')}")
    print(f"  is_fresh: {bundle['repaired_quality']['freshness'].get('is_fresh')}")

    print("\nArtifacts written:")
    print(f"  - data/clean/papers_clean_corrupted.csv/json")
    print(f"  - data/clean/papers_clean_repaired.csv/json")
    print(f"  - data/results/corruption_log.json")
    print(f"  - data/results/corrupted_metrics.json")
    print(f"  - data/results/repaired_metrics.json")
    print(f"  - data/quality/corrupted_freshness_report.json")
    print(f"  - data/quality/repaired_freshness_report.json")
    print(f"  - data/reports/corruption_report.md")

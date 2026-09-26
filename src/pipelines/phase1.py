from __future__ import annotations

import json
from hashlib import sha256

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


REQUIRED_CLEAN_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
    "age_days",
    "text_for_embedding",
}


def _load_source_records(settings: Settings) -> tuple[list[PaperRecord], str]:
    """Load the reproducible snapshot by default and refresh it only on request."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings), "crossref_api_or_fallback"
    return load_raw_records(settings.paths.raw_records_json), "local_raw_snapshot"


def _validate_clean_dataframe(df: pd.DataFrame) -> None:
    """Fail early with an actionable integration error before embedding starts."""
    if df.empty:
        raise ValueError("The cleaned dataframe is empty; baseline indexing cannot continue.")

    missing_columns = sorted(REQUIRED_CLEAN_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(
            "The cleaned dataframe does not satisfy the baseline contract. "
            f"Missing columns: {', '.join(missing_columns)}"
        )

    if df["paper_id"].isna().any() or (df["paper_id"].astype(str).str.strip() == "").any():
        raise ValueError("The cleaned dataframe contains an empty paper_id.")
    if not df["paper_id"].is_unique:
        raise ValueError("paper_id must be unique before building the baseline index.")

    empty_embedding_text = df["text_for_embedding"].isna() | (
        df["text_for_embedding"].astype(str).str.strip() == ""
    )
    if empty_embedding_text.any():
        raise ValueError("Every baseline record must have non-empty text_for_embedding.")


def _save_clean_artifacts(df: pd.DataFrame, settings: Settings) -> None:
    """Persist the same dataframe to CSV and JSON without leaking pandas types."""
    write_csv(df, settings.paths.clean_csv)
    json_records = json.loads(df.to_json(orient="records", date_format="iso"))
    write_json(settings.paths.clean_json, json_records)


def _prepare_test_set(df: pd.DataFrame, settings: Settings) -> None:
    """Create the benchmark once, then keep it fixed for all pipeline states."""
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(df, settings.paths.eval_testset)
    if not settings.paths.eval_testset.exists():
        raise FileNotFoundError(
            f"Evaluation set was not created at {settings.paths.eval_testset}."
        )


def run_baseline(settings: Settings | None = None) -> EvaluationBundle:
    """Build and evaluate the clean baseline, returning its evaluation bundle."""
    settings = settings or load_settings()
    run_started_at = now_utc()

    records, source_mode = _load_source_records(settings)
    if not records:
        raise ValueError("No source records are available for the baseline pipeline.")

    clean_df = build_clean_dataframe(records, run_started_at)
    _validate_clean_dataframe(clean_df)
    _save_clean_artifacts(clean_df, settings)

    baseline_index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    _prepare_test_set(clean_df, settings)

    evaluation = evaluate_pipeline(
        settings=settings,
        index=baseline_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(
        clean_df,
        settings,
        settings.paths.freshness_report,
    )
    if quality["success"]:
        write_json(settings.paths.active_state, {
            "state": "baseline",
            "collection_name": settings.baseline_collection_name,
            "quality_success": True,
            "auto_repair_status": "not_needed",
            "raw_sha256": sha256(settings.paths.raw_records_json.read_bytes()).hexdigest(),
        })
    source_summary = {
        "source": settings.source_api,
        "source_mode": source_mode,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "records": len(records),
        "clean_records": len(clean_df),
        "raw_response_path": str(
            settings.paths.raw_api_response.relative_to(settings.paths.project_dir)
        ),
        "raw_records_path": str(
            settings.paths.raw_records_json.relative_to(settings.paths.project_dir)
        ),
        "collection_name": baseline_index.collection_name,
        "run_started_at": run_started_at.isoformat(),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    return evaluation


def main() -> None:
    """Run the baseline pipeline and print its primary acceptance metrics."""
    evaluation = run_baseline()
    summary = evaluation.summary
    print("Baseline pipeline completed successfully.")
    print(f"Samples: {summary['samples']}")
    print(f"Retrieval hit rate: {summary['retrieval_hit_rate']:.4f}")
    print(f"Mean token F1: {summary['mean_token_f1']:.4f}")
    print(f"Judge accuracy: {summary['judge_accuracy']:.4f}")
    print(f"Mean judge score: {summary['mean_judge_score']:.4f}")

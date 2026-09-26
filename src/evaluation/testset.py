from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


QUESTION_TYPES = (
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "summary",
)

_REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "published",
    "categories_joined",
}


def _ground_truth(row: pd.Series, question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(row["summary"])
    if question_type == "authors":
        return row["authors_joined"]
    if question_type == "date":
        return row["published"]
    return row["categories_joined"]


def _question(title: str, question_type: str) -> str:
    if question_type == "summary":
        return f"What does the abstract of '{title}' say?"
    if question_type == "authors":
        return f"Who authored '{title}'?"
    if question_type == "date":
        return f"When was '{title}' published?"
    return f"What categories are listed for '{title}'?"


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Build ten source-grounded questions with deterministic IDs and paper choices."""
    missing_columns = _REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing columns: {sorted(missing_columns)}")
    if df["paper_id"].isna().any() or not df["paper_id"].is_unique:
        raise ValueError("Clean dataframe must have unique, non-null paper_id values")
    if len(df) < len(QUESTION_TYPES):
        raise ValueError("At least ten clean papers are needed for ten distinct questions")

    candidates = df.sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
    selected_ids: set[str] = set()
    questions: list[dict[str, Any]] = []
    for number, question_type in enumerate(QUESTION_TYPES, start=1):
        chosen: pd.Series | None = None
        for _, row in candidates.iterrows():
            paper_id = str(row["paper_id"])
            title = str(row["title"])
            answer = _ground_truth(row, question_type)
            if paper_id not in selected_ids and title and "'" not in title and isinstance(answer, str) and answer.strip():
                chosen = row
                break
        if chosen is None:
            raise ValueError(f"No unused paper has a valid answer for {question_type}")

        paper_id = str(chosen["paper_id"])
        selected_ids.add(paper_id)
        questions.append(
            {
                "id": f"q{number:02d}",
                "question_type": question_type,
                "question": _question(str(chosen["title"]), question_type),
                "ground_truth": _ground_truth(chosen, question_type),
                "ground_truth_doc_ids": [paper_id],
            }
        )

    write_json(Path(output_path), questions)
    return questions

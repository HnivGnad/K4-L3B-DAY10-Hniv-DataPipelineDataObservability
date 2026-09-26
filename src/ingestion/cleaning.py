from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "category_source",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
)

# Fallback topics are derived only from the paper title. They are not Crossref subjects.
_TITLE_TOPICS = (
    ("Agentic AI", r"\b(?:agentic|agents?|autonomous agents?)\b"),
    ("Healthcare", r"\b(?:medical|medicine|diagnostic|lesions?|healthcare)\b"),
    ("Governance and Compliance", r"\b(?:governance|compliance|regulatory)\b"),
    ("Security and Privacy", r"\b(?:security|privacy|investigation|safety)\b"),
    ("Computer Vision", r"\b(?:vision|multimodal|image)\b"),
    ("Economics and Finance", r"\b(?:economic|economics|financial|equity|market|supply chain)\b"),
    ("Education", r"\b(?:students?|education|teaching|classroom)\b"),
    ("Retrieval-Augmented Generation", r"\b(?:retrieval.augmented generation|rag)\b"),
)


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    without_tags = re.sub(r"<[^>]*>", " ", unescape(str(value)))
    return normalize_whitespace(without_tags)


def _clean_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    return [cleaned for item in value if (cleaned := _clean_text(item))]


def _parse_date(value: object) -> str | None:
    if value is None or not str(value).strip():
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def _infer_title_topics(title: str) -> list[str]:
    return [label for label, pattern in _TITLE_TOPICS if re.search(pattern, title, re.IGNORECASE)]


def build_embedding_text(row: dict[str, object]) -> str:
    """Build the shared five-part embedding text from cleaned fields."""
    return "\n".join(
        (
            f"Title: {row['title']}",
            f"Summary: {row['summary']}",
            f"Authors: {row['authors_joined']}",
            f"Categories: {row['categories_joined']}",
            f"Published: {row['published']}",
        )
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records into a stable dataframe for indexing and evaluation."""
    run_day = pd.Timestamp(run_date)
    if run_day.tzinfo is None:
        run_day = run_day.tz_localize("UTC")
    else:
        run_day = run_day.tz_convert("UTC")
    run_day = run_day.date()

    cleaned_records: list[dict[str, object]] = []
    for record in records:
        paper_id = _clean_text(record.paper_id).lower()
        title = _clean_text(record.title)
        published = _parse_date(record.published)
        if not paper_id or not title or published is None:
            continue

        summary = _clean_text(record.summary)
        authors = _clean_list(record.authors)
        source_categories = _clean_list(record.categories)
        primary_category = _clean_text(record.primary_category)
        if not source_categories and primary_category:
            source_categories = [primary_category]
        categories = source_categories or _infer_title_topics(title)
        category_source = "crossref_subject" if source_categories else "title_rules" if categories else "missing"
        row: dict[str, object] = {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": primary_category or (categories[0] if categories else ""),
            "category_source": category_source,
            "published": published,
            "updated": _parse_date(record.updated) or published,
            "abs_url": _clean_text(record.abs_url),
            "pdf_url": _clean_text(record.pdf_url),
            "comment": _clean_text(record.comment),
            "age_days": (run_day - datetime.fromisoformat(published).date()).days,
            "authors_joined": ", ".join(authors),
            "categories_joined": ", ".join(categories),
            "summary_chars": len(summary),
        }
        row["text_for_embedding"] = build_embedding_text(row)
        cleaned_records.append(row)

    df = pd.DataFrame.from_records(cleaned_records, columns=CLEAN_COLUMNS)
    if df.empty:
        return df
    return (
        df.drop_duplicates(subset="paper_id", keep="first")
        .sort_values("paper_id", kind="stable")
        .reset_index(drop=True)
    )

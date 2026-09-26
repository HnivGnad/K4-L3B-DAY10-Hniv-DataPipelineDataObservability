from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord
from retrieval.index import SearchResult
from retrieval.qa import answer_question


RUN_DATE = datetime(2026, 9, 26, tzinfo=timezone.utc)


def make_record(number: int, **changes: object) -> PaperRecord:
    record = PaperRecord(
        paper_id=f"10.1234/{number}",
        title=f"Agentic retrieval-augmented generation paper {number}",
        summary="<jats:p>One &amp; two.</jats:p> More details.",
        authors=[" Ada   Lovelace ", "Grace Hopper"],
        categories=[],
        primary_category="",
        published="2026-09-01",
        updated="2026-09-02",
        abs_url="https://example.org/article",
        pdf_url="",
        comment="",
    )
    return replace(record, **changes)


class DataContractTests(unittest.TestCase):
    def test_evaluation_can_use_vector_results_without_exact_title_lookup(self) -> None:
        class VectorOnlyIndex:
            def search(self, query, top_k=None):
                return [SearchResult(
                    paper_id="10.1234/1", title="Known title", score=0.7,
                    content="Summary: One sentence.",
                    metadata={"summary": "One sentence.", "published": "2026-09-01",
                              "authors_joined": "Ada Lovelace", "categories_joined": "Agentic AI"},
                )]

            def lookup(self, value):
                raise AssertionError("Evaluation must not use exact title lookup")

        result = answer_question(
            "What does the abstract of 'Known title' say?",
            settings=None, index=VectorOnlyIndex(), allow_exact_lookup=False,
        )
        self.assertEqual(result.retrieved_doc_ids, ["10.1234/1"])
        self.assertEqual(result.answer, "One sentence.")

    def test_cleaning_normalizes_and_deduplicates(self) -> None:
        records = [make_record(1), make_record(2, paper_id="10.1234/1")]
        df = build_clean_dataframe(records, RUN_DATE)

        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["summary"], "One & two. More details.")
        self.assertEqual(row["authors_joined"], "Ada Lovelace, Grace Hopper")
        self.assertEqual(row["summary_chars"], len(row["summary"]))
        self.assertEqual(row["age_days"], 25)
        self.assertEqual(row["category_source"], "title_rules")
        self.assertIn("Agentic AI", row["categories"])
        self.assertEqual(len(row["text_for_embedding"].splitlines()), 5)

    def test_source_categories_take_precedence_and_bad_dates_are_filtered(self) -> None:
        records = [
            make_record(1, categories=[" Crossref Subject "], updated="bad date"),
            make_record(2, published="bad date"),
        ]
        df = build_clean_dataframe(records, RUN_DATE)

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["categories"], ["Crossref Subject"])
        self.assertEqual(df.iloc[0]["category_source"], "crossref_subject")
        self.assertEqual(df.iloc[0]["updated"], "2026-09-01")

    def test_testset_is_stable_and_grounded_in_clean_rows(self) -> None:
        records = [make_record(number) for number in range(12)]
        df = build_clean_dataframe(records, RUN_DATE)
        shuffled = build_clean_dataframe(list(reversed(records)), RUN_DATE)

        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            questions = build_test_set(df, first_path)
            build_test_set(shuffled, second_path)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(json.loads(first_path.read_text()), questions)

        self.assertEqual(len(questions), 10)
        self.assertEqual(len({item["ground_truth_doc_ids"][0] for item in questions}), 10)
        self.assertEqual({item["question_type"] for item in questions}, {"summary", "authors", "date", "categories"})
        for question in questions:
            self.assertTrue(question["ground_truth"])
            self.assertIn(question["ground_truth_doc_ids"][0], set(df["paper_id"]))


if __name__ == "__main__":
    unittest.main()

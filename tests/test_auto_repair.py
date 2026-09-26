from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.config import load_settings
from core.utils import write_json
from ingestion.cleaning import build_clean_dataframe, build_embedding_text
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks
from pipelines.auto_repair import AutoRepairError, auto_repair_if_needed


RUN_DATE = datetime(2026, 9, 26, tzinfo=timezone.utc)
SOURCE_RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "crossref_records.json"


class AutoRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.settings = load_settings(project_dir=Path(self.temp_dir.name))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _baseline(self):
        raw_path = self.settings.paths.raw_records_json
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(SOURCE_RAW.read_bytes())
        return build_clean_dataframe(load_raw_records(raw_path), RUN_DATE)

    def test_failed_schema_gate_triggers_repair_from_unchanged_raw(self) -> None:
        baseline = self._baseline()
        before_hash = sha256(self.settings.paths.raw_records_json.read_bytes()).hexdigest()
        corrupted = baseline.drop(columns=["summary"])
        quality = run_data_quality_checks(corrupted, self.settings, "corrupted")
        self.assertFalse(quality["success"])

        outcome = auto_repair_if_needed(self.settings, baseline, quality, RUN_DATE)
        self.assertEqual(outcome.event["status"], "repaired")
        self.assertTrue(outcome.quality["success"])
        self.assertTrue(outcome.repaired_df.equals(baseline))
        self.assertEqual(sha256(self.settings.paths.raw_records_json.read_bytes()).hexdigest(), before_hash)
        self.assertEqual(json.loads(self.settings.paths.auto_repair_event.read_text())["status"], "repaired")

    def test_passing_gate_skips_repair(self) -> None:
        baseline = self._baseline()
        quality = {"success": True, "checks": [], "freshness": {"is_fresh": True}}
        outcome = auto_repair_if_needed(self.settings, baseline, quality, RUN_DATE)
        self.assertIsNone(outcome.repaired_df)
        self.assertEqual(outcome.event["status"], "skipped")
        self.assertFalse(outcome.event["triggered"])

    def test_missing_raw_fails_closed_and_records_event(self) -> None:
        baseline = build_clean_dataframe([], RUN_DATE)
        quality = {"success": False, "checks": [], "freshness": {"is_fresh": False}}
        with self.assertRaises(AutoRepairError):
            auto_repair_if_needed(self.settings, baseline, quality, RUN_DATE)
        event = json.loads(self.settings.paths.auto_repair_event.read_text())
        self.assertEqual(event["status"], "failed")
        self.assertFalse(event["after_quality_success"])

    def test_corruption_rounds_up_and_preserves_derived_contract(self) -> None:
        baseline = self._baseline()
        corrupted = corrupt_clean_dataframe(
            baseline, self.settings.paths.corruption_log, run_date=RUN_DATE
        )
        log = json.loads(self.settings.paths.corruption_log.read_text())
        self.assertEqual(log["scenarios"][0]["params"]["n_drop"], 5)
        for row in corrupted.to_dict("records"):
            self.assertEqual(row["text_for_embedding"], build_embedding_text(row))
            self.assertEqual(
                row["age_days"],
                (RUN_DATE.date() - datetime.fromisoformat(row["published"]).date()).days,
            )

    def test_changed_raw_snapshot_is_not_trusted(self) -> None:
        baseline = self._baseline()
        write_json(self.settings.paths.active_state, {"raw_sha256": "0" * 64})
        quality = {"success": False, "checks": [], "freshness": {"is_fresh": False}}
        with self.assertRaises(AutoRepairError):
            auto_repair_if_needed(self.settings, baseline, quality, RUN_DATE)
        self.assertEqual(json.loads(self.settings.paths.auto_repair_event.read_text())["status"], "failed")


if __name__ == "__main__":
    unittest.main()

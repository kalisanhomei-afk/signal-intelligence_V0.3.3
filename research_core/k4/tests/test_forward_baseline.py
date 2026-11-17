"""K4.5 historical-outcome leakage and honest persistence baseline tests."""
import json
from pathlib import Path
import unittest

from research_core.k4.forward_baseline import forecast

CASE_PATH = Path(__file__).resolve().parents[1] / "cases" / "2026-12-10-forward-baseline-input.json"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "cases" / "2026-12-10-forward-baseline-forecast.json"

class ForwardBaselineTests(unittest.TestCase):
    def case(self):
        return json.loads(CASE_PATH.read_text(encoding="utf-8"))

    def test_persisted_forecast_matches_committed_file(self):
        self.assertEqual(forecast(self.case()), json.loads(OUTPUT_PATH.read_text(encoding="utf-8")))

    def test_baseline_is_not_signal(self):
        x = forecast(self.case())
        self.assertEqual(x["forecast_value_mbu"], 1758)
        self.assertIsNone(x["consensus_value_mbu"])
        self.assertFalse(x["trade_eligible"])
        self.assertFalse(x["source_content_independently_authenticated"])

    def test_adjusted_production_without_balancing_rejected(self):
        c = self.case(); c["source_components_mbu"]["production"] += 1
        with self.assertRaisesRegex(ValueError, "SUPPLY_DEMAND_MISMATCH"): forecast(c)

    def test_future_input_rejected(self):
        c = self.case(); c["input_cutoff_utc"] = "2026-12-10T18:00:00Z"
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"): forecast(c)

    def test_future_source_rejected(self):
        c = self.case(); c["source_release_scheduled_utc"] = "2026-11-18T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"): forecast(c)

    def test_post_event_forecast_rejected(self):
        c = self.case(); c["created_utc"] = "2026-12-10T17:00:00Z"
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"): forecast(c)

    def test_unrecognized_source_rejected(self):
        c = self.case(); c["source_url"] = "https://example.com"
        with self.assertRaisesRegex(ValueError, "UNRECOGNIZED"): forecast(c)

    def test_fake_source_hash_rejected(self):
        c = self.case(); c["source_raw_sha256"] = "unknown"
        with self.assertRaisesRegex(ValueError, "HASH"): forecast(c)

    def test_future_outcome_injection_rejected(self):
        c = self.case(); c["actual_december_outcome_mbu"] = 0
        with self.assertRaisesRegex(ValueError, "INVALID_INPUT_CONTRACT"): forecast(c)

    def test_wrong_marketing_year_rejected(self):
        c = self.case(); c["marketing_year"] = "2027/28"
        with self.assertRaisesRegex(ValueError, "MODEL_OR_YEAR_MISMATCH"): forecast(c)

if __name__ == "__main__":
    unittest.main()

"""K4.5-B export driver first-case checks, no downloadable market data."""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from research_core.k4.export_driver_screen import assess

CASE = Path(__file__).resolve().parents[1] / "cases" / "2026-11-16-fgis-inspections-driver.json"

def sample():
    return json.loads(CASE.read_text(encoding="utf-8"))

class ExportDriverScreenTests(unittest.TestCase):
    def test_real_driver_is_mixed_signal(self):
        r = assess(sample())
        self.assertTrue(r["mixed_signals"])
        self.assertLess(r["weekly_vs_required_ratio"], 1)
        self.assertEqual(r["progress_vs_five_year_avg_percentage_points"], 2.1)
        self.assertLess(r["cumulative_yoy_change_percent"], -20)

    def test_sensitivity_cannot_be_promoted_to_forecast(self):
        r = assess(sample())
        self.assertIsNone(r["forecast_point_estimate_mbu"])
        self.assertEqual(r["model_v1_status"], "ABSTAIN_UNCALIBRATED_EXPORT_DRIVER")
        self.assertFalse(r["trade_eligible"])
        self.assertFalse(r["independent_predictive_edge_verified"])
        self.assertEqual([s["conditional_ending_stocks_mbu"] for s in r["scenario_only_not_probabilistic"]], [1808, 1758, 1708])

    def test_future_release_input_rejected(self):
        c = sample(); c["inputs_cutoff_utc"] = "2026-12-10T17:00:00Z"
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"): assess(c)

    def test_source_not_yet_released_rejected(self):
        c = sample(); c["source_report_release_utc_claim"] = "2026-11-18T17:00:00Z"
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"): assess(c)

    def test_late_capture_rejected(self):
        c = sample(); c["independent_pre_release_capture_utc"] = "2026-12-11T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "CAPTURE_TIME_ORDER"): assess(c)

    def test_cannot_claim_authentication_without_hash_and_capture(self):
        c = sample(); c["source_pit_authenticated"] = True
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_SOURCE_AUTHENTICATION"): assess(c)

    def test_hash_and_claim_still_require_independent_review(self):
        c = sample()
        c["official_raw_sha256"] = "a" * 64
        c["independent_pre_release_capture_utc"] = "2026-11-16T17:00:00Z"
        c["source_pit_authenticated"] = True
        r = assess(c)
        self.assertFalse(r["official_raw_pit_authenticated"])
        self.assertIsNone(r["forecast_point_estimate_mbu"])

    def test_cherry_picked_scenarios_rejected(self):
        c = sample(); c["illustrative_export_deltas_mbu"] = [0, 25, 100]
        with self.assertRaisesRegex(ValueError, "SCENARIO_GRID"): assess(c)

    def test_hindsight_outcome_injection_rejected(self):
        c = sample(); c["december_actual_ending_stocks_mbu"] = 0
        with self.assertRaisesRegex(ValueError, "INVALID_CONTRACT_KEYS"): assess(c)

    def test_wrong_source_rejected(self):
        c = sample(); c["numerical_source_url"] = "https://example.com"
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_MISMATCH"): assess(c)

    def test_impossible_week_value_rejected(self):
        c = sample(); c["weekly_inspections_mt"] = c["cumulative_inspections_mt"] + 1
        with self.assertRaisesRegex(ValueError, "WEEK_EXCEEDS_YEAR"): assess(c)

if __name__ == "__main__":
    unittest.main()

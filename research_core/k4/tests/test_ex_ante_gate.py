import unittest
from research_core.k4.ex_ante_gate import REQUIRED, SCHEMA, assess

def empty_case():
    c = {k: None for k in REQUIRED}
    c.update(schema=SCHEMA, hypothesis_id="H-CORN-001",
             event_id="USDA-WASDE-2026-11-10", release_scheduled_utc="2026-11-10T17:00:00Z",
             target="US_CORN_2026_27_ENDING_STOCKS_MBU",
             evaluation_rule="compare_frozen_forecast_to_frozen_consensus_before_official_outcome",
             frozen_before_release=False)
    return c

def filled_case():
    c = empty_case()
    c.update(forecast_created_utc="2026-11-10T15:00:00Z",
             forecast_inputs_cutoff_utc="2026-11-10T14:30:00Z",
             forecast_independent_capture_utc="2026-11-10T15:01:00Z",
             consensus_independent_capture_utc="2026-11-10T15:02:00Z",
             forecast_value_mbu=1800, consensus_value_mbu=1846,
             forecast_raw_sha256="a"*64, forecast_inputs_manifest_sha256="b"*64,
             consensus_raw_sha256="c"*64, forecast_method_id="frozen-v1",
             consensus_provider="TEST_ONLY", consensus_methodology="TEST_ONLY",
             frozen_before_release=True)
    return c

class ExAnteGateTests(unittest.TestCase):
    def test_missing_historical_prediction_blocks(self):
        x = assess(empty_case())
        self.assertEqual(x["status"], "BLOCKED_NO_EX_ANTE_EVIDENCE")
        self.assertIsNone(x["forecast_vs_consensus_delta_mbu"])
        self.assertFalse(x["trade_eligible"])

    def test_complete_fields_never_mean_independent_pit(self):
        x = assess(filled_case())
        self.assertEqual(x["status"], "REVIEW_CANDIDATE_NOT_PIT_CERTIFIED")
        self.assertEqual(x["forecast_vs_consensus_delta_mbu"], -46)
        self.assertFalse(x["independent_pit_certified"])
        self.assertFalse(x["predictive_edge_verified"])

    def test_late_forecast_rejected(self):
        c = filled_case(); c["forecast_created_utc"] = "2026-11-10T17:01:00Z"
        with self.assertRaisesRegex(ValueError, "POST_RELEASE"):
            assess(c)

    def test_late_survey_capture_rejected(self):
        c = filled_case(); c["consensus_independent_capture_utc"] = "2026-11-10T17:00:00Z"
        with self.assertRaisesRegex(ValueError, "POST_RELEASE"):
            assess(c)

    def test_inputs_cannot_be_newer_than_forecast(self):
        c = filled_case(); c["forecast_inputs_cutoff_utc"] = "2026-11-10T15:01:00Z"
        with self.assertRaisesRegex(ValueError, "INPUT_AFTER_FORECAST"):
            assess(c)

    def test_capture_cannot_predate_forecast(self):
        c = filled_case(); c["forecast_independent_capture_utc"] = "2026-11-10T14:00:00Z"
        with self.assertRaisesRegex(ValueError, "CAPTURE_BEFORE_FORECAST"):
            assess(c)

    def test_invalid_sha_rejected(self):
        c = filled_case(); c["forecast_raw_sha256"] = "not-hash"
        with self.assertRaisesRegex(ValueError, "INVALID_SHA256"):
            assess(c)

    def test_no_hindsight_result_allowed(self):
        c = filled_case(); c["official_outcome_mbu"] = 1758
        with self.assertRaisesRegex(ValueError, "INVALID_CONTRACT_KEYS"):
            assess(c)

    def test_freeze_flag_required(self):
        c = filled_case(); c["frozen_before_release"] = False
        self.assertEqual(assess(c)["status"], "BLOCKED_NO_EX_ANTE_EVIDENCE")

    def test_missing_consensus_capture_blocks(self):
        c = filled_case(); c["consensus_independent_capture_utc"] = None
        self.assertEqual(assess(c)["status"], "BLOCKED_NO_EX_ANTE_EVIDENCE")

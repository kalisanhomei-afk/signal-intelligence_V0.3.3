"""K4 H-CORN-001: accounting, missing data, no leakage, no false trading status."""
import copy
import json
from pathlib import Path
import unittest
from research_core.k4.hypothesis import ResearchGateError, evaluate_case

CASE = Path(__file__).resolve().parents[1] / "cases" / "2026-11-corn-wasde-retrospective.json"


def example():
    return json.loads(CASE.read_text(encoding="utf-8"))


class K4MechanismGateTests(unittest.TestCase):
    def test_real_reference_accounting_and_distinct_benchmarks(self):
        actual = evaluate_case(example())
        self.assertTrue(actual["stock_flow_identity_reconciled"])
        self.assertEqual(actual["reported_ending_stocks"], "1758")
        self.assertEqual(actual["consensus_ending_stocks"], "1846")
        self.assertEqual(actual["market_consensus_surprise_million_bushels"], "-88")
        self.assertEqual(actual["prior_month_change_million_bushels"], "-91")
        self.assertEqual(actual["stocks_to_use_percent"], "10.82")
        self.assertEqual(actual["mechanism_direction_benchmark_only"],
                         "UPWARD_PRICE_PRESSURE_RESEARCH_BASELINE_ONLY")

    def test_no_market_edge_or_retroactive_pit_claims(self):
        result = evaluate_case(example())
        self.assertFalse(result["trade_eligible"])
        self.assertFalse(result["historical_original_source_pit_certified"])
        self.assertFalse(result["event_study_eligible"])
        self.assertFalse(result["investment_edge_verified"])
        self.assertIsNone(result["strategy_return"])
        self.assertIsNone(result["price_effect_estimate"])
        self.assertIn("CONSENSUS_PRE_RELEASE_TIMESTAMP_NOT_INDEPENDENTLY_PROVEN",
                      result["missing_gates"])

    def test_stock_flow_supply_mismatch_fails_closed(self):
        case = example()
        case["reported"]["production"] = "15894"
        with self.assertRaisesRegex(ResearchGateError, "STOCK_FLOW_BALANCE_DOES_NOT_RECONCILE"):
            evaluate_case(case)

    def test_demand_components_mismatch_fails_closed(self):
        case = example()
        case["reported"]["exports"] = "3276"
        with self.assertRaisesRegex(ResearchGateError, "TOTAL_USE_COMPONENTS_DONT_RECONCILE"):
            evaluate_case(case)

    def test_wrong_marketing_year_not_silently_mixed(self):
        case = example()
        case["prior_report_marketing_year"] = "2025/26"
        with self.assertRaisesRegex(ResearchGateError, "PRIOR_REPORT_DIFFERENT_MARKETING_YEAR"):
            evaluate_case(case)

    def test_bad_marketing_year_invalid(self):
        case = example()
        case["marketing_year"] = "2026/28"
        with self.assertRaisesRegex(ResearchGateError, "MARKETING_YEAR_NOT_CONSECUTIVE"):
            evaluate_case(case)

    def test_missing_consensus_does_not_pretend_prior_change_is_surprise(self):
        case = example()
        case["reference"]["pre_report_consensus_ending_stocks"] = None
        result = evaluate_case(case)
        self.assertIsNone(result["market_consensus_surprise_million_bushels"])
        self.assertEqual(result["mechanism_direction_benchmark_only"],
                         "NOT_CALCULABLE_NO_CONSENSUS")
        self.assertIn("PRE_RELEASE_MARKET_CONSENSUS_UNAVAILABLE", result["missing_gates"])

    def test_consensus_negative_value_rejected(self):
        case = example()
        case["reference"]["pre_report_consensus_ending_stocks"] = "-1"
        with self.assertRaisesRegex(ResearchGateError, "INVALID_NONNEGATIVE"):
            evaluate_case(case)

    def test_consensus_zero_rejected(self):
        case = example()
        case["reference"]["pre_report_consensus_ending_stocks"] = "0"
        with self.assertRaisesRegex(ResearchGateError, "INVALID_NONNEGATIVE"):
            evaluate_case(case)

    def test_nonfinite_float_rejected(self):
        for bad in ("NaN", "Infinity", "-Infinity", 1758.0):
            with self.subTest(value=bad):
                case = example()
                case["reported"]["ending_stocks"] = bad
                with self.assertRaises(ResearchGateError):
                    evaluate_case(case)

    def test_same_metric_reverse_sign_is_downward_pressure_only(self):
        case = example()
        case["reference"]["pre_report_consensus_ending_stocks"] = "1700"
        out = evaluate_case(case)
        self.assertEqual(out["market_consensus_surprise_million_bushels"], "58")
        self.assertEqual(out["mechanism_direction_benchmark_only"],
                         "DOWNWARD_PRICE_PRESSURE_RESEARCH_BASELINE_ONLY")
        self.assertFalse(out["trade_eligible"])

    def test_zero_surprise_not_direction(self):
        case = example()
        case["reference"]["pre_report_consensus_ending_stocks"] = "1758"
        self.assertEqual(evaluate_case(case)["mechanism_direction_benchmark_only"],
                         "NEUTRAL_SURPRISE_RESEARCH_BASELINE_ONLY")

    def test_direct_claim_of_pit_certification_is_rejected(self):
        case = example()
        case["provenance"]["pit_certified"] = True
        with self.assertRaisesRegex(ResearchGateError, "UNREVIEWED_PIT_CERTIFICATION_CLAIM"):
            evaluate_case(case)

    def test_survey_recorded_after_schedule_is_not_pre_release(self):
        case = example()
        case["reference"]["survey_captured_at_utc"] = "2026-11-10T17:00:01Z"
        with self.assertRaisesRegex(ResearchGateError, "CONSENSUS_NOT_PROVEN_PRE_SCHEDULE"):
            evaluate_case(case)

    def test_survey_time_without_schedule_cannot_infer_time(self):
        case = example()
        case["reference"]["survey_captured_at_utc"] = "2026-11-10T16:00:00Z"
        case["provenance"]["scheduled_release_at_utc"] = None
        with self.assertRaisesRegex(ResearchGateError, "CONSENSUS_NOT_PROVEN_PRE_SCHEDULE"):
            evaluate_case(case)

    def test_source_observed_before_report_scheduled_time_rejected(self):
        case = example()
        case["provenance"]["report_observed_at_utc"] = "2026-11-10T16:30:00Z"
        with self.assertRaisesRegex(ResearchGateError, "REPORT_OBSERVATION_BEFORE_SCHEDULE"):
            evaluate_case(case)

    def test_missing_real_source_hash_not_invented(self):
        case = example()
        self.assertIsNone(case["provenance"]["official_source_sha256"])
        result = evaluate_case(case)
        self.assertIn("OFFICIAL_RAW_SOURCE_DIGEST_NOT_BOUND_IN_THIS_CASE", result["missing_gates"])

    def test_synthetic_fixtures_never_get_promoted(self):
        case = example()
        case["evidence_type"] = "SYNTHETIC_FIXTURE"
        out = evaluate_case(case)
        self.assertFalse(out["event_study_eligible"])
        self.assertFalse(out["trade_eligible"])

    def test_expected_commodity_and_units(self):
        for field, val in (("commodity", "Soybeans"), ("unit", "bushels")):
            with self.subTest(field=field):
                case = example()
                case[field] = val
                with self.assertRaises(ResearchGateError):
                    evaluate_case(case)

    def test_result_deterministic_and_no_price_labels(self):
        a = evaluate_case(example())
        b = evaluate_case(example())
        self.assertEqual(a, b)
        self.assertFalse("post_release_price" in a)
        self.assertFalse("profit" in a)


if __name__ == "__main__":
    unittest.main()

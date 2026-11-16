"""K4: independent poll-vintage sensitivity, provenance, and futures gating tests."""
import copy
import json
from pathlib import Path
import unittest

from research_core.k4.consensus_sensitivity import score_variants
from research_core.k4.hypothesis import ResearchGateError

SRC = Path(__file__).resolve().parents[1] / "cases" / "2026-11-consensus-source-variants.json"


def example():
    return json.loads(SRC.read_text(encoding="utf-8"))


class SurveyVintageGateTests(unittest.TestCase):
    def test_three_distinct_reported_consensus_surprises_and_stable_bounds(self):
        out = score_variants(example())
        self.assertEqual(out["survey_count"], 3)
        by_id = {r["survey_id"]: r["surprise_vs_survey_million_bushels"]
                 for r in out["survey_results"]}
        self.assertEqual(by_id, {
            "CME_EVENT_CALENDAR_ESTIMATES": "-88",
            "STONEX_NOV_05_AVERAGE": "-82",
            "DTN_DOW_JONES_NOV_06": "-68",
        })
        self.assertEqual(out["surprise_min_million_bushels"], "-88")
        self.assertEqual(out["surprise_max_million_bushels"], "-68")
        self.assertEqual(out["surprise_span_million_bushels"], "20")
        self.assertTrue(out["direction_consistent_among_reviewed_surveys"])
        self.assertFalse(out["survey_values_blended"])

    def test_monthly_wasde_revision_kept_separate_from_consensus_surprise(self):
        out = score_variants(example())
        self.assertEqual(out["USDA_month_on_month_change_million_bushels"], "-91")
        self.assertNotEqual(out["USDA_month_on_month_change_million_bushels"],
                            out["surprise_min_million_bushels"])

    def test_every_survey_always_unverified_asof_and_not_event_study(self):
        out = score_variants(example())
        self.assertEqual(out["independently_authenticated_pre_release_survey_count"], 0)
        self.assertFalse(out["historical_PIT_certified"])
        self.assertFalse(out["transaction_cost_adjusted_tradable"])
        self.assertFalse(out["price_response_estimated"])
        self.assertFalse(out["predictive_incremental_edge_validated"])
        self.assertEqual(out["historical_intraday_price_rows_acquired"], 0)
        self.assertTrue(all(not r["independently_authenticated_pre_release_vintage"]
                            and not r["event_study_eligible"] for r in out["survey_results"]))

    def test_no_cherry_picking_or_combining_surveys(self):
        bad = example()
        bad["survey_selection_policy"] = "TAKE_AVERAGE_OR_LARGEST_SURPRISE"
        with self.assertRaisesRegex(ResearchGateError, "SURVEY_CHERRY_PICK"):
            score_variants(bad)

    def test_lost_survey_is_not_silently_filled(self):
        bad = example()
        bad["survey_observation_vintages"].pop()
        with self.assertRaisesRegex(ResearchGateError, "REQUIRES_THREE"):
            score_variants(bad)

    def test_duplicate_survey_id_is_rejected(self):
        bad = example()
        bad["survey_observation_vintages"][2]["survey_id"] = \
            bad["survey_observation_vintages"][1]["survey_id"]
        with self.assertRaisesRegex(ResearchGateError, "DUPLICATE_OR_EMPTY"):
            score_variants(bad)

    def test_fictitious_archival_timestamp_not_promoted(self):
        for key, value in (
            ("independent_pre_release_capture_body_sha256", "f" * 64),
            ("independent_pre_release_capture_at_utc", "2026-11-06T10:00:00Z"),
        ):
            bad = example()
            bad["survey_observation_vintages"][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                    ResearchGateError, "EXTERNAL_ADJUDICATION"):
                score_variants(bad)

    def test_publisher_dateline_is_not_same_as_immutable_capture(self):
        bad = example()
        bad["survey_observation_vintages"][0]["time_evidence_quality"] = "VERIFIED_PUBLIC_TIMESTAMP"
        with self.assertRaisesRegex(ResearchGateError, "UNSUPPORTED_PROVENANCE_PROMOTION"):
            score_variants(bad)

    def test_source_type_and_identity_must_remain_separate(self):
        bad = example()
        bad["survey_observation_vintages"][0]["survey_underlying_vendor_identity"] = None
        with self.assertRaisesRegex(ResearchGateError, "MISSING_SOURCE_SURVEY_IDENTITY"):
            score_variants(bad)

    def test_publisher_date_after_release_fails_closed(self):
        bad = example()
        bad["survey_observation_vintages"][1]["publisher_article_date_claim"] = "2026-11-12"
        with self.assertRaisesRegex(ResearchGateError, "PUBLISHER_DATELINE_AFTER_RELEASE"):
            score_variants(bad)

    def test_nonfinite_or_float_or_negative_consensus_rejected(self):
        for v in (-1, "-1", "NaN", "Infinity", 1846.0):
            bad = example()
            bad["survey_observation_vintages"][0]["reported_ending_stocks"] = v
            with self.subTest(v=v), self.assertRaises(ResearchGateError):
                score_variants(bad)

    def test_invalid_marketing_year_cannot_mix_old_crop_and_new_crop(self):
        bad = example()
        bad["marketing_year"] = "2025/26"
        with self.assertRaisesRegex(ResearchGateError, "WRONG_MARKETING_YEAR"):
            score_variants(bad)

    def test_wrong_symbol_cannot_substitute_continuous_futures(self):
        bad = example()
        bad["price_data_feasibility"]["potential_contract_symbol"] = "ZC.cont"
        with self.assertRaisesRegex(ResearchGateError, "EXACT_CB0T_CONTRACT_NOT_FIXED"):
            score_variants(bad)

    def test_price_data_cannot_be_falsely_set_as_acquired(self):
        bad = example()
        bad["price_data_feasibility"]["actual_intraday_records_acquired"] = 100
        with self.assertRaisesRegex(ResearchGateError, "PRICE_HISTORY_NOT_YET_AUDITED"):
            score_variants(bad)

    def test_bid_ask_execution_not_implied_from_ohlcv(self):
        bad = example()
        bad["price_data_feasibility"]["orderbook_bid_ask_executability_proven"] = True
        with self.assertRaisesRegex(ResearchGateError, "UNVERIFIED_PRICE_OR_EXECUTABILITY"):
            score_variants(bad)

    def test_cme_contract_tick_and_size_must_match(self):
        bad = example()
        bad["price_data_feasibility"]["contract_unit_bushels"] = "1000"
        with self.assertRaisesRegex(ResearchGateError, "CME_CONTRACT_SPECIFICATION_CHANGED"):
            score_variants(bad)

    def test_expected_report_and_utc_release_schedule(self):
        bad = example()
        bad["release_schedule_utc"] = "2026-11-10T16:00:00Z"
        with self.assertRaisesRegex(ResearchGateError, "INCORRECT_OFFICIAL_RELEASE_SCHEDULE"):
            score_variants(bad)

    def test_survey_outcome_deterministic_regardless_order_without_source_mixing(self):
        first = score_variants(example())
        flipped = example()
        flipped["survey_observation_vintages"].reverse()
        second = score_variants(flipped)
        self.assertEqual(first["surprise_min_million_bushels"],
                         second["surprise_min_million_bushels"])
        self.assertEqual(first["surprise_max_million_bushels"],
                         second["surprise_max_million_bushels"])
        self.assertEqual({r["survey_id"]: r["surprise_vs_survey_million_bushels"]
                          for r in first["survey_results"]},
                         {r["survey_id"]: r["surprise_vs_survey_million_bushels"]
                          for r in second["survey_results"]})


if __name__ == "__main__":
    unittest.main()

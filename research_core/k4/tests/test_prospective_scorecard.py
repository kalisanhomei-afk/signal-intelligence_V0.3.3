"""K4.10 prospective scoring contract, no fake consensus/outcome or PIT promotion."""
import json
from pathlib import Path
import unittest

from research_core.k4.prospective_scorecard import (
    CONTRACT,EMPTY_EVIDENCE,FROZEN,historical_baseline,score
)

def load():
    return (json.loads(CONTRACT.read_text(encoding="utf-8")),
            json.loads(EMPTY_EVIDENCE.read_text(encoding="utf-8")),
            FROZEN.read_bytes())

def synthetic_evidence():
    contract,evidence,raw=load()
    evidence.update({
        "consensus_value_mbu":1725,
        "consensus_provider":"TEST_PROVIDER_NOT_AN_ACTUAL_DECEMBER_CONSENSUS",
        "consensus_methodology":"synthetic named survey test case",
        "consensus_source_url":"https://example.org/consensus-fake-test",
        "consensus_publication_utc":"2026-12-09T12:00:00Z",
        "consensus_capture_utc":"2026-12-09T12:01:00Z",
        "consensus_raw_sha256":"a"*64,
        "official_value_mbu":1700,
        "official_source_url":"https://www.usda.gov/example/synthetic-future-report",
        "official_capture_utc":"2026-12-10T17:01:00Z",
        "official_raw_sha256":"b"*64
    })
    return contract,evidence,raw

class K410HistoricalAndProspectiveTests(unittest.TestCase):
    def test_historical_persistence_reference_exact(self):
        x=historical_baseline()
        self.assertEqual(x["label_years"],9)
        self.assertEqual(x["absolute_error_mae_mbu"],"57.78")
        self.assertEqual(x["median_absolute_error_mbu"],"45.00")
        self.assertEqual(x["root_mean_squared_error_mbu"],"85.89")
        self.assertEqual(x["signed_error_actual_minus_forecast_mean_mbu"],"-31.11")
        self.assertEqual(x["max_abs_error_mbu"],"200.00")
        self.assertEqual((x["no_change_years"],x["revision_up_years"],x["revision_down_years"]),(3,2,4))
        self.assertFalse(x["historical_predictors_pit_verified"])
        self.assertFalse(x["sample_out_of_time_validation_completed"])

    def test_true_december_evidence_remains_null(self):
        c,e,raw=load()
        x=score(c,e,raw)
        self.assertEqual(x["status"],"WAITING_FOR_DECEMBER_PRE_RELEASE_CONSENSUS_AND_USDA_OUTCOME")
        self.assertEqual(len(x["missing_evidence"]),11)
        self.assertIsNone(x["v0_abs_error_mbu"])
        self.assertIsNone(x["consensus_abs_error_mbu"])
        self.assertIsNone(x["model_v1_abs_error_mbu"])
        self.assertFalse(x["trade_eligible"])

    def test_locked_forecast_bytes_must_match_hash(self):
        c,e,raw=load()
        with self.assertRaisesRegex(ValueError,"FROZEN_FORECAST_BYTES_TAMPERED"):
            score(c,e,raw+b"tamper")

    def test_frozen_value_cannot_change(self):
        c,e,raw=load()
        c["forecast_value_mbu"]=1759
        with self.assertRaisesRegex(ValueError,"FROZEN_CONTRACT_MISMATCH"):
            score(c,e,raw)

    def test_synthetic_provenance_only_allows_descriptive_scoring(self):
        c,e,raw=synthetic_evidence()
        x=score(c,e,raw)
        self.assertEqual(x["status"],"DESCRIPTIVE_SINGLE_EVENT_COMPARISON_REQUIRES_INDEPENDENT_PIT_REVIEW")
        self.assertEqual(x["v0_abs_error_mbu"],"58.00")
        self.assertEqual(x["consensus_abs_error_mbu"],"25.00")
        self.assertEqual(x["v0_minus_consensus_abs_error_mbu"],"33.00")
        self.assertFalse(x["prospective_one_event_comparison_is_predictive_edge_proof"])
        self.assertFalse(x["trading_edge_verified"])
        self.assertFalse(x["independent_pit_source_certification"])

    def test_consensus_after_release_rejected(self):
        c,e,raw=synthetic_evidence()
        e["consensus_capture_utc"]="2026-12-10T17:00:00Z"
        with self.assertRaisesRegex(ValueError,"CONSENSUS_NOT_PROVEN_CAPTURED_BEFORE_EVENT"):
            score(c,e,raw)

    def test_consensus_fake_publication_after_capture_rejected(self):
        c,e,raw=synthetic_evidence()
        e["consensus_publication_utc"]="2026-12-09T13:00:00Z"
        with self.assertRaisesRegex(ValueError,"CONSENSUS_NOT_PROVEN_CAPTURED_BEFORE_EVENT"):
            score(c,e,raw)

    def test_official_future_outcome_cannot_be_captured_before_release(self):
        c,e,raw=synthetic_evidence()
        e["official_capture_utc"]="2026-12-10T16:59:59Z"
        with self.assertRaisesRegex(ValueError,"OFFICIAL_OUTCOME_CAPTURED_BEFORE_EVENT"):
            score(c,e,raw)

    def test_wrong_official_source_rejected(self):
        c,e,raw=synthetic_evidence()
        e["official_source_url"]="https://example.org/not-usda"
        with self.assertRaisesRegex(ValueError,"UNRECOGNIZED_OFFICIAL_USDA_HOST"):
            score(c,e,raw)

    def test_unverified_hash_and_missing_methods_rejected(self):
        c,e,raw=synthetic_evidence()
        e["consensus_raw_sha256"]="unknown"
        with self.assertRaisesRegex(ValueError,"INVALID_SOURCE_SHA256"):
            score(c,e,raw)
        c,e,raw=synthetic_evidence()
        e["consensus_provider"]=""
        with self.assertRaisesRegex(ValueError,"MISSING_CONSENSUS_PROVENANCE"):
            score(c,e,raw)

    def test_outcome_and_consensus_are_not_invented_by_partial_inputs(self):
        c,e,raw=synthetic_evidence()
        e["official_value_mbu"]=None
        x=score(c,e,raw)
        self.assertFalse(x["evidence_complete"])
        self.assertIsNone(x["v0_abs_error_mbu"])
        self.assertIn("official_value_mbu",x["missing_evidence"])

    def test_hindsight_injection_to_evidence_is_rejected(self):
        c,e,raw=load()
        e["best_post_event_entry_price"]=0
        with self.assertRaisesRegex(ValueError,"EVIDENCE_CONTRACT_KEYS_MISMATCH"):
            score(c,e,raw)

    def test_nonnumeric_forecast_or_nan_outcome_rejected(self):
        c,e,raw=synthetic_evidence()
        e["official_value_mbu"]="NaN"
        with self.assertRaisesRegex(ValueError,"INVALID_QUANTITY"):
            score(c,e,raw)

    def test_model_v1_not_synthesized(self):
        c,e,raw=load()
        c["has_separately_frozen_v1"]=True
        with self.assertRaisesRegex(ValueError,"FROZEN_CONTRACT_MISMATCH"):
            score(c,e,raw)

if __name__=="__main__":
    unittest.main()

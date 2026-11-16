"""No synthetic evidence can be treated as a verified event study."""
import json
from pathlib import Path
import unittest
from research_core.k4.event_study_gate import FIELDS, assess

CASE = Path("research_core/k4/cases/2026-11-10-event-study-evidence.json")
def baseline():
    return json.loads(CASE.read_text(encoding="utf-8"))

class StudyGateTests(unittest.TestCase):
    def test_actual_case_stays_blocked(self):
        r = assess(baseline())
        self.assertEqual(len(r["missing_evidence"]), len(FIELDS))
        self.assertEqual(r["status"], "BLOCKED_MISSING_EVIDENCE")
        self.assertFalse(r["formal_event_study_eligible"])
        self.assertFalse(r["trade_eligible"])
        self.assertIsNone(r["strategy_return"])

    def test_incorrect_contract_fails(self):
        d=baseline(); d["symbol"]="ZCH7"
        with self.assertRaisesRegex(ValueError,"CONTRACT_MISMATCH"): assess(d)

    def test_schema_and_fields_fail_closed(self):
        d=baseline(); del d["evidence"]["survey_raw_sha256"]
        with self.assertRaisesRegex(ValueError,"EVIDENCE_CONTRACT"): assess(d)

    def test_late_survey_refused(self):
        d=baseline(); d["evidence"]["survey_independent_capture_utc"]="2026-11-10T17:00:00Z"
        with self.assertRaisesRegex(ValueError,"SURVEY_CAPTURE_NOT_PRE_RELEASE"): assess(d)

    def test_pre_release_official_capture_refused(self):
        d=baseline(); d["evidence"]["official_response_finished_utc"]="2026-11-10T16:59:59Z"
        with self.assertRaisesRegex(ValueError,"OFFICIAL_CAPTURE_BEFORE_RELEASE"): assess(d)

    def test_post_price_before_official_observation_refused(self):
        d=baseline(); d["evidence"]["official_response_finished_utc"]="2026-11-10T17:02:00Z"
        d["evidence"]["same_contract_post_observation_quote_utc"]="2026-11-10T17:01:59Z"
        with self.assertRaisesRegex(ValueError,"POST_PRICE_PRECEDES"): assess(d)

    def test_bad_sha_rejected(self):
        d=baseline(); d["evidence"]["futures_raw_sha256"]="FAKE"
        with self.assertRaisesRegex(ValueError,"INVALID_RAW_SHA256"): assess(d)

    def test_mere_populated_values_cannot_certify(self):
        d=baseline()
        for k in FIELDS:
            d["evidence"][k]="a"*64 if k.endswith("_sha256") else "UNVERIFIED_VENDOR_ASSERTION"
        d["evidence"]["survey_independent_capture_utc"]="2026-11-10T16:30:00Z"
        d["evidence"]["official_response_finished_utc"]="2026-11-10T17:01:00Z"
        d["evidence"]["same_contract_pre_release_quote_utc"]="2026-11-10T16:59:00Z"
        d["evidence"]["same_contract_post_observation_quote_utc"]="2026-11-10T17:03:00Z"
        r=assess(d)
        self.assertEqual(r["status"],"CANDIDATE_REQUIRES_INDEPENDENT_REVIEW")
        self.assertFalse(r["independently_authenticated"])
        self.assertFalse(r["formal_event_study_eligible"])
        self.assertFalse(r["cost_adjusted_edge_verified"])
        self.assertFalse(r["trade_eligible"])

if __name__=="__main__":
    unittest.main()

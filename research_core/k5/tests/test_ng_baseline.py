"""K5 first real EIA weekly forecast: no lookahead, fake data or trading promotion."""
import copy
import json
from pathlib import Path
import unittest
from research_core.k5.ng_baseline import compute,score

ROOT=Path(__file__).resolve().parents[1]/"cases"
INPUT=ROOT/"2026-11-19-eia-prior-week-input.json"
FROZEN=ROOT/"2026-11-19-eia-frozen-v0-forecast.json"
PENDING=ROOT/"2026-11-19-eia-outcome-pending.json"

def load():
    return json.loads(INPUT.read_text(encoding="utf-8"))

class FirstNaturalGasBaselineTests(unittest.TestCase):
    def test_persisted_forecast_reproducible(self):
        expected=json.loads(FROZEN.read_text(encoding="utf-8"))
        self.assertEqual(compute(load()),expected)
        self.assertEqual(expected["forecast_net_change_bcf"],61)
        self.assertEqual(expected["baseline_vs_5yr_stocks_bcf"],75)

    def test_no_trading_or_invented_consensus(self):
        x=compute(load())
        self.assertFalse(x["trade_eligible"])
        self.assertFalse(x["independent_pit_certified"])
        self.assertIsNone(x["market_consensus_bcf"])
        self.assertIsNone(x["actual_next_release_net_change_bcf"])

    def test_do_not_invent_raw_source_hash(self):
        x=compute(load())
        self.assertIsNone(x["source_raw_sha256"])
        self.assertFalse(x["source_raw_bytes_verified"])

    def test_previous_week_storage_balance_enforced(self):
        x=copy.deepcopy(load())
        x["prior_lower48_storage_bcf"]+=1
        with self.assertRaisesRegex(ValueError,"STORAGE_FLOW_MISMATCH"):
            compute(x)

    def test_post_release_lookahead_forbidden(self):
        x=copy.deepcopy(load())
        x["source_report_release_utc_claim"]="2026-11-20T10:00:00Z"
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD"):
            compute(x)

    def test_fake_original_byte_status_forbidden(self):
        x=copy.deepcopy(load())
        x["source_raw_bytes_verified"]=True
        with self.assertRaisesRegex(ValueError,"MODEL_OR_PROVENANCE"):
            compute(x)

    def test_forged_previous_week_change_forbidden(self):
        x=copy.deepcopy(load())
        x["source_reported_net_change_bcf"]=70
        with self.assertRaisesRegex(ValueError,"STORAGE_FLOW_MISMATCH"):
            compute(x)

    def test_unrecognized_target_forbidden(self):
        x=copy.deepcopy(load())
        x["target"]="STORAGE_TOTAL"
        with self.assertRaisesRegex(ValueError,"MODEL_OR_PROVENANCE"):
            compute(x)

    def test_future_outcome_remains_unknown(self):
        frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
        outcome=json.loads(PENDING.read_text(encoding="utf-8"))
        result=score(frozen,outcome)
        self.assertEqual(result["status"],"WAITING_FOR_REAL_POST_RELEASE_EIA_OUTCOME")
        self.assertIsNone(result["absolute_error_bcf"])
        self.assertFalse(result["trade_eligible"])

    def test_future_outcome_capture_before_release_forbidden(self):
        x={"event_id":"EIA-WNGSR-2026-11-19","actual_net_change_bcf":40,
           "source_raw_sha256":"a"*64,"source_capture_utc":"2026-11-19T15:00:00Z"}
        f=json.loads(FROZEN.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError,"OUTCOME_PRECEDES"):
            score(f,x)

    def test_synthetic_post_release_only_descriptive(self):
        x={"event_id":"EIA-WNGSR-2026-11-19","actual_net_change_bcf":40,
           "source_raw_sha256":"a"*64,"source_capture_utc":"2026-11-19T15:31:00Z"}
        f=json.loads(FROZEN.read_text(encoding="utf-8"))
        result=score(f,x)
        self.assertEqual(result["absolute_error_bcf"],21)
        self.assertFalse(result["trade_eligible"])
        self.assertFalse(result["independent_pit_certified"])

if __name__=="__main__":
    unittest.main()

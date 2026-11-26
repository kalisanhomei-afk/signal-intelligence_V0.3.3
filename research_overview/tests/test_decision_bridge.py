"""No-trading market bridge: synthetic bad inputs must not be promoted."""
import copy
import json
from pathlib import Path
import unittest

from research_overview.validate import HERE, load_portfolio
from research_overview.decision_bridge import assess_bridge, EXPECTED_BLOCKERS

class MarketBridgeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.cards = load_portfolio()
        cls.bridge=json.loads((HERE/"market_decision_bridge.json").read_text(encoding="utf-8"))

    def mutate(self):
        return copy.deepcopy(self.bridge)

    def test_current_two_hypotheses_both_blocked(self):
        result=assess_bridge(self.manifest,self.cards,self.bridge)
        self.assertEqual(result["result_count"],2)
        self.assertFalse(result["trade_eligible"])
        self.assertFalse(result["auto_order_execution_present"])
        for c in result["hypotheses"]:
            self.assertEqual(c["status"],"NO_GO_DESIGN_ONLY")
            self.assertEqual(tuple(c["blocking_gates"]),EXPECTED_BLOCKERS)
            self.assertFalse(c["trade_eligible"])

    def test_indicative_calendar_not_a_certified_consensus(self):
        self.assertEqual(self.cards[1]["indicative_external_forecasts"][0]["value"],69)
        self.assertEqual(self.cards[1]["market_consensus"]["status"],"NOT_VERIFIED")
        x=self.mutate()
        x["hypotheses"][1]["expectations"]["value"]=69
        with self.assertRaisesRegex(ValueError,"MARKET_CONSENSUS_PREMATURELY_PROMOTED"):
            assess_bridge(self.manifest,self.cards,x)

    def test_no_fictional_instrument_symbol_or_contract(self):
        x=self.mutate()
        x["hypotheses"][0]["instrument"]["symbol"]="SYNTHETIC_TEST_CONTRACT"
        with self.assertRaisesRegex(ValueError,"TRADABLE_INSTRUMENT_UNVERIFIED"):
            assess_bridge(self.manifest,self.cards,x)

    def test_no_fake_pre_release_quote(self):
        x=self.mutate()
        x["hypotheses"][1]["market_prices"]["pre_event_quote"]=3.45
        with self.assertRaisesRegex(ValueError,"MARKET_PRICE_WAS_INVENTED"):
            assess_bridge(self.manifest,self.cards,x)

    def test_no_fake_return_after_future_outcome(self):
        x=self.mutate()
        x["hypotheses"][1]["price_effect"]["estimated_net_return"]=0.15
        with self.assertRaisesRegex(ValueError,"MARKET_EDGE_PREMATURELY_PROMOTED"):
            assess_bridge(self.manifest,self.cards,x)

    def test_no_hindsight_calibration(self):
        x=self.mutate()
        x["hypotheses"][0]["price_effect"]["out_of_sample_events"]=100
        with self.assertRaisesRegex(ValueError,"MARKET_EDGE_PREMATURELY_PROMOTED"):
            assess_bridge(self.manifest,self.cards,x)

    def test_no_unverified_risk_limits_or_costs(self):
        x=self.mutate()
        x["hypotheses"][1]["portfolio_risk"]["transaction_costs_verified"]=True
        with self.assertRaisesRegex(ValueError,"RISK_CONTROLS_NOT_AUDITED"):
            assess_bridge(self.manifest,self.cards,x)

    def test_no_order_or_live_position(self):
        x=self.mutate()
        x["hypotheses"][0]["decision"]["approved_to_trade"]=True
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_TRADE_DECISION"):
            assess_bridge(self.manifest,self.cards,x)

    def test_no_silent_event_or_unit_conversion(self):
        x=self.mutate()
        x["hypotheses"][0]["forecast_unit"]="Bcf"
        with self.assertRaisesRegex(ValueError,"BRIDGE_METRIC_OR_EVENT_MISMATCH"):
            assess_bridge(self.manifest,self.cards,x)

    def test_reject_duplicate_hypothesis(self):
        x=self.mutate()
        x["hypotheses"][1]["hypothesis_id"]="H-CORN-001"
        with self.assertRaisesRegex(ValueError,"BRIDGE_DUPLICATE_OR_UNKNOWN_EVENT"):
            assess_bridge(self.manifest,self.cards,x)

    def test_design_snapshot_cannot_claim_live_market_data(self):
        x=self.mutate()
        x["actual_market_data_integrated"]=True
        with self.assertRaisesRegex(ValueError,"FAKE_MARKET_INTEGRATION"):
            assess_bridge(self.manifest,self.cards,x)

    def test_allows_only_same_snapshot_date(self):
        x=self.mutate()
        x["snapshot_date"]="2026-11-20"
        with self.assertRaisesRegex(ValueError,"BRIDGE_IS_NOT_DESIGN_SNAPSHOT"):
            assess_bridge(self.manifest,self.cards,x)

if __name__=="__main__":
    unittest.main()

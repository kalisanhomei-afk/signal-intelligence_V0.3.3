"""SIGNAL v0.1 architectural gate between research and any future investment decision.

It intentionally does NOT score, price, trade, or import market data. Every
missing piece stays explicit instead of being interpreted as zero, and no
real or simulated result can authorize orders through this interface.
"""
from __future__ import annotations

import json
from pathlib import Path
from research_overview.validate import HERE, require

PATH = HERE / "market_decision_bridge.json"

EXPECTED_BLOCKERS = (
    "PRE_EVENT_MARKET_EXPECTATION_NOT_VERIFIED",
    "EXACT_TRADABLE_CONTRACT_NOT_MAPPED",
    "SAME_CONTRACT_MARKET_QUOTES_NOT_CAPTURED",
    "SURPRISE_TO_PRICE_RELATION_NOT_VALIDATED",
    "EXECUTION_AND_PORTFOLIO_RISK_NOT_VALIDATED"
)

def all_null(fields, keys):
    return all(fields.get(k) is None for k in keys)

def assess_bridge(manifest, cards, bridge):
    require(isinstance(bridge, dict) and set(bridge) == {
        "schema", "snapshot_date", "stage", "purpose",
        "actual_market_data_integrated", "no_trade_enforced", "hypotheses"
    }, "BRIDGE_SCHEMA_KEYS")
    require(bridge["schema"] == "signal-market-decision-bridge-design-v0.1" and
            bridge["snapshot_date"] == manifest["snapshot_date"] and
            bridge["stage"] == "ARCHITECTURE_ONLY", "BRIDGE_IS_NOT_DESIGN_SNAPSHOT")
    require(bridge["actual_market_data_integrated"] is False and
            bridge["no_trade_enforced"] is True, "FAKE_MARKET_INTEGRATION")
    require(isinstance(bridge["hypotheses"], list) and
            len(bridge["hypotheses"]) == len(cards), "BRIDGE_COVERAGE")
    lookup = {c["hypothesis_id"]: c for c in cards}
    seen = set()
    results = []
    for item in bridge["hypotheses"]:
        require(isinstance(item, dict) and set(item) == {
            "hypothesis_id", "event_id", "forecast_unit", "expectations",
            "instrument", "market_prices", "price_effect", "portfolio_risk", "decision"
        }, "BRIDGE_EVENT_SCHEMA")
        ident = item["hypothesis_id"]
        require(ident in lookup and ident not in seen, "BRIDGE_DUPLICATE_OR_UNKNOWN_EVENT")
        seen.add(ident)
        card = lookup[ident]
        require(item["event_id"] == card["event_id"] and
                item["forecast_unit"] == card["unit"], "BRIDGE_METRIC_OR_EVENT_MISMATCH")
        expectation = item["expectations"]
        require(expectation["status"] == "UNVERIFIED_PRE_EVENT_CONSENSUS" and
                all_null(expectation, ["value", "source_url", "source_capture_utc", "source_sha256"]) and
                card["market_consensus"]["status"] == "NOT_VERIFIED",
                "MARKET_CONSENSUS_PREMATURELY_PROMOTED")
        instrument = item["instrument"]
        require(instrument["status"] == "UNMAPPED" and
                all_null(instrument, ["exchange", "symbol", "contract_month",
                                      "contract_size", "quote_unit", "currency", "roll_method"]),
                "TRADABLE_INSTRUMENT_UNVERIFIED")
        prices = item["market_prices"]
        require(prices["status"] == "NO_VERIFIED_PRICES" and
                all_null(prices, ["pre_event_quote", "pre_event_capture_utc",
                                  "post_event_quote", "post_event_capture_utc",
                                  "quote_source_sha256"]), "MARKET_PRICE_WAS_INVENTED")
        effect = item["price_effect"]
        require(effect["status"] == "NOT_CALIBRATED" and
                all_null(effect, ["ex_ante_surprise", "price_response_coefficient",
                                  "estimated_net_return"]) and
                type(effect["out_of_sample_events"]) is int and
                effect["out_of_sample_events"] == 0,
                "MARKET_EDGE_PREMATURELY_PROMOTED")
        risk = item["portfolio_risk"]
        require(risk["status"] == "NOT_EVALUATED" and
                risk["transaction_costs_verified"] is False and
                risk["liquidity_verified"] is False and
                risk["margin_risk_verified"] is False and
                risk["exposure_limit"] is None, "RISK_CONTROLS_NOT_AUDITED")
        decision = item["decision"]
        require(decision == {
            "status": "NO_GO", "proposed_position": None, "approved_to_trade": False
        } and card["decision"]["trade_eligible"] is False,
                "UNAUTHORIZED_TRADE_DECISION")
        results.append({
            "hypothesis_id": ident,
            "event_id": item["event_id"],
            "status": "NO_GO_DESIGN_ONLY",
            "blocking_gates": list(EXPECTED_BLOCKERS),
            "next_eligible_action": "PRESERVE_EVENT_EVIDENCE_AND_VALIDATE_V0",
            "trade_eligible": False
        })
    require(seen == set(lookup), "BRIDGE_MISSING_HYPOTHESES")
    return {
        "schema": "signal-market-decision-bridge-audit-v0.1",
        "snapshot_date": bridge["snapshot_date"],
        "stage": "ARCHITECTURE_ONLY",
        "result_count": len(results),
        "hypotheses": results,
        "trade_eligible": False,
        "auto_order_execution_present": False,
        "is_live_or_historical_backtest": False
    }

def audit_from_repo(root=HERE):
    from research_overview.validate import load_portfolio
    manifest, cards = load_portfolio(root)
    bridge = json.loads((Path(root) / "market_decision_bridge.json").read_text(encoding="utf-8"))
    return assess_bridge(manifest, cards, bridge)

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = audit_from_repo()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": report["stage"],
                      "hypotheses": report["result_count"], "trade_eligible": False}))

if __name__ == "__main__":
    main()

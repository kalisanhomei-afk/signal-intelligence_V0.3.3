"""K4.5 deterministic pre-WASDE persistence baseline. No data fetch or trading."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path

SCHEMA = "signal-k45-dec-corn-baseline-input-v1"
REQUIRED = {"schema", "event_id", "release_scheduled_utc", "created_utc", "input_cutoff_utc", "source_release_scheduled_utc", "source_url", "source_raw_sha256", "marketing_year", "baseline_mbu", "source_components_mbu", "model_id"}
COMPONENTS = {"beginning_stocks", "production", "imports", "feed_residual", "food_seed_industrial", "exports", "ending_stocks"}
MODEL_ID = "USDA_PREVIOUS_WASDE_PERSISTENCE_V0"

def utc(s):
    if not isinstance(s, str) or not s.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    try:
        return datetime.fromisoformat(s[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("INVALID_UTC") from exc

def forecast(c):
    if not isinstance(c, dict) or set(c) != REQUIRED:
        raise ValueError("INVALID_INPUT_CONTRACT")
    if c["schema"] != SCHEMA or c["model_id"] != MODEL_ID or c["marketing_year"] != "2026/27":
        raise ValueError("MODEL_OR_YEAR_MISMATCH")
    if c["event_id"] != "USDA-WASDE-2026-12-10":
        raise ValueError("EVENT_MISMATCH")
    if c["source_url"] != "https://esmis.nal.usda.gov/sites/default/release-files/796142/wasde1126.txt":
        raise ValueError("UNRECOGNIZED_OFFICIAL_SOURCE")
    if c["source_raw_sha256"] is not None:
        if not isinstance(c["source_raw_sha256"], str) or len(c["source_raw_sha256"]) != 64 or any(x not in "0123456789abcdef" for x in c["source_raw_sha256"]):
            raise ValueError("SOURCE_HASH_INVALID")
    release = utc(c["release_scheduled_utc"])
    created = utc(c["created_utc"])
    cutoff = utc(c["input_cutoff_utc"])
    source_released = utc(c["source_release_scheduled_utc"])
    if not source_released <= cutoff <= created < release:
        raise ValueError("LOOKAHEAD_OR_TIME_ORDER")
    if not isinstance(c["source_components_mbu"], dict) or set(c["source_components_mbu"]) != COMPONENTS:
        raise ValueError("COMPONENT_CONTRACT")
    x = c["source_components_mbu"]
    if any(type(v) is not int or v < 0 for v in x.values()):
        raise ValueError("COMPONENT_VALUE")
    derived = x["beginning_stocks"] + x["production"] + x["imports"] - x["feed_residual"] - x["food_seed_industrial"] - x["exports"]
    if derived != x["ending_stocks"] or c["baseline_mbu"] != derived or type(c["baseline_mbu"]) is not int:
        raise ValueError("SUPPLY_DEMAND_MISMATCH")
    return {
        "schema": "signal-k45-ex-ante-forecast-v1",
        "event_id": c["event_id"],
        "target": "US_CORN_2026_27_ENDING_STOCKS_MBU",
        "release_scheduled_utc": c["release_scheduled_utc"],
        "forecast_created_utc": c["created_utc"],
        "forecast_inputs_cutoff_utc": c["input_cutoff_utc"],
        "method_id": MODEL_ID,
        "forecast_value_mbu": derived,
        "comparison": "prior_USDA_only_not_independent_alpha",
        "source_url": c["source_url"],
        "source_raw_sha256": c["source_raw_sha256"],
        "source_content_independently_authenticated": False,
        "model_adjustments_independently_evidenced": False,
        "consensus_value_mbu": None,
        "consensus_independently_pit_verified": False,
        "decision": "PERSISTENCE_BASELINE_FROZEN_CANDIDATE_NOT_SIGNAL",
        "trade_eligible": False,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = forecast(json.loads(a.case.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["decision"], "forecast_mbu": result["forecast_value_mbu"], "trade_eligible": False}))

if __name__ == "__main__":
    main()

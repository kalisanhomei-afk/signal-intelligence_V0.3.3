"""K4.5 ex-ante preregistration gate. Never manufactures historical forecasts."""
from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path

SCHEMA = "signal-k45-ex-ante-registration-v1"
REQUIRED = {
    "schema", "hypothesis_id", "event_id", "release_scheduled_utc",
    "forecast_created_utc", "forecast_raw_sha256", "forecast_value_mbu",
    "forecast_method_id", "forecast_inputs_cutoff_utc",
    "forecast_inputs_manifest_sha256", "forecast_independent_capture_utc",
    "consensus_value_mbu", "consensus_raw_sha256", "consensus_provider",
    "consensus_independent_capture_utc", "consensus_methodology",
    "target", "evaluation_rule", "frozen_before_release",
}
HASHES = ("forecast_raw_sha256", "forecast_inputs_manifest_sha256", "consensus_raw_sha256")
TIMES = ("release_scheduled_utc", "forecast_created_utc", "forecast_inputs_cutoff_utc",
         "forecast_independent_capture_utc", "consensus_independent_capture_utc")

def parse_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("INVALID_UTC") from exc
    if result.utcoffset().total_seconds() != 0:
        raise ValueError("UTC_OFFSET_INVALID")
    return result

def assess(case):
    if not isinstance(case, dict) or set(case) != REQUIRED:
        raise ValueError("INVALID_CONTRACT_KEYS")
    if case["schema"] != SCHEMA or case["hypothesis_id"] != "H-CORN-001":
        raise ValueError("INVALID_SCHEMA_OR_HYPOTHESIS")
    if case["target"] != "US_CORN_2026_27_ENDING_STOCKS_MBU":
        raise ValueError("TARGET_MISMATCH")
    if case["evaluation_rule"] != "compare_frozen_forecast_to_frozen_consensus_before_official_outcome":
        raise ValueError("EVALUATION_RULE_NOT_PREREGISTERED")
    if not isinstance(case["event_id"], str) or not case["event_id"].strip():
        raise ValueError("INVALID_EVENT_ID")
    times = {k: parse_utc(case[k]) for k in TIMES if case[k] is not None}
    for key in HASHES:
        v = case[key]
        if v is not None and (not isinstance(v, str) or len(v) != 64 or
                              any(c not in "0123456789abcdef" for c in v)):
            raise ValueError("INVALID_SHA256_" + key)
    for key in ("forecast_method_id", "consensus_provider", "consensus_methodology"):
        v = case[key]
        if v is not None and (not isinstance(v, str) or not v.strip()):
            raise ValueError("INVALID_STRING_" + key)
    for key in ("forecast_value_mbu", "consensus_value_mbu"):
        v = case[key]
        if v is not None and (type(v) not in (int, float) or not 0 <= v <= 100000 or v != v):
            raise ValueError("INVALID_VALUE_" + key)
    if type(case["frozen_before_release"]) is not bool:
        raise ValueError("INVALID_FREEZE_FLAG")
    release = times.get("release_scheduled_utc")
    if release:
        for k in TIMES[1:]:
            if k in times and times[k] >= release:
                raise ValueError("POST_RELEASE_EVIDENCE_" + k)
    if "forecast_created_utc" in times and "forecast_inputs_cutoff_utc" in times:
        if times["forecast_inputs_cutoff_utc"] > times["forecast_created_utc"]:
            raise ValueError("INPUT_AFTER_FORECAST")
    if "forecast_created_utc" in times and "forecast_independent_capture_utc" in times:
        if times["forecast_independent_capture_utc"] < times["forecast_created_utc"]:
            raise ValueError("CAPTURE_BEFORE_FORECAST")
    missing = sorted(k for k in REQUIRED if case[k] is None)
    complete = not missing and case["frozen_before_release"]
    return {
        "schema": "signal-k45-ex-ante-gate-result-v1",
        "event_id": case["event_id"],
        "status": "REVIEW_CANDIDATE_NOT_PIT_CERTIFIED" if complete else "BLOCKED_NO_EX_ANTE_EVIDENCE",
        "missing_fields": missing,
        "registration_complete": complete,
        "forecast_vs_consensus_delta_mbu": (
            case["forecast_value_mbu"] - case["consensus_value_mbu"] if complete else None
        ),
        "independent_pit_certified": False,
        "predictive_edge_verified": False,
        "market_event_study_eligible": False,
        "trade_eligible": False,
        "rule": "Completeness and asserted timestamps are not independent PIT authentication; historical outcomes cannot reconstruct ex-ante forecasts.",
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = assess(json.loads(a.case.read_text(encoding="utf-8")))
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "k45_ex_ante_gate.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "missing": len(result["missing_fields"]), "trade_eligible": False}))

if __name__ == "__main__":
    main()

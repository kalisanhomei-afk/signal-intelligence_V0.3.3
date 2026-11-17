"""K4.5-B USDA corn export inspections: competing signals, not an alpha model.

No network, no paid data, no forecasts produced from uncalibrated features.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

SCHEMA = "signal-k45-export-driver-evidence-v1"
EXPECTED_KEYS = {
    "schema", "event_id", "marketing_year", "target", "release_scheduled_utc",
    "observation_week_end", "source_report_release_utc_claim",
    "inputs_cutoff_utc", "source_dataset", "numerical_source_url",
    "official_report_catalog_url", "official_raw_sha256",
    "independent_pre_release_capture_utc", "source_pit_authenticated",
    "weekly_inspections_mt", "weekly_required_to_hit_usda_mt",
    "cumulative_inspections_mt", "prior_year_cumulative_inspections_mt",
    "usda_percent_completed", "five_year_average_percent_completed",
    "usda_exports_baseline_mbu", "usda_ending_stocks_baseline_mbu",
    "illustrative_export_deltas_mbu", "model_calibration_evidence_sha256",
}
TARGET = "US_CORN_2026_27_ENDING_STOCKS_MBU"
SCHEDULE = "2026-12-10T17:00:00Z"
SOURCE = "USDA_FGIS_WEEKLY_INSPECTIONS_WA_GR101"
NUMERIC_URL = "https://www.cmegroup.com/education/events/econoday/675853"
OFFICIAL_URL = "https://mymarketnews.ams.usda.gov/viewReport/3071"

def utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("INVALID_UTC") from exc

def sha(value):
    if value is not None and (
        not isinstance(value, str) or len(value) != 64 or
        any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("INVALID_SHA256")

def assess(x):
    if not isinstance(x, dict) or set(x) != EXPECTED_KEYS:
        raise ValueError("INVALID_CONTRACT_KEYS")
    if (x["schema"] != SCHEMA or x["event_id"] != "USDA-WASDE-2026-12-10"
        or x["marketing_year"] != "2026/27" or x["target"] != TARGET
        or x["release_scheduled_utc"] != SCHEDULE):
        raise ValueError("EVENT_OR_TARGET_MISMATCH")
    if (x["source_dataset"] != SOURCE or x["numerical_source_url"] != NUMERIC_URL
        or x["official_report_catalog_url"] != OFFICIAL_URL
        or x["observation_week_end"] != "2026-11-12"):
        raise ValueError("SOURCE_IDENTITY_MISMATCH")
    for field in ("official_raw_sha256", "model_calibration_evidence_sha256"):
        sha(x[field])
    if type(x["source_pit_authenticated"]) is not bool:
        raise ValueError("INVALID_AUTHENTICATION_FLAG")
    published = utc(x["source_report_release_utc_claim"])
    cutoff = utc(x["inputs_cutoff_utc"])
    release = utc(x["release_scheduled_utc"])
    if not published <= cutoff < release:
        raise ValueError("LOOKAHEAD_OR_TIME_ORDER")
    capture = x["independent_pre_release_capture_utc"]
    if capture is not None and not published <= utc(capture) <= cutoff:
        raise ValueError("CAPTURE_TIME_ORDER")
    if x["source_pit_authenticated"] and (
        capture is None or x["official_raw_sha256"] is None):
        raise ValueError("UNSUPPORTED_SOURCE_AUTHENTICATION")
    ints = ("weekly_inspections_mt", "weekly_required_to_hit_usda_mt",
            "cumulative_inspections_mt", "prior_year_cumulative_inspections_mt",
            "usda_exports_baseline_mbu", "usda_ending_stocks_baseline_mbu")
    if any(type(x[k]) is not int or x[k] <= 0 for k in ints):
        raise ValueError("BAD_VOLUME_OR_STOCK")
    if x["weekly_inspections_mt"] > x["cumulative_inspections_mt"]:
        raise ValueError("WEEK_EXCEEDS_YEAR")
    if x["usda_exports_baseline_mbu"] != 3275 or x["usda_ending_stocks_baseline_mbu"] != 1758:
        raise ValueError("FROZEN_V0_MISMATCH")
    for k in ("usda_percent_completed", "five_year_average_percent_completed"):
        if type(x[k]) not in (int, float) or not 0 < x[k] < 100:
            raise ValueError("INVALID_PERCENT")
    deltas = x["illustrative_export_deltas_mbu"]
    if deltas != [-50, 0, 50]:
        raise ValueError("SCENARIO_GRID_NOT_PREREGISTERED")
    weekly_ratio = x["weekly_inspections_mt"] / x["weekly_required_to_hit_usda_mt"]
    yoy_pct = 100 * (x["cumulative_inspections_mt"] / x["prior_year_cumulative_inspections_mt"] - 1)
    progress_gap_pp = x["usda_percent_completed"] - x["five_year_average_percent_completed"]
    conflicting = weekly_ratio < 1 and progress_gap_pp > 0
    calibrated = x["model_calibration_evidence_sha256"] is not None
    return {
        "schema": "signal-k45-export-driver-screen-result-v1",
        "event_id": x["event_id"],
        "source_report_release_utc_claim": x["source_report_release_utc_claim"],
        "inputs_cutoff_utc": x["inputs_cutoff_utc"],
        "weekly_vs_required_ratio": round(weekly_ratio, 6),
        "cumulative_yoy_change_percent": round(yoy_pct, 3),
        "progress_vs_five_year_avg_percentage_points": round(progress_gap_pp, 3),
        "competing_signal_directions": {
            "current_week_vs_required": "BELOW_TARGET_PACE" if weekly_ratio < 1 else "AT_OR_ABOVE_TARGET_PACE",
            "cumulative_vs_seasonal_average": "AHEAD" if progress_gap_pp > 0 else "AT_OR_BEHIND",
        },
        "mixed_signals": conflicting,
        "scenario_only_not_probabilistic": [
            {
                "assumed_export_revision_mbu": d,
                "conditional_ending_stocks_mbu": x["usda_ending_stocks_baseline_mbu"] - d
            } for d in deltas
        ],
        "forecast_point_estimate_mbu": None,
        "model_v1_status": "ABSTAIN_UNCALIBRATED_EXPORT_DRIVER",
        "numeric_source_publication_claim_is_not_pit_authentication": True,
        "official_raw_pit_authenticated": False,
        "calibration_evidence_present": calibrated,
        "december_consensus_pit_verified": False,
        "independent_predictive_edge_verified": False,
        "trade_eligible": False,
        "reason": "Weekly pace and seasonal cumulative progress send opposing signals; no historically validated mapping of inspections to December WASDE export revisions. Scenario levels are arbitrary stress inputs, not forecasts."
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = assess(json.loads(a.case.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["model_v1_status"], "mixed": result["mixed_signals"], "trade_eligible": False}))

if __name__ == "__main__":
    main()

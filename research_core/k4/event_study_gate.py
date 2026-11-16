"""K4 conservative event-study readiness inventory. No network, orders, or alpha claims."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

FIELDS = (
    "official_raw_sha256",
    "official_response_finished_utc",
    "official_report_identity",
    "survey_raw_sha256",
    "survey_independent_capture_utc",
    "survey_provider_and_methodology",
    "futures_raw_sha256",
    "futures_vendor_license_reference",
    "futures_instrument_definition",
    "same_contract_pre_release_quote_utc",
    "same_contract_post_observation_quote_utc",
    "bid_ask_and_cost_evidence",
)
EVENT_UTC = "2026-11-10T17:00:00Z"

def _timestamp(s):
    if not isinstance(s, str) or not s.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.utcoffset().total_seconds() != 0:
        raise ValueError("UTC_OFFSET_INVALID")
    return d

def assess(data):
    if data.get("schema") != "signal-k4-event-study-evidence-v1":
        raise ValueError("INVALID_SCHEMA")
    if data.get("hypothesis_id") != "H-CORN-001" or data.get("symbol") != "ZCZ6":
        raise ValueError("HYPOTHESIS_OR_CONTRACT_MISMATCH")
    evidence = data.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(FIELDS):
        raise ValueError("EVIDENCE_CONTRACT_MISMATCH")
    blockers = [name for name in FIELDS if evidence[name] is None]
    # Reject placeholders and never silently promote an asserted vendor value to authenticated truth.
    for name in FIELDS:
        v = evidence[name]
        if v is not None and (not isinstance(v, str) or not v.strip()):
            raise ValueError("INVALID_EVIDENCE_VALUE_" + name)
    for key in ("official_raw_sha256", "survey_raw_sha256", "futures_raw_sha256"):
        v = evidence[key]
        if v is not None and (len(v) != 64 or any(c not in "0123456789abcdef" for c in v)):
            raise ValueError("INVALID_RAW_SHA256_" + key)
    t = {key: _timestamp(evidence[key]) for key in (
        "official_response_finished_utc", "survey_independent_capture_utc",
        "same_contract_pre_release_quote_utc", "same_contract_post_observation_quote_utc"
    ) if evidence[key] is not None}
    event = _timestamp(EVENT_UTC)
    if "survey_independent_capture_utc" in t and t["survey_independent_capture_utc"] >= event:
        raise ValueError("SURVEY_CAPTURE_NOT_PRE_RELEASE")
    if "official_response_finished_utc" in t and t["official_response_finished_utc"] < event:
        raise ValueError("OFFICIAL_CAPTURE_BEFORE_RELEASE")
    if "same_contract_pre_release_quote_utc" in t and t["same_contract_pre_release_quote_utc"] >= event:
        raise ValueError("PRE_RELEASE_QUOTE_NOT_PRE_RELEASE")
    if ("same_contract_post_observation_quote_utc" in t and
        "official_response_finished_utc" in t and
        t["same_contract_post_observation_quote_utc"] <= t["official_response_finished_utc"]):
        raise ValueError("POST_PRICE_PRECEDES_SYSTEM_OBSERVATION")
    # Data presence and valid ordering only nominate independent review.
    # File hashes, license, survey identity and executable bid/ask MUST be independently audited.
    candidate = not blockers
    return {
        "schema": "signal-k4-event-study-gate-result-v1",
        "hypothesis_id": "H-CORN-001", "symbol": "ZCZ6",
        "missing_evidence": blockers,
        "evidence_fields_complete": candidate,
        "status": "CANDIDATE_REQUIRES_INDEPENDENT_REVIEW" if candidate else "BLOCKED_MISSING_EVIDENCE",
        "independently_authenticated": False,
        "formal_event_study_eligible": False,
        "cost_adjusted_edge_verified": False,
        "trade_eligible": False,
        "strategy_return": None,
        "rule": "Evidence field presence is not independent authentication or tradability.",
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = assess(json.loads(args.case.read_text(encoding="utf-8")))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "event_study_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "missing_count": len(report["missing_evidence"]), "trade_eligible": False}))

if __name__ == "__main__":
    main()

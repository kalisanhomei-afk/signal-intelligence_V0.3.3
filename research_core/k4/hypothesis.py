"""SIGNAL K4: falsifiable corn inventory-surprise mechanism pilot.

Pure standard-library accounting + provenance readiness, NOT a predictive
model, live signal, certified point-in-time backtest, or trading engine.
This code makes no external requests. Numerical values come from the
supplied case; never synthesize missing observations.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import re

HYPOTHESIS_ID = "H-CORN-001"
UNIT = "million_bushels"
REQUIRED_BALANCE = (
    "beginning_stocks", "production", "imports",
    "domestic_use", "exports", "ending_stocks", "total_use",
)


class ResearchGateError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise ResearchGateError(code)


def dec(value, field, *, strictly_positive=False):
    require(isinstance(value, str), f"DECIMAL_STRING_REQUIRED_{field}")
    try:
        num = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ResearchGateError(f"INVALID_DECIMAL_{field}") from exc
    require(num.is_finite(), f"NONFINITE_{field}")
    require(num > 0 if strictly_positive else num >= 0, f"INVALID_NONNEGATIVE_{field}")
    return num


def iso_utc(value: str, field: str):
    require(isinstance(value, str) and bool(value), f"INVALID_TIME_{field}")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResearchGateError(f"INVALID_TIME_{field}") from exc
    require(dt.tzinfo is not None and dt.utcoffset() is not None, f"TIMEZONE_REQUIRED_{field}")
    return dt


def marketing_year(value):
    require(isinstance(value, str) and re.fullmatch(r"20\d{2}/\d{2}", value) is not None,
            "MARKETING_YEAR_INVALID")
    start = int(value[:4])
    require((start + 1) % 100 == int(value[-2:]), "MARKETING_YEAR_NOT_CONSECUTIVE")
    return value


def moneyless_summary(v: Decimal) -> str:
    return format(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def evaluate_case(case: dict) -> dict:
    """Check accounting, compare survey vs previous month, and FAIL CLOSED on PIT."""
    require(isinstance(case, dict), "CASE_MUST_BE_OBJECT")
    require(case.get("hypothesis_id") == HYPOTHESIS_ID, "WRONG_HYPOTHESIS")
    require(case.get("research_case_id") and isinstance(case["research_case_id"], str),
            "MISSING_CASE_ID")
    require(case.get("evidence_type") in ("RETROSPECTIVE_REFERENCE", "SYNTHETIC_FIXTURE"),
            "EVIDENCE_TYPE_NOT_APPROVED")
    require(case.get("commodity") == "Corn" and case.get("region") == "United States",
            "WRONG_COMMODITY_OR_REGION")
    require(case.get("unit") == UNIT, "UNITS_MUST_BE_MILLION_BUSHELS")
    my = marketing_year(case.get("marketing_year"))
    require(case.get("prior_report_marketing_year") == my, "PRIOR_REPORT_DIFFERENT_MARKETING_YEAR")
    try:
        datetime.strptime(case["release_date"], "%Y-%m-%d")
    except (KeyError, ValueError, TypeError) as exc:
        raise ResearchGateError("INVALID_RELEASE_DATE") from exc

    reported = case.get("reported")
    require(isinstance(reported, dict), "MISSING_REPORTED_BALANCE")
    numbers = {name: dec(reported.get(name), name,
                         strictly_positive=name == "total_use") for name in REQUIRED_BALANCE}
    supply = numbers["beginning_stocks"] + numbers["production"] + numbers["imports"]
    utilization = numbers["domestic_use"] + numbers["exports"]
    require(utilization == numbers["total_use"], "TOTAL_USE_COMPONENTS_DONT_RECONCILE")
    require(supply - numbers["total_use"] == numbers["ending_stocks"],
            "STOCK_FLOW_BALANCE_DOES_NOT_RECONCILE")

    reference = case.get("reference")
    require(isinstance(reference, dict), "MISSING_EXPECTATION_REFERENCE")
    prior = dec(reference.get("prior_month_ending_stocks"), "prior_month_ending_stocks")
    consensus_raw = reference.get("pre_report_consensus_ending_stocks")
    # Without a market survey, month-to-month USDA revisions are NOT market surprises.
    consensus = (dec(consensus_raw, "pre_report_consensus_ending_stocks",
                     strictly_positive=True) if consensus_raw is not None else None)
    provenance = case.get("provenance")
    require(isinstance(provenance, dict), "MISSING_PROVENANCE")
    require(provenance.get("pit_certified") is not True, "UNREVIEWED_PIT_CERTIFICATION_CLAIM")
    require(provenance.get("report_source_url", "").startswith("https://"),
            "OFFICIAL_REPORT_URL_REQUIRED")
    if reference.get("survey_captured_at_utc") is not None:
        survey_time = iso_utc(reference["survey_captured_at_utc"], "survey_captured_at_utc")
        schedule = provenance.get("scheduled_release_at_utc")
        require(schedule is not None and survey_time < iso_utc(schedule, "scheduled_release_at_utc"),
                "CONSENSUS_NOT_PROVEN_PRE_SCHEDULE")
    if provenance.get("report_observed_at_utc") is not None:
        observed = iso_utc(provenance["report_observed_at_utc"], "report_observed_at_utc")
        if provenance.get("scheduled_release_at_utc") is not None:
            require(observed >= iso_utc(provenance["scheduled_release_at_utc"], "scheduled_release_at_utc"),
                    "REPORT_OBSERVATION_BEFORE_SCHEDULE")

    # This preview is an accounting/hypothesis mechanism ONLY. It is never a
    # forecast, a profitable signal, an event-study result, or a trade instruction.
    surprise = numbers["ending_stocks"] - consensus if consensus is not None else None
    if surprise is None:
        direction = "NOT_CALCULABLE_NO_CONSENSUS"
    elif surprise < 0:
        direction = "UPWARD_PRICE_PRESSURE_RESEARCH_BASELINE_ONLY"
    elif surprise > 0:
        direction = "DOWNWARD_PRICE_PRESSURE_RESEARCH_BASELINE_ONLY"
    else:
        direction = "NEUTRAL_SURPRISE_RESEARCH_BASELINE_ONLY"

    blockers = [
        "HISTORICAL_REPORT_BYTE_LEVEL_PIT_NOT_CERTIFIED",
        "OUT_OF_SAMPLE_PRICE_RESPONSE_AND_EXECUTION_NOT_VALIDATED",
        "NO_COSTS_SLIPPAGE_OR_EX_POST_RISK_ANALYSIS",
        "PREDICTIVE_INCREMENT_OVER_PUBLIC_BENCHMARK_NOT_TESTED",
    ]
    if provenance.get("official_source_sha256") is None:
        blockers.append("OFFICIAL_RAW_SOURCE_DIGEST_NOT_BOUND_IN_THIS_CASE")
    if reference.get("survey_captured_at_utc") is None:
        blockers.append("CONSENSUS_PRE_RELEASE_TIMESTAMP_NOT_INDEPENDENTLY_PROVEN")
    if consensus is None:
        blockers.append("PRE_RELEASE_MARKET_CONSENSUS_UNAVAILABLE")
    if case["evidence_type"] == "RETROSPECTIVE_REFERENCE":
        blockers.append("RETROSPECTIVE_REFERENCE_CANNOT_CERTIFY_HISTORICAL_AVAILABILITY")

    return {
        "schema": "signal-k4-hypothesis-mechanism-review-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "research_case_id": case["research_case_id"],
        "input_evidence_type": case["evidence_type"],
        "commodity": "Corn", "region": "United States",
        "marketing_year": my, "unit": UNIT,
        "reported_ending_stocks": str(numbers["ending_stocks"]),
        "prior_month_ending_stocks": str(prior),
        "consensus_ending_stocks": str(consensus) if consensus is not None else None,
        "prior_month_change_million_bushels": str(numbers["ending_stocks"] - prior),
        "market_consensus_surprise_million_bushels": str(surprise) if surprise is not None else None,
        "stocks_to_use_percent": moneyless_summary(
            Decimal("100") * numbers["ending_stocks"] / numbers["total_use"]),
        "stock_flow_identity_reconciled": True,
        "mechanism_direction_benchmark_only": direction,
        "status": "ACCOUNTING_PASS_MECHANISM_ONLY_PIT_UNVERIFIED",
        "historical_original_source_pit_certified": False,
        "event_study_eligible": False,
        "investment_edge_verified": False,
        "trade_eligible": False,
        "price_effect_estimate": None,
        "strategy_return": None,
        "missing_gates": sorted(set(blockers)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    case = json.loads(args.case.read_text(encoding="utf-8"))
    result = evaluate_case(case)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "hypothesis_review.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# SIGNAL K4 — H-CORN-001 accounting and research hypothesis",
        "",
        f"Case: {result['research_case_id']} ({result['marketing_year']}).",
        "",
        f"Reported ending stocks: {result['reported_ending_stocks']} million bushels.",
        f"Market survey expectation: {result['consensus_ending_stocks']} million bushels.",
        f"Stock surprise vs pre-report survey: {result['market_consensus_surprise_million_bushels']} million bushels.",
        f"USDA month-to-month change: {result['prior_month_change_million_bushels']} million bushels (NOT equivalent to market surprise).",
        f"Stock/use ratio: {result['stocks_to_use_percent']}%.",
        "",
        "**RESEARCH ONLY. No PIT-certified source history, no price response backtest, no alpha, no executable trade.**",
        "",
        "## Missing gates",
        *[f"- {x}" for x in result["missing_gates"]],
        "",
    ]
    (args.output / "hypothesis_review.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "case": result["research_case_id"],
        "stock_flow_identity_reconciled": result["stock_flow_identity_reconciled"],
        "market_consensus_surprise_million_bushels": result["market_consensus_surprise_million_bushels"],
        "trade_eligible": False, "historical_original_source_pit_certified": False,
        "status": result["status"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

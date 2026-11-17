"""K4 pre-release poll-vintage sensitivity: one report, several UNVERIFIED surveys.

Independent publishers need not measure the same analyst group/time. Results
are descriptive and DO NOT certify the analyst estimates actually existed at
the indicated historical decision instant. No market prices are fetched.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

from research_core.k4.hypothesis import HYPOTHESIS_ID, ResearchGateError, dec, iso_utc, marketing_year, require


def score_variants(case: dict) -> dict:
    require(isinstance(case, dict), "CASE_MUST_BE_OBJECT")
    require(case.get("schema") == "signal-k4-consensus-sensitivity-catalog-v1", "INVALID_CATALOG_SCHEMA")
    require(case.get("hypothesis_id") == HYPOTHESIS_ID, "WRONG_HYPOTHESIS_ID")
    require(case.get("source_report") == "WASDE-677", "UNSUPPORTED_REFERENCE_RELEASE")
    require(case.get("source_report_release_date") == "2026-11-10", "RELEASE_DATE_MISMATCH")
    release_time = iso_utc(case.get("release_schedule_utc"), "release_schedule_utc")
    require(release_time.isoformat() == "2026-11-10T17:00:00+00:00",
            "INCORRECT_OFFICIAL_RELEASE_SCHEDULE_TIME")
    require(case.get("commodity") == "Corn" and case.get("region") == "United States",
            "WRONG_COMMODITY_OR_GEOGRAPHY")
    marketing_year(case.get("marketing_year"))
    require(case["marketing_year"] == "2026/27", "WRONG_MARKETING_YEAR")
    require(case.get("unit") == "million_bushels", "UNIT_MISMATCH")
    require(case.get("survey_selection_policy") ==
            "DISPLAY_EACH_SOURCE_SEPARATELY_NEVER_AVERAGE_NOR_SELECT_BEST_LOOKING_RESULT",
            "SURVEY_CHERRY_PICK_OR_UNDISCLOSED_BLEND_FORBIDDEN")
    actual = dec(case.get("actual_ending_stocks"), "actual_ending_stocks", strictly_positive=True)
    old = dec(case.get("usda_prior_month_ending_stocks"), "usda_prior_month_ending_stocks", strictly_positive=True)

    surveys = case.get("survey_observation_vintages")
    require(isinstance(surveys, list) and len(surveys) == 3, "REQUIRES_THREE_IDENTIFIED_PUBLISHER_VINTAGES")
    ids = set()
    rows = []
    for survey in surveys:
        require(isinstance(survey, dict), "INVALID_SURVEY_OBJECT")
        ident = survey.get("survey_id")
        require(isinstance(ident, str) and bool(ident) and ident not in ids,
                "DUPLICATE_OR_EMPTY_SURVEY_ID")
        ids.add(ident)
        require(survey.get("publisher") and survey.get("survey_family") and survey.get("survey_underlying_vendor_identity"),
                "MISSING_SOURCE_SURVEY_IDENTITY")
        url = survey.get("source_url")
        require(isinstance(url, str) and url.startswith("https://") and "@" not in url, "INVALID_SURVEY_URL")
        try:
            claimed = date.fromisoformat(survey["publisher_article_date_claim"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ResearchGateError("INVALID_PUBLISHER_DATELINE") from exc
        require(claimed <= release_time.date(), "PUBLISHER_DATELINE_AFTER_RELEASE")
        require(survey.get("time_evidence_quality") == "PUBLISHER_DATE_ONLY_PRE_RELEASE_UNVERIFIED",
                "UNSUPPORTED_PROVENANCE_PROMOTION")
        require(survey.get("independent_pre_release_capture_body_sha256") is None
                and survey.get("independent_pre_release_capture_at_utc") is None,
                "CLAIMED_INDEPENDENT_CAPTURE_REQUIRES_EXTERNAL_ADJUDICATION")
        require(survey.get("source_acquisition_status")
                in {"CURRENT_PUBLIC_PAGE_REVIEWED_NOT_INDEPENDENT_PRE_RELEASE_CAPTURED",
                    "ARTICLE_PUBLISHED_DATE_CLAIM_NOT_CRYPTOPROVEN"},
                "INVALID_SURVEY_ACQUISITION_STATUS")
        estimate = dec(survey.get("reported_ending_stocks"), "reported_ending_stocks", strictly_positive=True)
        surprise = actual - estimate
        rows.append({
            "survey_id": ident,
            "publisher": survey["publisher"],
            "survey_family": survey["survey_family"],
            "survey_underlying_vendor_identity": survey["survey_underlying_vendor_identity"],
            "publisher_article_date_claim": claimed.isoformat(),
            "publisher_article_precedes_release_date": claimed < release_time.date(),
            "source_url": url,
            "reported_ending_stocks_million_bushels": str(estimate),
            "surprise_vs_survey_million_bushels": str(surprise),
            "direction": "NEGATIVE_STOCKS_SURPRISE" if surprise < 0
                         else "POSITIVE_STOCKS_SURPRISE" if surprise > 0 else "ZERO_SURPRISE",
            "independently_authenticated_pre_release_vintage": False,
            "event_study_eligible": False,
        })
    require(ids == {"CME_EVENT_CALENDAR_ESTIMATES", "STONEX_NOV_05_AVERAGE",
                    "DTN_DOW_JONES_NOV_06"}, "SURVEY_ID_SET_HAS_CHANGED")
    values = [Decimal(x["surprise_vs_survey_million_bushels"]) for x in rows]
    price = case.get("price_data_feasibility")
    require(isinstance(price, dict), "MISSING_EXCHANGE_PRICE_DATA_CONTRACT")
    require(price.get("candidate_exchange") == "CBOT (CME Group)" and
            price.get("potential_contract_symbol") == "ZCZ6", "EXACT_CB0T_CONTRACT_NOT_FIXED")
    require(price.get("actual_intraday_records_acquired") == 0, "PRICE_HISTORY_NOT_YET_AUDITED")
    require(price.get("event_contract_evidence_sha256") is None and
            price.get("orderbook_bid_ask_executability_proven") is False, "UNVERIFIED_PRICE_OR_EXECUTABILITY")
    require(price.get("contract_unit_bushels") == "5000" and
            price.get("minimum_tick_cents_per_bushel") == "0.25" and
            price.get("minimum_tick_usd_per_contract") == "12.50",
            "CME_CONTRACT_SPECIFICATION_CHANGED_WITHOUT_REVIEW")

    return {
        "schema": "signal-k4-consensus-vintage-review-v1",
        "research_hypothesis_id": HYPOTHESIS_ID,
        "source_report": case["source_report"],
        "marketing_year": case["marketing_year"],
        "unit": case["unit"],
        "reported_ending_stocks": str(actual),
        "USDA_previous_month_ending_stocks": str(old),
        "USDA_month_on_month_change_million_bushels": str(actual - old),
        "survey_count": len(rows),
        "survey_results": rows,
        "surprise_min_million_bushels": str(min(values)),
        "surprise_max_million_bushels": str(max(values)),
        "surprise_span_million_bushels": str(max(values) - min(values)),
        "direction_consistent_among_reviewed_surveys": len(set(
            x["direction"] for x in rows)) == 1,
        "survey_values_blended": False,
        "price_symbol_held_for_future_study_only": price["potential_contract_symbol"],
        "independently_authenticated_pre_release_survey_count": 0,
        "historical_intraday_price_rows_acquired": 0,
        "historical_PIT_certified": False,
        "price_response_estimated": False,
        "predictive_incremental_edge_validated": False,
        "transaction_cost_adjusted_tradable": False,
        "status": "SURVEY_SENSITIVITY_NUMERICALLY_CHECKED_ASOF_UNVERIFIED_NO_PRICE_DATA",
        "next_critical_gates": [
            "INDEPENDENTLY_TIMESTAMP_SURVEYS_BEFORE_2026_11_10_17_UTC",
            "ACQUIRE_EXACT_ZCZ6_INTRADAY_BARS_AND_LICENSE_TERMS",
            "VALIDATE_SYNCHRONIZED_QUOTES_AFTER_SYSTEM_DATA_ARRIVAL",
            "PRE_REGISTER_OUT_OF_SAMPLE_INCREMENTAL_MODEL_AND_COSTS",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score_variants(json.loads(args.catalog.read_text(encoding="utf-8")))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "survey_vintage_sensitivity.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    rows = [
        "# SIGNAL K4 — 2026-11 WASDE corn: *survey-version sensitivity* (NOT as-of certified)",
        "",
        "| Survey | Estimated stocks (mil bu) | Surprise vs USDA | Publisher dateline |",
        "| --- | ---: | ---: | --- |",
    ]
    for r in result["survey_results"]:
        rows.append("| {survey_id} | {reported_ending_stocks_million_bushels} | "
                    "{surprise_vs_survey_million_bushels} | {publisher_article_date_claim} |".format(**r))
    rows.extend([
        "",
        f"Across the three **distinct sources**, surprise range: {result['surprise_min_million_bushels']}"
        f" to {result['surprise_max_million_bushels']} million bushels"
        f" (spread {result['surprise_span_million_bushels']}).",
        "Not a confidence interval or sample of identical survey instruments.",
        "",
        "**NO pre-release immutable snapshot proven; NO trading price data acquired; NO alpha / PIT certification.**",
        "",
    ])
    (args.output / "survey_vintage_sensitivity.md").write_text("\n".join(rows), encoding="utf-8")
    print(json.dumps({
        "surveys": result["survey_count"], "minimum_surprise": result["surprise_min_million_bushels"],
        "maximum_surprise": result["surprise_max_million_bushels"],
        "intraday_bars": 0, "PIT_CERTIFIED": False, "TRADE_ELIGIBLE": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

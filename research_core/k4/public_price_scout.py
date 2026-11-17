"""K4 publicly reported quote scout — not an intraday market data backtest.

The two market reporters have no authenticated as-of snapshots here.
All comparisons are descriptive. Never claim execution, market impact,
profitable alpha, or a causal reaction attributable to WASDE alone.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import json
from pathlib import Path
from urllib.parse import urlsplit

from research_core.k4.hypothesis import ResearchGateError, require, dec, iso_utc, HYPOTHESIS_ID


def _cents(value, name, tick):
    p = dec(value, name, strictly_positive=True)
    require(p / tick == (p / tick).to_integral_value(), "PRICE_NOT_ON_CONTRACT_TICK_GRID")
    return p


def scout_prices(case: dict) -> dict:
    require(isinstance(case, dict), "SCOUT_CASE_NOT_OBJECT")
    require(case.get("schema") == "signal-k4-public-price-scout-v1", "WRONG_PRICE_SCOUT_SCHEMA")
    require(case.get("hypothesis_id") == HYPOTHESIS_ID, "WRONG_HYPOTHESIS")
    require(case.get("report_date") == "2026-11-10", "WRONG_EVENT_DATE")
    release = iso_utc(case.get("report_release_scheduled_utc"), "report_release_scheduled_utc")
    require(release == datetime(2026, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
            "WRONG_EVENT_TIME_UTC")
    require(case.get("commodity") == "Corn" and case.get("market") == "CBOT", "WRONG_CROP_OR_MARKET")
    require(case.get("instrument_id_for_research_only") == "ZCZ6" and
            case.get("barchart_symbol_alias") == "ZCZ26", "MIXED_OR_UNSUPPORTED_CONTRACT")
    require(case.get("symbol_cross_vendor_mapping_authenticated") is False,
            "UNREVIEWED_CROSS_VENDOR_CONTRACT_AUTHENTICATION")
    require(case.get("unit") == "US_cents_per_bushel", "PRICE_UNIT_MISMATCH")
    tick = dec(case.get("tick_size_cents"), "tick_size_cents", strictly_positive=True)
    require(tick == Decimal("0.25") and case.get("contract_bushels") == "5000",
            "CBOT_CORN_SPEC_UNREVIEWED_CHANGE")

    groups = case.get("reporting_sources")
    require(isinstance(groups, list) and len(groups) == 2, "EXACT_TWO_DISTINCT_PRICE_PUBLISHERS_REQUIRED")
    sources = {}
    for group in groups:
        name = group.get("publisher")
        require(name and name not in sources, "DUPLICATE_PRICE_PUBLISHER")
        url = group.get("source_url")
        host = urlsplit(url).hostname if isinstance(url, str) else None
        require(urlsplit(url).scheme == "https" and host in {"tools.gotredas.com", "mnbl.websol.barchart.com"},
                "PRICE_PUBLISHER_URL_NOT_APPROVED")
        require(group.get("raw_archived_source_sha256") is None and
                group.get("publisher_quote_captured_independently_at_utc") is None,
                "FALSE_INDEPENDENT_HISTORICAL_QUOTE_CERTIFICATION")
        if name == "Tredas":
            require(group.get("evidence_class") == "RETROSPECTIVE_POST_EVENT_WEB_ARTICLE_QUOTE",
                    "PRICE_TYPE_CANNOT_BE_PROMOTED")
            require(group.get("bid_ask_or_trade_executability_proven") is False,
                    "EXECUTION_PRICE_NOT_PROVEN")
        else:
            require(group.get("evidence_class") == "RETROSPECTIVE_DAILY_WEB_HISTORY_NOT_MINUTE_BARS",
                    "DAILY_HISTORY_NOT_INTRADAY_TRADE_DATA")
        sources[name] = group

    require(set(sources) == {"Tredas", "Barchart embedded third-party futures detail"},
            "UNEXPECTED_PRICE_SOURCES")
    article = sources["Tredas"]
    quotes = article.get("intraday_claimed_quotes")
    require(isinstance(quotes, list) and len(quotes) == 2, "NEED_TWO_FIXED_PUBLISHER_QUOTE_REFERENCES")
    observed = []
    for r in quotes:
        stamp = iso_utc(r.get("timestamp_utc"), "publisher_claimed_utc")
        # The publisher's CT time is a claim from a retrospective article. Do
        # not assume it is cryptographically witnessed by an independent party.
        claimed = r.get("publisher_claimed_time_ct")
        require(isinstance(claimed, str) and claimed.endswith(" CST"), "PUBLISHER_CT_LABEL_MISSING")
        local = datetime.strptime(claimed, "%Y-%m-%d %H:%M:%S CST").replace(tzinfo=timezone(timedelta(hours=-6)))
        require(local.astimezone(timezone.utc) == stamp, "CT_AND_UTC_REPORT_CLOCK_CONFLICT")
        require(release < stamp <= release + timedelta(minutes=10), "QUOTE_NOT_WITHIN_EVENT_TEN_MINUTES")
        p = _cents(r.get("quote_cents_per_bushel"), "publisher_quote", tick)
        observed.append((stamp, p))
    require(observed[0][0] < observed[1][0], "NON_INCREASING_PUBLISHER_QUOTE_TIMES")

    daily = sources["Barchart embedded third-party futures detail"].get("daily_reference")
    require(isinstance(daily, list) and len(daily) == 2, "DAILY_REFERENCE_REQUIRES_TWO_DATES")
    daily_by_date = {}
    for row in daily:
        day = row.get("trade_date")
        require(day in {"2026-11-09", "2026-11-10"} and day not in daily_by_date,
                "DAILY_REFERENCE_BAD_DATE_OR_DUPLICATE")
        require(row.get("price_type") == "PUBLISHER_DAILY_LAST_MAY_NOT_EQUAL_OFFICIAL_CME_SETTLEMENT",
                "UNVERIFIED_OFFICIAL_SETTLEMENT_PROMOTION")
        daily_by_date[day] = _cents(row.get("settlement_or_last_cents_per_bushel"),
                                    "daily_reference", tick)
    require(set(daily_by_date) == {"2026-11-09", "2026-11-10"}, "DAILY_REFERENCE_BOTH_DATES_REQUIRED")

    prior = daily_by_date["2026-11-09"]
    latest = daily_by_date["2026-11-10"]
    p1 = observed[0][1]
    p2 = observed[1][1]

    return {
        "schema": "signal-k4-public-price-scout-review-v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "contract_research_symbol": "ZCZ6",
        "publisher_alias_without_metadata_authentication": "ZCZ26",
        "report_scheduled_release_utc": "2026-11-10T17:00:00Z",
        "quote_observations_type": "THIRD_PARTY_RETROSPECTIVE_NARRATIVE_ONLY",
        "prior_day_publisher_last_cents": str(prior),
        "event_day_publisher_last_cents": str(latest),
        "first_claimed_quote_utc": observed[0][0].isoformat().replace("+00:00", "Z"),
        "first_claimed_quote_cents": str(p1),
        "second_claimed_quote_utc": observed[1][0].isoformat().replace("+00:00", "Z"),
        "second_claimed_quote_cents": str(p2),
        "prior_day_to_first_claimed_quote_cents": str(p1-prior),
        "prior_day_to_second_claimed_quote_cents": str(p2-prior),
        "first_to_second_claimed_quote_cents": str(p2-p1),
        "prior_day_to_event_day_publisher_last_cents": str(latest-prior),
        "previous_day_to_event_quote_attribution_to_WASDE_permitted": False,
        "live_or_independently_attested_quote_rows_acquired": 0,
        "actual_trade_bid_ask_rows_acquired": 0,
        "contemporaneous_pre_event_price_available": False,
        "source_quotes_historically_time_authenticated": False,
        "causal_effect_estimated": False,
        "incremental_alpha_verified": False,
        "trade_eligible": False,
        "formal_intraday_event_study_eligible": False,
        "status": "SCOUT_PUBLISHER_CLAIMS_ONLY_ACQUIRE_AUTHENTICATED_EVENT_TAPE_BEFORE_BACKTEST",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    score = scout_prices(json.loads(args.case.read_text(encoding="utf-8")))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "price_scout_research_only.json").write_text(
        json.dumps(score, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# SIGNAL K4 — public ZCZ6 prices, retrospective scout only",
        "",
        "| Comparison | Difference, US cents/bushel |",
        "|---|---:|",
        f"| 11:01 CT vs Nov 9 publisher daily last | {score['prior_day_to_first_claimed_quote_cents']} |",
        f"| 11:06 CT vs Nov 9 publisher daily last | {score['prior_day_to_second_claimed_quote_cents']} |",
        f"| 11:06 CT vs 11:01 CT (same Tredas report) | {score['first_to_second_claimed_quote_cents']} |",
        f"| Nov 10 vs Nov 9 Barchart publisher daily last | {score['prior_day_to_event_day_publisher_last_cents']} |",
        "",
        "**Crucial:** prior-day-to-post-release price difference includes overnight market change;",
        "it is NOT the event response or an opportunity an observer can trade.",
        "These are third-party article/report claims, not acquired CME/CBOT prints, OHLCV,",
        "bid/ask or independently time-certified archive. No causal effect/alpha/trading claim.",
    ]
    (args.output / "price_scout_research_only.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    print(json.dumps({"quoted_prices": 2, "real_intraday_bars": 0,
                      "first_to_second_claimed_quote_cents": score["first_to_second_claimed_quote_cents"],
                      "trade_eligible": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

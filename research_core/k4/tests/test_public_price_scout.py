"""K4 public quote claims must not become proof of market execution."""
import json
from pathlib import Path
import unittest

from research_core.k4.public_price_scout import scout_prices
from research_core.k4.hypothesis import ResearchGateError

CASE = Path(__file__).resolve().parents[1] / "cases" / "2026-11-10-zcz6-public-price-scout.json"


def example():
    return json.loads(CASE.read_text(encoding="utf-8"))


class PublicPriceScoutGuards(unittest.TestCase):
    def test_reporter_values_and_cents_not_dollars(self):
        r = scout_prices(example())
        self.assertEqual(r["first_claimed_quote_cents"], "450.75")
        self.assertEqual(r["second_claimed_quote_cents"], "452.50")
        self.assertEqual(r["prior_day_to_first_claimed_quote_cents"], "11.50")
        self.assertEqual(r["prior_day_to_second_claimed_quote_cents"], "13.25")
        self.assertEqual(r["first_to_second_claimed_quote_cents"], "1.75")
        self.assertEqual(r["prior_day_to_event_day_publisher_last_cents"], "9.75")

    def test_not_a_minute_bar_or_executable_trade_claim(self):
        r = scout_prices(example())
        self.assertFalse(r["previous_day_to_event_quote_attribution_to_WASDE_permitted"])
        self.assertEqual(r["actual_trade_bid_ask_rows_acquired"], 0)
        self.assertEqual(r["live_or_independently_attested_quote_rows_acquired"], 0)
        self.assertFalse(r["source_quotes_historically_time_authenticated"])
        self.assertFalse(r["contemporaneous_pre_event_price_available"])
        self.assertFalse(r["trade_eligible"])
        self.assertFalse(r["formal_intraday_event_study_eligible"])
        self.assertFalse(r["incremental_alpha_verified"])

    def test_do_not_confuse_100x_price_unit(self):
        case=example()
        case["unit"]="USD_per_bushel"
        with self.assertRaisesRegex(ResearchGateError,"PRICE_UNIT_MISMATCH"):
            scout_prices(case)

    def test_futures_contract_cannot_be_replaced_by_cfd(self):
        case=example()
        case["instrument_id_for_research_only"]="CORN_USD"
        with self.assertRaisesRegex(ResearchGateError,"MIXED_OR_UNSUPPORTED_CONTRACT"):
            scout_prices(case)

    def test_cross_vendor_alias_is_not_authenticated_without_metadata(self):
        case=example()
        case["symbol_cross_vendor_mapping_authenticated"]=True
        with self.assertRaisesRegex(ResearchGateError,"UNREVIEWED_CROSS_VENDOR"):
            scout_prices(case)

    def test_one_quote_wrong_price_tick_rejected(self):
        case=example()
        case["reporting_sources"][0]["intraday_claimed_quotes"][0]["quote_cents_per_bushel"]="450.73"
        with self.assertRaisesRegex(ResearchGateError,"PRICE_NOT_ON_CONTRACT_TICK_GRID"):
            scout_prices(case)

    def test_publisher_time_and_utc_must_agree(self):
        case=example()
        case["reporting_sources"][0]["intraday_claimed_quotes"][0]["timestamp_utc"]="2026-11-10T16:01:05Z"
        with self.assertRaisesRegex(ResearchGateError,"CT_AND_UTC_REPORT_CLOCK_CONFLICT"):
            scout_prices(case)

    def test_pre_event_quote_not_counted_as_post_event(self):
        case=example()
        case["reporting_sources"][0]["intraday_claimed_quotes"][0].update({
            "timestamp_utc":"2026-11-10T16:59:00Z",
            "publisher_claimed_time_ct":"2026-11-10 10:59:00 CST"})
        with self.assertRaisesRegex(ResearchGateError,"QUOTE_NOT_WITHIN_EVENT_TEN_MINUTES"):
            scout_prices(case)

    def test_reverse_quote_order_fails(self):
        case=example()
        q=case["reporting_sources"][0]["intraday_claimed_quotes"]
        q.reverse()
        with self.assertRaisesRegex(ResearchGateError,"NON_INCREASING"):
            scout_prices(case)

    def test_publisher_cannot_declare_independent_historical_capture(self):
        for key,val in (("raw_archived_source_sha256","c"*64),
                        ("publisher_quote_captured_independently_at_utc","2026-11-10T17:01:05Z")):
            case=example()
            case["reporting_sources"][0][key]=val
            with self.subTest(key=key),self.assertRaisesRegex(
                    ResearchGateError,"FALSE_INDEPENDENT_HISTORICAL_QUOTE_CERTIFICATION"):
                scout_prices(case)

    def test_barchart_not_called_exchange_settlement_without_review(self):
        case=example()
        case["reporting_sources"][1]["daily_reference"][1]["price_type"]="OFFICIAL_CME_SETTLEMENT"
        with self.assertRaisesRegex(ResearchGateError,"UNVERIFIED_OFFICIAL_SETTLEMENT_PROMOTION"):
            scout_prices(case)

    def test_bad_daily_quotation_day_rejected(self):
        case=example()
        case["reporting_sources"][1]["daily_reference"][1]["trade_date"]="2026-11-11"
        with self.assertRaisesRegex(ResearchGateError,"DAILY_REFERENCE_BAD_DATE_OR_DUPLICATE"):
            scout_prices(case)

    def test_no_publisher_price_can_be_promoted_to_real_bid_ask(self):
        case=example()
        case["reporting_sources"][0]["bid_ask_or_trade_executability_proven"]=True
        with self.assertRaisesRegex(ResearchGateError,"EXECUTION_PRICE_NOT_PROVEN"):
            scout_prices(case)

    def test_same_real_reference_data_is_deterministic(self):
        self.assertEqual(scout_prices(example()),scout_prices(example()))


if __name__ == "__main__":
    unittest.main()

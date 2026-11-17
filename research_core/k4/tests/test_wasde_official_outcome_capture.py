"""K4.11 November official-table layout dry run, December synthetic data tests.

No December 2026 USDA result exists in these test fixtures. These do NOT certify
a first-publication time or future official December number.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research_core.k4.wasde_official_outcome_capture import (
    parse_wasde_corn, capture, assess, validate_locked, source_allowed
)

def make_source(month="December", previous="Nov", current="Dec",
                earlier=1758, outcome=1700, unit="Million Bushels", year="2026/27"):
    # Format matches the USDA November table layout, but ALL values in this
    # short future-dated fixture are synthetic and have NO official provenance.
    return (f"WASDE - 678 - 12                    {month} 2026\n\n"
            "                  U.S. Feed Grain and Corn Supply and Use  1/\n"
            "================================================================================\n"
            f"                               2024/25  2025/26 Est. {year} Proj. {year} Proj.\n"
            f"Item                                                           {previous}           {current}\n"
            "================================================================================\n"
            "                                                Million Metric Tons\n"
            "FEED GRAINS\n"
            "Ending Stocks                    42.3          56.0          47.2          46.5\n"
            "                                                  Million Acres\n"
            "CORN\n"
            "Area Planted                     90.9          98.7          96.8          96.8\n"
            f"                                                 {unit}\n"
            f"Beginning Stocks                 1763          1551          2095          2095\n"
            f"Ending Stocks                    1551          2095          {earlier}          {outcome}\n"
            "Avg.FarmPrice ($/bu)             4.24          4.16          4.60          4.70\n"
            "================================================================================\n"
            "            U.S. Sorghum, Barley, and Oats Supply and Use\n"
           ).encode("utf-8")

def meta(start="2026-12-10T17:01:00Z",end="2026-12-10T17:01:01Z",
         url="https://esmis.nal.usda.gov/sites/default/release-files/796142/wasde1226.txt"):
    return {"requested_url":url,"response_url":url,
            "fetch_started_utc":start,"fetch_finished_utc":end}

class USDAOfficialOutcomeTests(unittest.TestCase):
    def test_original_frozen_forecast_contract_is_not_modified(self):
        sha=validate_locked()
        self.assertEqual(sha,"54d4d7597d457c64307e9a2e1e5670cd5f1ecd52676180eded2a19a8ebcaca48")

    def test_synthetic_december_table_corn_not_feed_grains(self):
        o=parse_wasde_corn(make_source())
        self.assertEqual(o["previous_month_ending_stock_mbu"],1758)
        self.assertEqual(o["current_month_ending_stock_mbu"],1700)
        self.assertEqual(o["unit"],"million_bushels")

    def test_november_official_layout_format_same_parser(self):
        b=make_source(month="November",previous="Oct",current="Nov",
                      earlier=1849,outcome=1758)
        o=parse_wasde_corn(b,"November","Oct","Nov")
        self.assertEqual(o["current_month_ending_stock_mbu"],1758)

    def test_official_only_v0_score_without_consensus(self):
        r=assess(make_source(),meta())
        self.assertEqual(r["status"],"OFFICIAL_RAW_V0_SCORED_CONSENSUS_INDEPENDENT")
        self.assertEqual(r["v0_absolute_error_mbu"],58)
        self.assertIsNone(r["market_consensus_mbu"])
        self.assertIsNone(r["consensus_abs_error_mbu"])
        self.assertEqual(r["official_raw_sha256"],hashlib.sha256(make_source()).hexdigest())
        self.assertFalse(r["trade_eligible"])

    def test_wrong_month_november_source_rejected(self):
        with self.assertRaisesRegex(ValueError,"WRONG_WASDE_REPORT_MONTH"):
            assess(make_source(month="November",previous="Oct",current="Nov"),meta())

    def test_prior_month_reference_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"NOVEMBER_ORIGINAL_REFERENCE_CHANGED"):
            assess(make_source(earlier=1759),meta())

    def test_wrong_units_rejected(self):
        with self.assertRaisesRegex(ValueError,"CORN_VOLUME_UNITS_NOT_MILLION_BUSHELS"):
            assess(make_source(unit="Million Metric Tons"),meta())

    def test_wrong_year_rejected(self):
        with self.assertRaisesRegex(ValueError,"WRONG_MARKETING_YEAR"):
            assess(make_source(year="2025/26"),meta())

    def test_missing_latest_month_column_rejected(self):
        with self.assertRaisesRegex(ValueError,"WRONG_WASDE_MONTHLY_COLUMNS"):
            assess(make_source(current="Nov"),meta())

    def test_duplicate_corn_subsection_rejected(self):
        b=make_source().replace(b"CORN\n",b"CORN\nCORN\n")
        with self.assertRaisesRegex(ValueError,"CORN_SUBSECTION_NOT_UNIQUE"):
            assess(b,meta())

    def test_not_our_official_host_rejected(self):
        with self.assertRaisesRegex(ValueError,"NOT_EXACT_OFFICIAL"):
            assess(make_source(),meta(url="https://example.org/wasde1226.txt"))

    def test_capture_before_release_makes_no_network_request(self):
        def forbidden():
            raise AssertionError("NO_HTTP_BEFORE_WASDE")
        with tempfile.TemporaryDirectory() as d:
            r=capture(d,forbidden,clock=lambda:"2026-11-17T04:00:00Z")
            self.assertEqual(r["status"],"BLOCKED_DECEMBER_WASDE_NOT_YET_RELEASED")
            self.assertEqual(list(Path(d).glob("*")),[])

    def test_synthetic_postrelease_capture_saves_original_and_pair(self):
        with tempfile.TemporaryDirectory() as d:
            r=capture(d,lambda:(make_source(),meta()),clock=lambda:"2026-12-10T17:01:00Z")
            self.assertEqual(r["status"],"OFFICIAL_RAW_V0_SCORED_CONSENSUS_INDEPENDENT")
            self.assertEqual(r["official_value_mbu"],1700)
            self.assertEqual(r["v0_absolute_error_mbu"],58)
            self.assertEqual(len(list(Path(d).iterdir())),3)
            self.assertEqual((Path(d)/r["raw_file"]).read_bytes(),make_source())
            result=json.loads((Path(d)/r["score_file"]).read_text())
            self.assertIsNone(result["market_consensus_mbu"])
            self.assertEqual(result["official_raw_sha256"],r["official_raw_sha256"])

    def test_duplicate_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            good=capture(d,lambda:(make_source(),meta()),clock=lambda:"2026-12-10T17:01:00Z")
            bad=capture(d,lambda:(make_source(),meta()),clock=lambda:"2026-12-10T17:02:00Z")
            self.assertEqual(good["status"],"OFFICIAL_RAW_V0_SCORED_CONSENSUS_INDEPENDENT")
            self.assertEqual(bad["status"],"BLOCKED_OFFICIAL_WASDE_NOT_VALIDATED")
            self.assertEqual(len(list(Path(d).iterdir())),3)

    def test_future_source_is_unknown_today(self):
        with tempfile.TemporaryDirectory() as d:
            result=capture(d,clock=lambda:"2026-11-17T00:00:00Z")
            self.assertIsNone(result["official_raw_sha256"])

if __name__=="__main__":
    unittest.main()

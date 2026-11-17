"""K5.2 offline checks. Future EIA outcomes below are synthetic fixtures, NOT actual Nov19 data."""
import json
from pathlib import Path
import unittest

from research_core.k5.official_event_score import (
    ROOT,FROZEN,FIRST,PRIOR_RECEIPT, evaluate, official_parsed,
    frozen_checked,prior_checked,git_blob_sha,FROZEN_BLOB_SHA,
)

def fake_new(current=3890,previous=3862,change=28):
    data=json.loads(FIRST.read_bytes().decode("utf-8-sig"))
    data["release_date"]="2026-Nov-19 00:00:00"
    data["current_week"]="2026-11-13"
    data["week_ago"]="2026-11-06"
    data["year_ago"]="2025-11-13"
    s=next(x for x in data["series"] if x["series_id"]=="png.nw2_epg0_swo_r48_bcf.w")
    s["data"]=[["2026-11-13",current],["2026-11-06",previous],["2025-11-13",3880]]
    s["calculated"]["net_change"]=change
    s["calculated"]["implied_flow"]=change
    return json.dumps(data,separators=(",",":"),ensure_ascii=True).encode("utf-8")

def meta(start="2026-11-19T15:31:00Z",end="2026-11-19T15:31:01Z"):
    return {"requested_url":"https://ir.eia.gov/ngs/wngsr.json",
            "response_host":"ir.eia.gov",
            "response_path":"/secure/ngs/wngsr.json",
            "capture_started_utc":start,"capture_finished_utc":end}

def evaluate_fake(raw=None,capture=None):
    return evaluate(FROZEN.read_bytes(),FIRST.read_bytes(),PRIOR_RECEIPT.read_bytes(),
                    fake_new() if raw is None else raw,meta() if capture is None else capture)

class K52StrictOriginalEventTests(unittest.TestCase):
    def test_github_frozen_original_unmodified(self):
        data=FROZEN.read_bytes()
        self.assertEqual(git_blob_sha(data),FROZEN_BLOB_SHA)
        self.assertEqual(frozen_checked(data)["forecast_net_change_bcf"],61)

    def test_real_prior_original_and_receipt_are_integral(self):
        p=prior_checked(FIRST.read_bytes(),PRIOR_RECEIPT.read_bytes())
        self.assertEqual(p["source_report"]["storage_bcf"],3862)
        self.assertEqual(p["source_report"]["net_change_bcf"],61)

    def test_future_unknown_outcome_stays_null(self):
        r=evaluate(FROZEN.read_bytes(),FIRST.read_bytes(),PRIOR_RECEIPT.read_bytes())
        self.assertEqual(r["status"],"WAITING_FOR_NOV19_OFFICIAL_EIA_ORIGINAL")
        self.assertIsNone(r["actual_net_change_bcf"])
        self.assertIsNone(r["v0_absolute_error_bcf"])
        self.assertFalse(r["trade_eligible"])

    def test_synthetic_future_parse_only_descriptive_score(self):
        r=evaluate_fake()
        self.assertEqual(r["actual_net_change_bcf"],28)
        self.assertEqual(r["v0_absolute_error_bcf"],33)
        self.assertEqual(r["revised_prior_week_bcf"],0)
        self.assertEqual(r["status"],"ONE_EVENT_OFFICIAL_RAW_DESCRIPTIVE_SCORE_ONLY")
        self.assertFalse(r["independent_pit_first_publication_verified"])
        self.assertFalse(r["alpha_or_trade_verified"])
        self.assertFalse(r["trade_eligible"])

    def test_synthetic_prior_stock_revision_recorded_not_hidden(self):
        r=evaluate_fake(fake_new(current=3892,previous=3864,change=28))
        self.assertEqual(r["revised_prior_week_bcf"],2)
        self.assertTrue(r["official_data_checks"]["prior_source_vintage_revised"])
        self.assertEqual(r["v0_absolute_error_bcf"],33)

    def test_wrong_reporting_week_rejected(self):
        data=json.loads(fake_new())
        data["current_week"]="2026-11-06"
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_EVENT_WEEK"):
            evaluate_fake(json.dumps(data).encode())

    def test_wrong_release_date_rejected(self):
        data=json.loads(fake_new())
        data["release_date"]="2026-Nov-13 00:00:00"
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_EVENT_WEEK"):
            evaluate_fake(json.dumps(data).encode())

    def test_wrong_series_and_unit_rejected(self):
        data=json.loads(fake_new())
        for row in data["series"]:
            if row["series_id"]=="png.nw2_epg0_swo_r48_bcf.w":
                row["unitsshort"]="Mcf"
        with self.assertRaisesRegex(ValueError,"WRONG_SERIES_UNITS_OR_SOURCE"):
            evaluate_fake(json.dumps(data).encode())

    def test_official_change_does_not_match_stocks(self):
        with self.assertRaisesRegex(ValueError,"OFFICIAL_CHANGE_LEVEL_RECONCILIATION"):
            evaluate_fake(fake_new(current=3890,previous=3862,change=55))

    def test_not_official_url_rejected(self):
        m=meta();m["response_host"]="example.com"
        with self.assertRaisesRegex(ValueError,"NOT_OFFICIAL_EIA_DATA_URL"):
            evaluate_fake(capture=m)

    def test_capture_before_schedule_rejected(self):
        with self.assertRaisesRegex(ValueError,"RESULT_CAPTURE_BEFORE_EIA_SCHEDULE"):
            evaluate_fake(capture=meta(start="2026-11-19T15:29:00Z"))

    def test_capture_timestamps_reversed_rejected(self):
        with self.assertRaisesRegex(ValueError,"RESULT_CAPTURE_BEFORE_EIA_SCHEDULE"):
            evaluate_fake(capture=meta(start="2026-11-19T15:32:00Z",end="2026-11-19T15:31:00Z"))

    def test_forecast_altered_even_if_json_still_valid_rejected(self):
        x=json.loads(FROZEN.read_text())
        x["forecast_net_change_bcf"]=63
        with self.assertRaisesRegex(ValueError,"PRE_RELEASE_FORECAST_BYTES_CHANGED"):
            evaluate(json.dumps(x).encode(),FIRST.read_bytes(),PRIOR_RECEIPT.read_bytes())

    def test_previous_original_tamper_rejected(self):
        with self.assertRaisesRegex(ValueError,"PRIOR_OFFICIAL_SOURCE_TAMPERED"):
            evaluate(FROZEN.read_bytes(),FIRST.read_bytes()+b" ",PRIOR_RECEIPT.read_bytes())

    def test_future_file_is_not_inserted_by_just_a_number(self):
        with self.assertRaisesRegex(ValueError,"EIA_SOURCE_AND_CAPTURE_REQUIRED"):
            evaluate(FROZEN.read_bytes(),FIRST.read_bytes(),PRIOR_RECEIPT.read_bytes(),
                     fake_new(),None)

if __name__=="__main__":
    unittest.main()

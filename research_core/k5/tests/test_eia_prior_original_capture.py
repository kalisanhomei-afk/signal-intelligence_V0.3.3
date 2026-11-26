"""K5.1 fail-closed EIA prior-original source capture tests, no network needed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research_core.k5.eia_prior_original_capture import capture,validate_data,SCHEDULE

DATA={
    "release_name":"Weekly Natural Gas Storage Report",
    "release_date":"2026-Nov-13 00:00:00",
    "current_week":"2026-11-06",
    "week_ago":"2026-10-30",
    "year_ago":"2025-11-06",
    "5yr_avg":"5-year (2021-25) average",
    "fuel_type":"natural gas",
    "process":"storage",
    "periodicity":"weekly",
    "series":[
        {"series_id":"png.nw2_epg0_swo_r48_bcf.w",
         "name":"total lower 48 states",
         "source":"U.S. Energy Information Administration",
         "unitsshort":"bcf",
         "calculated":{"net_change":61,"implied_flow":61,"5yr-avg":3787},
         "data":[["2026-11-06",3862],["2026-10-30",3801],["2025-11-06",3954]]}
    ]
}

def raw(case=None):
    return json.dumps(DATA if case is None else case,separators=(",",":"),ensure_ascii=False).encode()

def fetcher(content=None,started="2026-11-17T03:00:00Z",finished="2026-11-17T03:00:01Z"):
    def fx():
        return raw() if content is None else content,{
            "requested_url":"https://ir.eia.gov/ngs/wngsr.json",
            "response_host":"ir.eia.gov",
            "response_path":"/secure/ngs/wngsr.json",
            "signed_redirect_query_deliberately_omitted":True,
            "capture_started_utc":started,
            "capture_finished_utc":finished,
            "content_type_claim":"application/json",
            "last_modified_claim":None,
            "etag_claim":None
        }
    return fx

class EIAOriginalCaptureTests(unittest.TestCase):
    def test_official_lower48_parse(self):
        r=validate_data(raw())
        self.assertEqual(r["net_change_bcf"],61)
        self.assertEqual(r["storage_bcf"],3862)
        self.assertEqual(r["five_year_average_storage_bcf"],3787)
        self.assertEqual(r["week_end"],"2026-11-06")
        self.assertFalse(r["all_source_revision_flags_independently_audited"])

    def test_source_bom_accepted_without_changing_hash(self):
        b=b"\xef\xbb\xbf"+raw()
        self.assertEqual(validate_data(b)["net_change_bcf"],61)
        with tempfile.TemporaryDirectory() as d:
            result=capture(Path(d),fetcher(b))
            self.assertEqual(result["source_raw_sha256"],hashlib.sha256(b).hexdigest())
            self.assertEqual((Path(d)/result["source_raw_file"]).read_bytes(),b)

    def test_wrong_week_rejected(self):
        data=json.loads(raw())
        data["current_week"]="2026-11-13"
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_RELEASE_OR_WEEK"):
            validate_data(raw(data))

    def test_wrong_release_rejected(self):
        data=json.loads(raw())
        data["release_date"]="2026-Nov-19 00:00:00"
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_RELEASE_OR_WEEK"):
            validate_data(raw(data))

    def test_wrong_series_or_units_rejected(self):
        data=json.loads(raw())
        data["series"][0]["unitsshort"]="Mcf"
        with self.assertRaisesRegex(ValueError,"WRONG_LOWER48_UNITS_OR_PROVENANCE"):
            validate_data(raw(data))
        data=json.loads(raw())
        data["series"][0]["series_id"]="other"
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS_LOWER48_SERIES"):
            validate_data(raw(data))

    def test_tampered_change_rejected(self):
        data=json.loads(raw())
        data["series"][0]["calculated"]["net_change"]=62
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_NET_CHANGE"):
            validate_data(raw(data))

    def test_tampered_stocks_rejected(self):
        data=json.loads(raw())
        data["series"][0]["data"][0][1]=3800
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_STOCKS_OR_DATES"):
            validate_data(raw(data))

    def test_actual_full_bytes_and_receipt_pair(self):
        with tempfile.TemporaryDirectory() as d:
            result=capture(d,fetcher())
            self.assertEqual(result["status"],"PRIOR_EIA_ORIGINAL_BYTES_CAPTURED_BEFORE_NEXT_EVENT")
            self.assertEqual(result["source_raw_sha256"],hashlib.sha256(raw()).hexdigest())
            self.assertEqual((Path(d)/result["source_raw_file"]).read_bytes(),raw())
            receipt=json.loads((Path(d)/result["source_raw_file"].replace("_original.json","_receipt.json")).read_text())
            self.assertEqual(result,receipt)
            self.assertFalse(result["trade_eligible"])
            self.assertFalse(result["noaa_ex_ante_vintages_verified"])

    def test_capture_at_or_after_future_release_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            result=capture(d,fetcher(finished=SCHEDULE))
            self.assertEqual(result["status"],"BLOCKED_NO_VALID_EIA_PRIOR_RELEASE_ORIGINAL")
            self.assertIsNone(result["source_raw_sha256"])
            self.assertEqual(list(Path(d).glob("*")),[])

    def test_mismatched_source_capture_timestamps_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            result=capture(d,fetcher(started="2026-11-17T03:01:00Z",finished="2026-11-17T03:00:00Z"))
            self.assertTrue(result["status"].startswith("BLOCKED"))

    def test_successful_archive_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            a=capture(d,fetcher())
            b=capture(d,fetcher(finished="2026-11-17T03:30:00Z"))
            self.assertEqual(b["status"],"BLOCKED_NO_VALID_EIA_PRIOR_RELEASE_ORIGINAL")
            self.assertEqual(b["reason"],"SOURCE_ARCHIVE_ALREADY_EXISTS_NO_OVERWRITE")
            receipt_files=list(Path(d).glob("*_receipt.json"))
            self.assertEqual(len(receipt_files),1)
            self.assertEqual(json.loads(receipt_files[0].read_text())["source"]["capture_finished_utc"],
                             "2026-11-17T03:00:01Z")

"""K4.8 future report capture: fail closed on wrong weeks, mismatched totals, and timing."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from research_core.k4.fgis_forward_capture import extract_header_and_corn,capture,SOURCES

REPORT=(
    "WA_GR101\nWashington, DC    Mon   Nov 16, 2026   USDA Market News\n"
    "*CORRECTIONS AT BOTTOM OF REPORT ARE INCLUDED IN CURRENT MARKET YEAR TO DATE*\n"
    "GRAINS INSPECTED AND/OR WEIGHED FOR EXPORT\n"
    "REPORTED IN WEEK ENDING NOV 12, 2026\n"
    "BARLEY 499 0 122 1364 5289\n"
    "CORN 865,503 908,378 2,066,210 12,463,023 15,851,319\n"
).encode("utf-8")
def fake(source):
    return REPORT,{"requested_url":source,"response_url":source,
                   "fetch_started_utc":"2026-11-17T02:10:00Z",
                   "fetch_finished_utc":"2026-11-17T02:10:01Z",
                   "source_etag":None,"source_last_modified_claim":None,
                   "source_content_type":"text/plain"}

class FGISForwardCaptureTests(unittest.TestCase):
    def test_expected_official_wa_gr101_summary(self):
        d=extract_header_and_corn(REPORT)
        self.assertEqual(d["corn_week_current_mt"],865503)
        self.assertEqual(d["corn_marketing_year_to_date_mt"],12463023)
        self.assertTrue(d["raw_report_revision_warning_present"])

    def test_wrong_week_never_captured(self):
        with self.assertRaisesRegex(ValueError,"WEEK_END_NOT_EXPECTED"):
            extract_header_and_corn(REPORT.replace(b"NOV 12",b"NOV 05"))

    def test_wrong_report_date_never_captured(self):
        with self.assertRaisesRegex(ValueError,"REPORT_DATE_NOT_EXPECTED"):
            extract_header_and_corn(REPORT.replace(b"Nov 16",b"Nov 09"))

    def test_wrong_total_never_captured(self):
        with self.assertRaisesRegex(ValueError,"REPORT_NUMBERS_UNEXPECTED"):
            extract_header_and_corn(REPORT.replace(b"865,503",b"865,504"))

    def test_capture_contains_bytes_and_sha(self):
        with tempfile.TemporaryDirectory() as d:
            r=capture(Path(d),fake)
            self.assertTrue(r["status"].startswith("CAPTURED_"))
            self.assertEqual(r["source_raw_sha256"],hashlib.sha256(REPORT).hexdigest())
            self.assertEqual((Path(d)/r["source_raw_file"]).read_bytes(),REPORT)
            self.assertFalse(r["trade_eligible"])
            self.assertFalse(r["source_report_first_publication_utc_independently_verified"])
            self.assertFalse(r["repo_commit_provides_independent_timestamp_certificate"])

    def test_after_release_cannot_be_backfilled(self):
        def late(source):
            raw,meta=fake(source)
            meta["fetch_finished_utc"]="2026-12-10T17:00:00Z"
            return raw,meta
        with tempfile.TemporaryDirectory() as d:
            r=capture(Path(d),late)
            self.assertEqual(r["status"],"BLOCKED_NO_VALID_OFFICIAL_RAW_BYTES")
            self.assertFalse((Path(d)/"WA_GR101_20261116_official_captured.txt").exists())
            self.assertEqual(len(r["attempts"]),len(SOURCES))

    def test_no_official_source_retrievable_keeps_null(self):
        def broken(source):
            raise ValueError("HTTP_403")
        with tempfile.TemporaryDirectory() as d:
            r=capture(Path(d),broken)
            self.assertEqual(r["status"],"BLOCKED_NO_VALID_OFFICIAL_RAW_BYTES")
            self.assertIsNone(r["source_raw_sha256"])
            self.assertFalse(r["trade_eligible"])
            self.assertTrue((Path(d)/"capture_receipt.json").exists())

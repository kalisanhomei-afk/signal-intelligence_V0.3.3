"""K4.8 committed prospective USDA FGIS source bytes and receipt: immutable-intent regression."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

from research_core.k4.fgis_forward_capture import extract_header_and_corn

ROOT=Path(__file__).resolve().parents[1] / "evidence" / "fgis"
RAW=ROOT / "WA_GR101_20261116_official_raw.txt"
RECEIPT=ROOT / "WA_GR101_20261116_capture_receipt.json"

class CommittedFGISForwardEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=RAW.read_bytes()
        cls.r=json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_official_source_byte_exact_identity(self):
        self.assertEqual(len(self.raw),18499)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),
                         "4555c478b09d2507d042de55c6d5042e095f37b13d05185fcf889433c52802e5")
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),self.r["source_raw_sha256"])
        self.assertEqual(len(self.raw),self.r["source_raw_bytes"])
        self.assertTrue(self.raw.startswith(b"WA_GR101\r\n"))

    def test_actual_captured_values_reproducible(self):
        d=extract_header_and_corn(self.raw)
        self.assertEqual(d,self.r["source_report"])
        self.assertEqual(d["corn_week_current_mt"],865503)
        self.assertEqual(d["corn_marketing_year_to_date_mt"],12463023)
        self.assertTrue(d["raw_report_revision_warning_present"])

    def test_report_capture_precedes_december_wasde(self):
        src=self.r["source"]
        t=lambda v:datetime.fromisoformat(v.replace("Z","+00:00"))
        self.assertLess(t(src["fetch_started_utc"]),t(src["fetch_finished_utc"]))
        self.assertLess(t(src["fetch_finished_utc"]),t(self.r["future_wasde_scheduled_utc"]))
        self.assertEqual(self.r["status"],"CAPTURED_PRE_DECEMBER_RELEASE_NOT_INDEPENDENT_PIT_CERTIFIED")
        self.assertEqual(src["requested_url"],"https://www.ams.usda.gov/mnreports/wa_gr101.txt")
        self.assertEqual(src["response_url"],src["requested_url"])

    def test_source_header_not_pit_certification(self):
        self.assertFalse(self.r["source_report_first_publication_utc_independently_verified"])
        self.assertFalse(self.r["source_history_corrections_eliminated"])
        self.assertFalse(self.r["repo_commit_provides_independent_timestamp_certificate"])
        self.assertFalse(self.r["trade_eligible"])
        self.assertFalse(self.r["predictive_edge_verified"])

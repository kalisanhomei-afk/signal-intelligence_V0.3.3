"""K4.9 generic archive auditor: validate real Nov16 and future weekly receipt chain."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from research_core.k4.fgis_archive_audit import audit
from research_core.k4.fgis_weekly_vintage import capture,ROLLING

ORIGINAL=Path(__file__).resolve().parents[1]/"evidence"/"fgis"
FILENAME="WA_GR101_20261116_official_raw.txt"
RECEIPT="WA_GR101_20261116_capture_receipt.json"

def newreport():
    r=(ORIGINAL/FILENAME).read_bytes()
    r=r.replace(b"Mon   Nov 16, 2026",b"Mon   Nov 23, 2026",1)
    r=r.replace(b"REPORTED IN WEEK ENDING NOV 12, 2026",
                b"REPORTED IN WEEK ENDING NOV 19, 2026",1)
    r=r.replace(b"GRAIN      11/12/2026  11/05/2026  11/13/2025",
                b"GRAIN      11/19/2026  11/12/2026  11/20/2025",1)
    old=b"CORN          865,503     908,378   2,066,210   12,463,023   15,851,319"
    new=b"CORN         1,000,000     870,000   2,066,210   13,467,520   15,851,319"
    assert old in r
    return r.replace(old,new,1)

def capture_new(folder):
    def provider(url):
        return newreport(),{"requested_url":url,"response_url":ROLLING,
            "fetch_started_utc":"2026-11-24T00:00:00Z",
            "fetch_finished_utc":"2026-11-24T00:00:01Z",
            "source_last_modified_claim":None,
            "source_etag":None}
    return capture("2026-11-23","2026-11-19","2026-12-10T17:00:00Z",folder,
                   prior_raw=folder/FILENAME,prior_receipt=folder/RECEIPT,
                   fetcher=provider)

def copy_old(dest):
    for name in (FILENAME,RECEIPT):
        shutil.copyfile(ORIGINAL/name,Path(dest)/name)

class FGISArchiveAuditTests(unittest.TestCase):
    def test_existing_nov16_official_original_audits(self):
        r=audit(ORIGINAL)
        self.assertEqual(r["distinct_weeks"],1)
        self.assertEqual(r["version_count"],1)
        self.assertEqual(r["week_ends"],["2026-11-12"])
        self.assertEqual(r["observations"][0]["corn_week_mt"],865503)
        self.assertFalse(r["trade_eligible"])

    def test_new_report_plus_previous_revision_chain(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            copy_old(root)
            created=capture_new(root)
            self.assertTrue(created["status"].startswith("CAPTURED_"))
            r=audit(root)
            self.assertEqual(r["distinct_weeks"],2)
            self.assertEqual(r["version_count"],2)
            self.assertEqual(r["observations"][-1]["prior_comparison"]["previous_week_revision_delta_mt"],4497)
            self.assertFalse(r["first_published_content_independently_attested"])

    def test_tampered_original_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);copy_old(root)
            with (root/FILENAME).open("ab") as f:f.write(b"tampered")
            with self.assertRaisesRegex(ValueError,"ORIGINAL_RAW_BYTES_MISMATCH"):
                audit(root)

    def test_trade_promotion_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);copy_old(root)
            x=json.loads((root/RECEIPT).read_text(encoding="utf-8"))
            x["trade_eligible"]=True
            (root/RECEIPT).write_text(json.dumps(x),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_TRADE_PROMOTION"):
                audit(root)

    def test_claimed_prior_without_raw_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);copy_old(root)
            created=capture_new(root)
            (root/RECEIPT).unlink()
            (root/FILENAME).unlink()
            with self.assertRaisesRegex(ValueError,"REFERENCED_PREVIOUS_SOURCE_NOT_ARCHIVED"):
                audit(root)

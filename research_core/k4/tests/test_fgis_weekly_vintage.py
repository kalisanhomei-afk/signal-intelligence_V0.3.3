"""K4.9 weekly FGIS prospective capture: bytes, revisions, cutoffs and no overwrites."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research_core.k4.fgis_weekly_vintage import capture, parse_report, allowed, ROLLING

ROOT=Path(__file__).resolve().parents[1] / "evidence" / "fgis"
OLD=ROOT / "WA_GR101_20261116_official_raw.txt"
OLD_RECEIPT=ROOT / "WA_GR101_20261116_capture_receipt.json"
RAW=OLD.read_bytes()
OLD_ROW=b"CORN          865,503     908,378   2,066,210   12,463,023   15,851,319"

def next_week(current=1000000,reported_prev=865503,total=13463023):
    raw=RAW
    raw=raw.replace(b"Mon   Nov 16, 2026",b"Mon   Nov 23, 2026",1)
    raw=raw.replace(b"REPORTED IN WEEK ENDING NOV 12, 2026",
                    b"REPORTED IN WEEK ENDING NOV 19, 2026",1)
    raw=raw.replace(b"GRAIN      11/12/2026  11/05/2026  11/13/2025",
                    b"GRAIN      11/19/2026  11/12/2026  11/20/2025",1)
    newrow=f"CORN       {current:,}      {reported_prev:,}    2,066,210    {total:,}    15,851,319".encode()
    assert OLD_ROW in raw
    return raw.replace(OLD_ROW,newrow,1)

def provider(raw=None, finished="2026-11-24T00:00:01Z", source=ROLLING):
    def fetch(url):
        return (raw if raw is not None else next_week()),{
            "requested_url":url, "response_url":source,
            "fetch_started_utc":"2026-11-24T00:00:00Z",
            "fetch_finished_utc":finished,
            "source_last_modified_claim":"Mon, 23 Nov 2026 16:00:00 GMT",
            "source_etag":None,
        }
    return fetch

def kwargs(directory):
    return dict(report_date="2026-11-23",week_end="2026-11-19",
                cutoff_utc="2026-12-10T17:00:00Z",output_dir=directory)

class FGISWeeklyVintageTests(unittest.TestCase):
    def test_backward_compatibility_existing_real_raw(self):
        r=parse_report(RAW,"2026-11-16","2026-11-12")
        self.assertEqual(r["corn_week_current_mt"],865503)
        self.assertEqual(r["corn_marketing_year_to_date_mt"],12463023)
        self.assertEqual(r["previous_week_end"],"2026-11-05")

    def test_synthetic_next_week_is_parsed(self):
        r=parse_report(next_week(),"2026-11-23","2026-11-19")
        self.assertEqual(r["corn_week_current_mt"],1000000)
        self.assertEqual(r["corn_week_previous_mt"],865503)
        self.assertEqual(r["previous_week_end"],"2026-11-12")

    def test_wrong_report_date_blocked(self):
        with self.assertRaisesRegex(ValueError,"WRONG_REPORT_DATE"):
            parse_report(RAW,"2026-11-23","2026-11-19")

    def test_wrong_week_end_blocked(self):
        with self.assertRaisesRegex(ValueError,"WRONG_WEEK_END"):
            parse_report(next_week(),"2026-11-23","2026-11-20")

    def test_non_official_slug_rejected(self):
        with self.assertRaisesRegex(ValueError,"REPORT_SLUG_MISMATCH"):
            parse_report(next_week().replace(b"WA_GR101",b"NOT_GR101",1),
                         "2026-11-23","2026-11-19")

    def test_bad_weekday_rejected(self):
        with self.assertRaisesRegex(ValueError,"REPORT_WEEKDAY_INCONSISTENT"):
            parse_report(next_week().replace(b"Mon   Nov 23",b"Tue   Nov 23",1),
                         "2026-11-23","2026-11-19")

    def test_injecting_extra_top_corn_row_fails(self):
        r=next_week()
        start=r.index(b"CORN       1,000,000")
        end=r.index(b"\r\n",start)
        r=r[:end]+b"\r\n"+r[start:end]+r[end:]
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS_TOP_CORN_ROW"):
            parse_report(r,"2026-11-23","2026-11-19")

    def test_historical_url_report_date_must_match(self):
        good="https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/3071/2026-11-23/1365708/ams_3071_00354.txt"
        self.assertTrue(allowed(good,"2026-11-23"))
        with self.assertRaisesRegex(ValueError,"WRONG_OFFICIAL_HISTORICAL_DATE"):
            allowed(good,"2026-11-30")

    def test_untrusted_url_rejected(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_URL_NOT_ALLOWED"):
            allowed("https://example.com/wa_gr101.txt","2026-11-23")
        with self.assertRaisesRegex(ValueError,"SOURCE_URL_NOT_ALLOWED"):
            allowed(ROLLING+"?random=1","2026-11-23")

    def test_capture_new_week_creates_exact_unchanging_pair(self):
        raw=next_week()
        with tempfile.TemporaryDirectory() as d:
            r=capture(**kwargs(d),fetcher=provider(raw))
            self.assertTrue(r["status"].startswith("CAPTURED_"))
            self.assertEqual(r["source_raw_sha256"],hashlib.sha256(raw).hexdigest())
            self.assertEqual((Path(d)/r["raw_filename"]).read_bytes(),raw)
            receipt=json.loads((Path(d)/r["receipt_filename"]).read_text())
            self.assertEqual(receipt["source_raw_sha256"],r["source_raw_sha256"])
            self.assertFalse(r["trade_eligible"])
            self.assertFalse(r["source_first_publication_time_independently_verified"])

    def test_previous_week_unrevised_and_cumulative(self):
        with tempfile.TemporaryDirectory() as d:
            r=capture(**kwargs(d),prior_raw=OLD,prior_receipt=OLD_RECEIPT,
                      fetcher=provider())
            self.assertEqual(r["prior_report_comparison"]["status"],"PREVIOUS_WEEK_UNCHANGED")
            self.assertEqual(r["prior_report_comparison"]["previous_week_revision_delta_mt"],0)
            self.assertEqual(r["prior_report_comparison"]["cumulative_implied_other_revisions_mt"],0)

    def test_revision_from_original_versus_reported_week(self):
        raw=next_week(reported_prev=870000,total=13467520)
        with tempfile.TemporaryDirectory() as d:
            r=capture(**kwargs(d),prior_raw=OLD,prior_receipt=OLD_RECEIPT,
                      fetcher=provider(raw))
            p=r["prior_report_comparison"]
            self.assertEqual(p["status"],"PREVIOUS_WEEK_REVISED")
            self.assertEqual(p["previous_week_revision_delta_mt"],4497)
            self.assertEqual(p["cumulative_implied_other_revisions_mt"],4497)
            self.assertFalse(r["source_corrections_independently_certified"])

    def test_no_overwrite_when_same_data_seen_again(self):
        with tempfile.TemporaryDirectory() as d:
            a=capture(**kwargs(d),fetcher=provider())
            b=capture(**kwargs(d),fetcher=provider(finished="2026-11-24T01:00:00Z"))
            self.assertEqual(b["status"],"ALREADY_ARCHIVED_IDENTICAL_BYTES")
            self.assertEqual(len(list(Path(d).glob("*official_raw.txt"))),1)
            saved=json.loads((Path(d)/a["receipt_filename"]).read_text())
            self.assertEqual(saved["source"]["fetch_finished_utc"],"2026-11-24T00:00:01Z")

    def test_new_revision_same_report_date_preserves_first_raw(self):
        with tempfile.TemporaryDirectory() as d:
            a=capture(**kwargs(d),fetcher=provider())
            b=capture(**kwargs(d),fetcher=provider(next_week(1000001,865503,13463024)))
            self.assertNotEqual(a["source_raw_sha256"],b["source_raw_sha256"])
            self.assertTrue((Path(d)/a["raw_filename"]).exists())
            self.assertTrue((Path(d)/b["raw_filename"]).exists())
            self.assertEqual(len(list(Path(d).glob("*official_raw.txt"))),2)

    def test_late_capture_rejected_without_raw_archive(self):
        with tempfile.TemporaryDirectory() as d:
            r=capture(**kwargs(d),fetcher=provider(finished="2026-12-10T17:00:00Z"))
            self.assertEqual(r["status"],"BLOCKED_NO_VALID_OFFICIAL_REPORT")
            self.assertIsNone(r["source_raw_sha256"])
            self.assertEqual(list(Path(d).glob("*.txt")),[])

    def test_stale_week_rejected_even_if_download_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            r=capture(**kwargs(d),fetcher=provider(raw=RAW))
            self.assertEqual(r["status"],"BLOCKED_NO_VALID_OFFICIAL_REPORT")
            self.assertTrue(any(x["reason"]=="WRONG_REPORT_DATE" for x in r["attempts"]))

    def test_tampered_previous_report_blocks_revision_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/"fake_raw.txt"
            fake.write_bytes(OLD.read_bytes()+b"changed")
            r=capture(**kwargs(d),prior_raw=fake,prior_receipt=OLD_RECEIPT,
                      fetcher=provider())
            self.assertEqual(r["status"],"BLOCKED_NO_VALID_OFFICIAL_REPORT")
            self.assertTrue(any(x["reason"]=="PREVIOUS_RAW_SHA_MISMATCH" for x in r["attempts"]))

    def test_previous_capture_from_future_cannot_be_used(self):
        with tempfile.TemporaryDirectory() as d:
            forged=json.loads(OLD_RECEIPT.read_text(encoding="utf-8"))
            forged["source"]["fetch_finished_utc"]="2026-11-25T00:00:00Z"
            p=Path(d)/"forged_receipt.json"
            p.write_text(json.dumps(forged),encoding="utf-8")
            r=capture(**kwargs(d),prior_raw=OLD,prior_receipt=p,
                      fetcher=provider())
            self.assertEqual(r["status"],"BLOCKED_NO_VALID_OFFICIAL_REPORT")
            self.assertTrue(any(x["reason"]=="PREVIOUS_CAPTURE_NOT_BEFORE_CURRENT"
                                for x in r["attempts"]))

    def test_prior_receipt_numbers_must_equal_original_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            forged=json.loads(OLD_RECEIPT.read_text(encoding="utf-8"))
            forged["source_report"]["corn_week_current_mt"]=865504
            p=Path(d)/"forged_values.json"
            p.write_text(json.dumps(forged),encoding="utf-8")
            r=capture(**kwargs(d),prior_raw=OLD,prior_receipt=p,
                      fetcher=provider())
            self.assertEqual(r["status"],"BLOCKED_NO_VALID_OFFICIAL_REPORT")
            self.assertTrue(any(x["reason"]=="PREVIOUS_RECEIPT_RAW_CONTENT_MISMATCH"
                                for x in r["attempts"]))

    def test_unknown_previous_week_is_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            r=capture(**kwargs(d),fetcher=provider())
            p=r["prior_report_comparison"]
            self.assertEqual(p["status"],"NO_VERIFIED_PREVIOUS_WEEK_CAPTURE")
            self.assertIsNone(p["previous_week_revision_delta_mt"])
            self.assertIsNone(p["cumulative_implied_other_revisions_mt"])

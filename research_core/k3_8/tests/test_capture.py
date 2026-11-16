"""K3.8 deterministic/offline tests. Synthetic reports are never production evidence."""
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.request import Request
from zoneinfo import ZoneInfo

from research_core.k3_8.capture import (
    CaptureError, Fetch, OfficialRedirects, capture, checked_url,
    parse_utc, prior_comparison, report_identity, validate_fetch,
    validate_spec, verify_saved, MAX_BYTES,
)

UTC = timezone.utc
NASS_DATE = "2026-11-16"
NASS_BARRIER = "2026-11-16T21:00:00Z"
NASS_URL = "https://esmis.nal.usda.gov/sites/default/release-files/demo/CropProg-11-16-2026.txt"
NASS_TEXT = b"""Crop Progress

Released November 16, 2026, by the National Agricultural Statistics Service
Corn Harvested for Grain - Selected States
"""
WASDE_DATE = "2026-12-10"
WASDE_BARRIER = "2026-12-10T17:00:00Z"
WASDE_URL = "https://usda.azureedge.us/oce/commodity/wasde/wasde1226.txt"
WASDE_TEXT = b"""WASDE-678
World Agricultural Supply and Demand Estimates
December 10, 2026
Corn: U.S. supply and use
"""


def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def downloaded(src="NASS", raw=None, *, started=None, ended=None, size=None, status=200,
               resolved=None, redirects=(), ctype="text/plain"):
    if raw is None:
        raw = NASS_TEXT if src == "NASS" else WASDE_TEXT
    started = dt(started or ("2026-11-16T21:00:35Z" if src == "NASS"
                             else "2026-12-10T17:00:35Z"))
    ended = dt(ended or ("2026-11-16T21:00:40Z" if src == "NASS"
                         else "2026-12-10T17:00:40Z"))
    url = NASS_URL if src == "NASS" else WASDE_URL
    return Fetch(raw, url, resolved or url, status, ctype, len(raw) if size is None else size,
                 started, ended, tuple(redirects))


def capture_test(tmp, src="NASS", result=None, *, prior=None, output=None, barrier=None,
                 now=None, safety=120):
    result = result or downloaded(src)
    output = output or Path(tmp) / "fresh"
    return capture(
        src, NASS_URL if src == "NASS" else WASDE_URL,
        NASS_DATE if src == "NASS" else WASDE_DATE,
        barrier or (NASS_BARRIER if src == "NASS" else WASDE_BARRIER),
        output, safety_seconds=safety, prior=prior,
        transport=lambda s, u: result,
        preflight_now=now or (dt("2026-11-16T21:00:36Z")
                              if src == "NASS" else dt("2026-12-10T17:00:36Z")),
    )


class ObserverGuards(unittest.TestCase):
    def test_official_nass_immutable_capture_roundtrip(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "run"
            r = capture_test(td, output=root)
            self.assertEqual(r["source_sha256"], hashlib.sha256(NASS_TEXT).hexdigest())
            self.assertEqual(r["first_observed_at_utc"], r["response_finished_at_utc"])
            self.assertEqual(r["safe_feature_not_before_utc"], "2026-11-16T21:02:40.000000Z")
            self.assertEqual(r["timestamp_quality"], "UNKNOWN")
            self.assertFalse(r["pit_certified_historical"])
            self.assertEqual(r["prior_source_comparison"]["status"], "NO_AUTHENTICATED_PRIOR_LEDGER")
            self.assertTrue(verify_saved(root)["verified"])
            self.assertEqual((root / r["raw_path"]).read_bytes(), NASS_TEXT)

    def test_wasde_future_official_report_identity(self):
        with TemporaryDirectory() as td:
            r = capture_test(td, src="WASDE")
            self.assertEqual(r["report_id"], "WASDE-678")
            self.assertEqual(r["report_date_confirmed_from_body"], WASDE_DATE)
            self.assertEqual(r["safe_feature_not_before_utc"], "2026-12-10T17:02:40.000000Z")

    def test_reject_unsupported_or_third_party_domains(self):
        for url in ("http://www.usda.gov/a.txt", "https://evil.usda.gov/a.txt",
                    "https://example.org/a.txt", "https://www.usda.gov/a.pdf",
                    "https://user@www.usda.gov/a.txt", "https://www.usda.gov/a.txt#fragment",
                    "https://www.usda.gov:8080/a.txt"):
            with self.subTest(url=url), self.assertRaises(CaptureError):
                checked_url(url, "WASDE")

    def test_nass_only_nass_official_domains(self):
        with self.assertRaises(CaptureError):
            checked_url("https://www.usda.gov/oce/wasde.txt", "NASS")

    def test_disallowed_redirect_not_followed(self):
        handler = OfficialRedirects("NASS")
        with self.assertRaisesRegex(CaptureError, "NON_OFFICIAL_OR_NON_TEXT_RESOURCE"):
            handler.redirect_request(Request(NASS_URL), None, 302, "moved", {},
                                     "https://malicious.example/steal.txt")

    def test_explicit_utc_required(self):
        for s in ("2026-11-16T21:00:00", "2026-11-16T13:00:00-08:00",
                  "2026-11-16T21:00:00+01:00"):
            with self.subTest(s=s), self.assertRaises(CaptureError):
                parse_utc(s)

    def test_dst_timezone_offset_is_not_assumed(self):
        eastern = ZoneInfo("America/New_York")
        self.assertEqual(dt(NASS_BARRIER).astimezone(eastern).strftime("%H:%M %z"), "16:00 -0500")
        self.assertEqual(dt("2027-06-14T20:00:00Z").astimezone(eastern).strftime("%H:%M %z"), "16:00 -0400")

    def test_future_release_not_run_early(self):
        with self.assertRaisesRegex(CaptureError, "PRE_RELEASE_CAPTURE_NOT_ALLOWED"):
            validate_spec("NASS", NASS_URL, NASS_DATE, NASS_BARRIER, 120,
                          dt("2026-11-16T20:59:59Z"))

    def test_old_historical_backdating_blocked(self):
        with self.assertRaisesRegex(CaptureError, "HISTORICAL_BACKDATING_FORBIDDEN"):
            validate_spec("NASS", NASS_URL, "2016-11-16", NASS_BARRIER, 120,
                          dt("2026-11-16T21:00:40Z"))

    def test_partial_download_detected_and_no_file_written(self):
        with TemporaryDirectory() as td:
            result = downloaded(size=len(NASS_TEXT) + 7)
            with self.assertRaisesRegex(CaptureError, "TRUNCATED_OR_EXTRA"):
                capture_test(td, result=result)
            self.assertFalse((Path(td) / "fresh").exists())

    def test_non_success_http_rejected(self):
        with TemporaryDirectory() as td:
            for code in (403, 404, 500):
                with self.subTest(code=code), self.assertRaisesRegex(CaptureError, "OFFICIAL_HTTP"):
                    capture_test(td, result=downloaded(status=code))
            self.assertFalse((Path(td) / "fresh").exists())

    def test_html_login_response_rejected(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(CaptureError, "HTML_ERROR_PAGE"):
                capture_test(td, result=downloaded(
                    raw=b"<html>Crop Progress Released November 16, 2026 Corn</html>",
                    ctype="text/html"))
            self.assertFalse((Path(td) / "fresh").exists())

    def test_wrong_release_or_stale_page_rejected(self):
        with TemporaryDirectory() as td:
            stale = NASS_TEXT.replace(b"November 16", b"November 9")
            with self.assertRaisesRegex(CaptureError, "WRONG_RELEASE_DATE"):
                capture_test(td, result=downloaded(raw=stale))

    def test_wrong_report_type_rejected(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(CaptureError, "NASS_WRONG_REPORT_TYPE"):
                capture_test(td, result=downloaded(raw=b"Released November 16, 2026 Corn"))

    def test_missing_corn_scope_is_rejected(self):
        with TemporaryDirectory() as td:
            raw = NASS_TEXT.replace(b"Corn", b"Soybeans")
            with self.assertRaisesRegex(CaptureError, "CORN_SCOPE_NOT_FOUND"):
                capture_test(td, result=downloaded(raw=raw))

    def test_wasde_wrong_date_rejected(self):
        with TemporaryDirectory() as td:
            raw = WASDE_TEXT.replace(b"December 10", b"November 10")
            with self.assertRaisesRegex(CaptureError, "WASDE_HEADER_DATE_MISMATCH"):
                capture_test(td, src="WASDE", result=downloaded("WASDE", raw=raw))

    def test_started_before_schedule_even_if_finished_after_blocked(self):
        with TemporaryDirectory() as td:
            res = downloaded(started="2026-11-16T20:59:59Z", ended="2026-11-16T21:01:00Z")
            with self.assertRaisesRegex(CaptureError, "CLOCK_OR_EARLY"):
                capture_test(td, result=res)

    def test_late_retrospective_download_not_called_immediate_release(self):
        with TemporaryDirectory() as td:
            res = downloaded(started="2026-11-20T21:00:35Z", ended="2026-11-20T21:00:40Z")
            with self.assertRaisesRegex(CaptureError, "OUTSIDE_ACTUAL_RELEASE_PILOT_WINDOW"):
                capture_test(td, result=res, now=dt("2026-11-20T21:00:36Z"))

    def test_same_digest_prior_cannot_rewrite_existing_observation(self):
        dig = hashlib.sha256(NASS_TEXT).hexdigest()
        prior = {"receipts": [{"source": "NASS", "report_id": "NASS-CROP-PROGRESS-2026-11-16",
                                "source_sha256": dig}]}
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(CaptureError, "EXACT_ALREADY_OBSERVED"):
                capture_test(td, prior=prior)
            self.assertFalse((Path(td) / "fresh").exists())

    def test_changed_digest_classified_candidate_not_proven_revision(self):
        p = {"receipts": [{"source": "NASS", "report_id": "NASS-CROP-PROGRESS-2026-11-16",
                           "source_sha256": "a" * 64}]}
        with TemporaryDirectory() as td:
            r = capture_test(td, prior=p)
            self.assertIn("POSSIBLE_REVISION", r["prior_source_comparison"]["status"])
            self.assertFalse(r["prior_source_comparison"]["revision_authenticated"])

    def test_existing_output_directory_not_overwritten(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "run"
            capture_test(td, output=root)
            with self.assertRaises(FileExistsError):
                capture_test(td, output=root)
            self.assertTrue(verify_saved(root)["verified"])

    def test_content_tampering_detected_by_replay(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "run"
            r = capture_test(td, output=root)
            (root / r["raw_path"]).write_bytes(b"altered")
            with self.assertRaisesRegex(CaptureError, "RAW_SHA256_REPLAY_MISMATCH"):
                verify_saved(root)

    def test_receipt_tampering_detected_by_replay(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "run"
            capture_test(td, output=root)
            (root / "receipt.json").write_text("{}")
            with self.assertRaisesRegex(CaptureError, "RECEIPT_SHA256_REPLAY_MISMATCH"):
                verify_saved(root)

    def test_lag_range_limits(self):
        with self.assertRaises(CaptureError):
            validate_spec("NASS", NASS_URL, NASS_DATE, NASS_BARRIER, -1,
                          dt("2026-11-16T21:00:40Z"))
        with self.assertRaises(CaptureError):
            validate_spec("NASS", NASS_URL, NASS_DATE, NASS_BARRIER, 3601,
                          dt("2026-11-16T21:00:40Z"))

    def test_first_observed_not_first_globally(self):
        with TemporaryDirectory() as td:
            r = capture_test(td)
            self.assertFalse(r["source_originality_certified"])
            self.assertFalse(r["cross_run_global_dedup_verified"])
            self.assertEqual(r["published_at_utc"], "")
            self.assertEqual(r["available_at_utc"], "")


if __name__ == "__main__":
    unittest.main()

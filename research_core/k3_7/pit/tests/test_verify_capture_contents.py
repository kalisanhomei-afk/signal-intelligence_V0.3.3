"""Capture payload matching must not claim timestamp certification on index alone."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_core.k3_7.pit.pilot6.verify_capture_contents import (
    case_entries, inspect, match_target_text, normalize_html, run, verify_warc_identity, warc_content
)


class ArchiveContentTests(unittest.TestCase):
    def test_2016_wasde_needs_corn_context(self):
        text = normalize_html(b"<p>USDA lowered new crop corn ending stocks to 2.008 billion bushels.</p>")
        self.assertTrue(match_target_text(text, "WASDE", 2016))
        self.assertFalse(match_target_text("The company reached 2.008 billion users", "WASDE", 2016))

    def test_2022_nass_requires_crop_with_poor_good_classification(self):
        t = normalize_html(b"USDA corn is 73% in good to excellent condition this week.")
        self.assertTrue(match_target_text(t, "NASS", 2022))
        self.assertFalse(match_target_text("Soybeans were 73% harvested", "NASS", 2022))

    def test_gzip_warc_member_supported(self):
        compressed = gzip.compress(b"WARC/1.0\r\nWARC-Type: response\r\n\r\n"
                                   b"<html>USDA corn 73% good to excellent</html>")
        plain = warc_content(compressed)
        self.assertIn(b"WARC/1.0", plain)
        self.assertTrue(match_target_text(normalize_html(plain), "NASS", 2022))

    def test_archive_index_duplicates_not_counted_as_independent_captures(self):
        case = {"queries": [
            {"provider": "IA_CDX", "capture_entries_in_180day_window": [
                {"capture_at_utc": "2016-06-11T13:03:24Z", "archived_url": "https://a", "capture_digest": "x"}]},
            {"provider": "IA_AVAILABILITY", "capture_entries_in_180day_window": [
                {"capture_at_utc": "2016-06-11T13:03:24Z", "archived_url": "https://a", "capture_digest": "x"}]}]}
        self.assertEqual(len(list(case_entries(case))), 1)

    def test_commoncrawl_warc_target_and_capture_date_must_match(self):
        url = "https://www.dtnpf.com/agriculture/web/ag/news/article/2022/06/10/x"
        body = (b"WARC/1.0\r\nWARC-Type: response\r\n"
                b"WARC-Date: 2022-07-03T10:56:16Z\r\n"
                b"WARC-Target-URI: " + url.encode() + b"\r\n\r\n"
                b"HTTP/1.1 200 OK\r\n\r\nCorn ending stocks 1.485 billion bushels")
        self.assertTrue(verify_warc_identity(body, url, "2022-07-03T10:56:16Z"))
        self.assertFalse(verify_warc_identity(body, url, "2022-07-04T10:56:16Z"))
        self.assertFalse(verify_warc_identity(body, url + "/other", "2022-07-03T10:56:16Z"))

    def test_wayback_memento_header_time_disagreement_is_blocked(self):
        case = {"kind": "WASDE", "year": 2016,
                "target_media_url": "https://www.dtnpf.com/test"}
        cap = {"capture_at_utc": "2016-06-11T13:03:24Z", "capture_digest": "a"}
        response = {"status": "FETCHED", "raw": b"USDA corn ending stocks 2.008 billion bushels",
                    "http_status": 200,
                    "resolved_url": "https://web.archive.org/web/20160611130324id_/https://www.dtnpf.com/test",
                    "memento_datetime_header": "Mon, 13 Jun 2016 13:03:24 GMT",
                    "capture_sha256": "example"}
        with patch("research_core.k3_7.pit.pilot6.verify_capture_contents.safe_open",
                   return_value=response):
            r = inspect(case, "WAYBACK", cap)
        self.assertEqual(r["status"], "MEMENTO_HEADER_TIMESTAMP_MISMATCH")
        self.assertFalse(r["value_matched"])

    def test_replay_redirect_to_another_capture_time_is_blocked(self):
        case = {"kind": "WASDE", "year": 2016,
                "target_media_url": "https://www.dtnpf.com/test"}
        cap = {"capture_at_utc": "2016-06-11T13:03:24Z", "capture_digest": "a"}
        response = {"status": "FETCHED", "raw": b"USDA corn ending stocks 2.008 billion",
                    "http_status": 200,
                    "resolved_url": "https://web.archive.org/web/20201101000000id_/https://www.dtnpf.com/test",
                    "capture_sha256": "example"}
        with patch("research_core.k3_7.pit.pilot6.verify_capture_contents.safe_open",
                   return_value=response):
            r = inspect(case, "WAYBACK", cap)
        self.assertEqual(r["status"], "ARCHIVED_CAPTURE_REDIRECT_TIME_MISMATCH")
        self.assertFalse(r["value_matched"])

    def test_exact_replay_timestamp_with_value_matches_only_as_candidate(self):
        case = {"kind": "WASDE", "year": 2016,
                "target_media_url": "https://www.dtnpf.com/test"}
        cap = {"capture_at_utc": "2016-06-11T13:03:24Z", "capture_digest": "a"}
        response = {"status": "FETCHED", "raw": b"USDA corn ending stocks 2.008 billion bushels",
                    "http_status": 200,
                    "resolved_url": "https://web.archive.org/web/20160611130324id_/https://www.dtnpf.com/test",
                    "memento_datetime_header": "Sat, 11 Jun 2016 13:03:24 GMT",
                    "capture_sha256": "example"}
        with patch("research_core.k3_7.pit.pilot6.verify_capture_contents.safe_open",
                   return_value=response):
            r = inspect(case, "WAYBACK", cap)
        self.assertTrue(r["value_matched"])
        self.assertFalse(r["pit_certified"])

    def test_unreachable_archive_is_never_pit(self):
        data = {"cases": [{"kind": "WASDE", "year": 2016, "nominal_release_date": "2016-06-10",
                           "expected_value": "2008", "target_media_url": "https://example.com",
                           "queries": [{"provider": "IA_CDX", "capture_entries_in_180day_window": [
                               {"capture_at_utc": "2016-06-11T13:03:24Z", "archived_url": "https://example.com"}]}]}]}
        with tempfile.TemporaryDirectory() as td:
            inp, out = Path(td) / "source.json", Path(td) / "report"
            inp.write_text(json.dumps(data))
            with patch("research_core.k3_7.pit.pilot6.verify_capture_contents.safe_open",
                       return_value={"status": "ARCHIVE_HTTP_ERROR", "http_status": 403}):
                res = run(inp, out)
            self.assertEqual(res["metric_level_historical_public_by_candidates"], 0)
            self.assertEqual(res["pit_certified"], 0)
            self.assertEqual(res["cases"][0]["matched_capture_count"], 0)


if __name__ == "__main__":
    unittest.main()

"""Capture payload matching must not claim timestamp certification on index alone."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_core.k3_7.pit.pilot6.verify_capture_contents import (
    case_entries, match_target_text, normalize_html, run, warc_content
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

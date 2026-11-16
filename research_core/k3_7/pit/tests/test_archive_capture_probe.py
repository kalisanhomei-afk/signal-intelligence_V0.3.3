"""Offline fail-closed historical archival index probe tests."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from research_core.k3_7.pit.pilot6.archive_capture_probe import (
    in_window, parse_availability, parse_commoncrawl, parse_wayback_cdx, run
)


class IndependentCaptureMetadataTests(unittest.TestCase):
    def setUp(self):
        self.start = date(2016, 6, 10)
        self.end = date(2016, 12, 7)

    def test_old_exact_cdx_capture_index_is_candidate_not_certified_content(self):
        response = {"status": "HTTP_OK", "body": json.dumps([
            ["timestamp", "original", "digest", "statuscode"],
            ["20160611094600", "https://example.com/story", "BASE32_DIGEST", "200"],
            ["20200611094600", "https://example.com/story", "NEW_DIGEST", "200"]])}
        x = parse_wayback_cdx(response, self.start, self.end)
        self.assertEqual(x["state"], "CANDIDATE_INDEX_HITS")
        self.assertEqual(x["total_hits_in_window"], 1)
        self.assertEqual(x["capture_entries_in_180day_window"][0]["capture_at_utc"],
                         "2016-06-11T09:46:00Z")

    def test_wayback_closest_after_historical_window_is_rejected(self):
        resp = {"status": "HTTP_OK", "body": json.dumps({"archived_snapshots": {
            "closest": {"timestamp": "20240303000000", "url": "https://web.archive.org/web/a"}}})}
        x = parse_availability(resp, self.start, self.end)
        self.assertEqual(x["state"], "CLOSEST_CAPTURE_OUTSIDE_WINDOW")
        self.assertEqual(x["total_hits_in_window"], 0)

    def test_commoncrawl_404_is_absent_in_one_index_not_all_sources(self):
        x = parse_commoncrawl({"status": "HTTP_ERROR", "http_status": 404}, self.start, self.end)
        self.assertEqual(x["state"], "INDEX_QUERY_NO_MATCH")
        self.assertEqual(x["total_hits_in_window"], 0)

    def test_commoncrawl_403_is_unavailable_not_nonexistent(self):
        x = parse_commoncrawl({"status": "HTTP_ERROR", "http_status": 403}, self.start, self.end)
        self.assertEqual(x["state"], "INDEX_UNAVAILABLE")

    def test_rejects_invalid_capture_timestamp(self):
        self.assertFalse(in_window("20160610", self.start, self.end))
        self.assertFalse(in_window("20230611120000", self.start, self.end))

    def test_no_internet_access_cannot_promote_pit(self):
        cases = []
        for year in (2016, 2020, 2022):
            for kind in ("WASDE", "NASS"):
                cases.append({"kind": kind, "year": year, "release_date": f"{year}-06-10",
                              "official_numeric_value": "2008",
                              "content_evidence_url": "https://example.com/record",
                              "timestamp_quality": "UNKNOWN", "pit_certified": False,
                              "available_at_utc": ""})
        with tempfile.TemporaryDirectory() as t:
            catalog = Path(t) / "cases.json"
            catalog.write_text(json.dumps({"schema": "test-only", "records": cases}))
            out = Path(t) / "out"
            def forbidden(_):
                return {"status": "HTTP_ERROR", "http_status": 403, "request_url": "mock"}
            result = run(catalog, out, requester=forbidden)
            self.assertEqual(result["pit_certified_rows"], 0)
            self.assertEqual(result["total_candidate_index_hits"], 0)
            self.assertTrue(all(r["timestamp_quality"] == "UNKNOWN" for r in result["cases"]))
            self.assertTrue((out / "historical_capture_index_probe.json").is_file())


if __name__ == "__main__":
    unittest.main()

"""Deterministic synthetic tests: no sockets, API keys, or live-source claims."""
import csv
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request

from research_core.k3_7.nass import pipeline as m

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
RAW = (FIXTURES / "report_synthetic.txt").read_bytes()
ARCHIVE_RAW = (FIXTURES / "archive_synthetic.html").read_bytes()
# Test-only invented URLs NEVER appear in production data/out.
URL = "https://esmis.nal.usda.gov/sites/default/release-files/fixture-only/prog2316.txt"
RETRIEVED = "2026-11-13T07:00:00.123456Z"


def response(raw, url=URL, retrieved=RETRIEVED):
    return dict(raw=raw, source_url=url, retrieved_at_utc=retrieved,
                http_status=200, content_type="text/plain", last_modified="Mon, 06 Jun 2016 20:00:00 GMT")


def add_report(bundle, raw=RAW, url=URL, retrieved=RETRIEVED):
    # The banner is removed only inside TemporaryDirectory integration tests.
    body = raw.split(b"\n", 1)[1] if raw.startswith(b"SYNTHETIC OFFLINE FIXTURE") else raw
    return m.acquire(bundle, url, "report", lambda _: response(body, url, retrieved),
                     expected_report_date="2016-06-06")


class ParserTests(unittest.TestCase):
    def test_current_state_values_and_derived_good_excellent(self):
        parsed = m.parse_report(RAW, "2016-06-06")
        self.assertEqual(parsed["report_date"], "2016-06-06")
        self.assertEqual(parsed["week_ending"], "2016-06-05")
        self.assertEqual([r["state"] for r in parsed["rows"]], ["Colorado", "North Carolina"])
        self.assertEqual(parsed["rows"][0]["good_excellent_pct"], 75)
        self.assertEqual(parsed["rows"][1]["good_excellent_pct"], 60)
        self.assertEqual(parsed["declared_state_count"], 2)
        self.assertEqual(len(parsed["missing_reference_states"]), 16)

    def test_all_three_pilot_year_headers_and_sunday_weeks(self):
        for year, release, week in ((2016, "June 6, 2016", "June 5, 2016"),
                                    (2020, "June 8, 2020", "June 7, 2020"),
                                    (2022, "June 6, 2022", "June 5, 2022")):
            raw = RAW.replace(b"June 6, 2016", release.encode()).replace(b"June 5, 2016", week.encode())
            with self.subTest(year=year):
                parsed = m.parse_report(raw)
                self.assertEqual(parsed["report_date"][:4], str(year))
                self.assertEqual(parsed["week_ending"][:4], str(year))
                self.assertEqual(len(parsed["rows"]), 2)

    def test_no_aggregate_previous_week_year_or_soybean_rows(self):
        parsed = m.parse_report(RAW)
        self.assertEqual(len(parsed["rows"]), 2)
        self.assertEqual(parsed["rows"][0]["very_poor_pct"], 1)

    def test_simple_single_line_column_header(self):
        raw = RAW.replace(b"               : Very :      :      :      :\nState          : poor : Poor : Fair : Good : Excellent",
                          b"State : Very poor : Poor : Fair : Good : Excellent")
        self.assertEqual(len(m.parse_report(raw)["rows"]), 2)

    def test_no_corn_condition_is_explicit_unreported_in_retrieved_report(self):
        raw = RAW[:RAW.index(b"Corn Condition")]
        parsed = m.parse_report(raw)
        self.assertEqual(parsed["status"], "NOT_REPORTED_IN_RETRIEVED_REPORT")
        self.assertEqual(parsed["rows"], [])
        self.assertEqual(parsed["week_ending"], "")

    def test_malformed_heading_is_parse_error(self):
        with self.assertRaisesRegex(m.SourceError, "UNSUPPORTED_CORN_CONDITION_HEADING"):
            m.parse_report(RAW.replace(b"Corn Condition - Selected", b"Corn Condition / Selected"))

    def test_mismatch_release_date(self):
        with self.assertRaisesRegex(m.SourceError, "RELEASE_DATE_MISMATCH"):
            m.parse_report(RAW, "2016-06-07")

    def test_wrong_crop_report_or_pilot_year_is_rejected(self):
        for raw in (b"<html>Service unavailable</html>", RAW.replace(b"2016", b"2023"),
                    RAW.replace(b"National Agricultural Statistics Service", b"Unofficial mirror")):
            with self.subTest(raw=raw[:50]), self.assertRaises(m.SourceError):
                m.parse_report(raw)

    def test_invalid_week_is_rejected(self):
        for old, new in ((b"June 5, 2016", b"June 4, 2016"),
                         (b"June 5, 2016", b"June 12, 2016"),
                         (b"June 6, 2016", b"June 10, 2016")):
            with self.subTest(new=new), self.assertRaisesRegex(m.SourceError, "IMPLAUSIBLE_WEEK"):
                m.parse_report(RAW.replace(old, new))

    def test_multiple_current_tables_rejected(self):
        with self.assertRaisesRegex(m.SourceError, "MULTIPLE_CONTEMPORARY"):
            m.parse_report(RAW + RAW)

    def test_unsupported_column_order_rejected(self):
        with self.assertRaisesRegex(m.SourceError, "COLUMN_ORDER"):
            m.parse_report(RAW.replace(b"Fair : Good", b"Good : Fair"))

    def test_missing_rating_is_not_zero_filled(self):
        for bad in (b"1 4 (NA) 50 25", b"1 4 -- 50 25", b"1 4 50 25", b"1 4 -1 50 46"):
            parsed = m.parse_report(RAW.replace(b"1 4 20 50 25", bad))
            self.assertEqual(len(parsed["rows"]), 1)
            self.assertEqual(parsed["issues"][0]["code"], "MISSING_OR_NONNUMERIC_RATING")
            self.assertEqual(parsed["issues"][0]["state"], "Colorado")

    def test_percentage_range_sum_and_tolerance(self):
        for bad, code in ((b"101 0 0 0 0", "PERCENTAGE_OUT_OF_RANGE"),
                          (b"1 4 20 50 30", "PERCENTAGE_SUM_OUT_OF_TOLERANCE")):
            parsed = m.parse_report(RAW.replace(b"1 4 20 50 25", bad))
            self.assertEqual(len(parsed["rows"]), 1)
            self.assertEqual(parsed["issues"][0]["code"], code)
        for total, last in ((99, b"24"), (101, b"26")):
            row = m.parse_report(RAW.replace(b"1 4 20 50 25", b"1 4 20 50 " + last))["rows"][0]
            self.assertEqual(row["percentage_sum"], total)
            self.assertEqual(row["percentage_quality"], "ROUNDING_TOLERANCE")

    def test_duplicate_state_quarantines_both_rows(self):
        parsed = m.parse_report(RAW.replace(b"North Carolina :", b"Colorado ......:"))
        self.assertEqual(parsed["rows"], [])
        self.assertIn("DUPLICATE_STATE_ROW", [i["code"] for i in parsed["issues"]])

    def test_unknown_state_is_audited(self):
        parsed = m.parse_report(RAW.replace(b"North Carolina :", b"Not A State ..:"))
        self.assertIn("UNRECOGNIZED_TABLE_ROW", [i["code"] for i in parsed["issues"]])
        self.assertIn("North Carolina", parsed["missing_reference_states"])

    def test_unknown_first_state_row_is_not_swallowed_by_header(self):
        parsed = m.parse_report(RAW.replace(b"Colorado ......:", b"Unknown State .:", 1))
        self.assertIn("UNRECOGNIZED_TABLE_ROW", [i["code"] for i in parsed["issues"]])

    def test_missing_rating_and_absent_state_have_distinct_gap_statuses(self):
        parsed = m.parse_report(RAW.replace(b"1 4 20 50 25", b"1 4 -- 50 25"))
        gaps = {g["state"]: g["status"] for g in parsed["state_rating_gaps"]}
        self.assertEqual(gaps["Colorado"], "RATING_REJECTED")
        self.assertEqual(gaps["Iowa"], "NOT_LISTED_IN_RETRIEVED_TABLE")
        self.assertNotIn("North Carolina", gaps)

    def test_missing_or_mismatched_national_row_is_audited(self):
        for raw in (RAW.replace(b"2 States ......:", b"18 States .....:"),
                    RAW.replace(b"2 States ......: 2 6 25 48 19\n", b"")):
            parsed = m.parse_report(raw)
            self.assertEqual(len(parsed["rows"]), 2)
            self.assertEqual(parsed["status"], "PARTIAL_PARSE")

    def test_revised_marker_retained(self):
        self.assertTrue(m.parse_report(RAW + b"\nRevised edition\n")["revision_marker"])


class DiscoveryAndNetworkTests(unittest.TestCase):
    def test_observed_links_keep_same_date_distinct_editions(self):
        links, next_url, issues = m.archive_links(ARCHIVE_RAW, m.ARCHIVE)
        self.assertEqual(len(links), 2)
        self.assertEqual(next_url, m.ARCHIVE + "?page=1")
        self.assertEqual(issues, [])
        self.assertEqual(links[0]["report_date"], "2016-06-06")

    def test_undated_link_never_inferred_from_filename(self):
        links, next_url, issues = m.archive_links(b'<a href="/prog2316.txt">TXT</a>', m.ARCHIVE)
        self.assertEqual(links, [])
        self.assertIsNone(next_url)
        self.assertEqual(issues[0]["code"], "UNDATED_TXT_LINK")

    def test_no_next_page_is_invented(self):
        links, next_url, _ = m.archive_links(ARCHIVE_RAW.replace(b'rel="next"', b'rel="last"').replace(b'Next \xe2\x80\xba', b'Last'), m.ARCHIVE)
        self.assertEqual(len(links), 2)
        self.assertIsNone(next_url)

    def test_ambiguous_next_pages_rejected(self):
        with self.assertRaisesRegex(m.SourceError, "AMBIGUOUS"):
            m.archive_links(ARCHIVE_RAW + b'<a rel="next" href="?page=2">Next</a>', m.ARCHIVE)

    def test_unapproved_urls_and_redirects_rejected(self):
        for url in ("http://esmis.nal.usda.gov/a", "https://esmis.nal.usda.gov.evil.invalid/a",
                    "https://user:secret@esmis.nal.usda.gov/a", "https://esmis.nal.usda.gov:8443/a"):
            with self.subTest(url=url), self.assertRaises(m.SourceError):
                m.checked_url(url)
        with self.assertRaises(m.SourceError):
            m.OfficialRedirects().redirect_request(Request(m.ARCHIVE), None, 302, "Found", {}, "https://example.invalid/a")

    def test_failed_request_records_actual_attempt_without_hash_or_retrieval(self):
        with tempfile.TemporaryDirectory() as td:
            def fail(_):
                raise URLError("Tunnel connection failed: 403 Forbidden")
            receipt = m.acquire(Path(td), m.ARCHIVE, "archive", fail)
            self.assertEqual(receipt["status"], "SOURCE_UNAVAILABLE")
            self.assertNotIn("source_sha256", receipt)
            self.assertNotIn("retrieved_at_utc", receipt)
            self.assertNotIn("source_url", receipt)
            self.assertEqual(m.read_ledger(Path(td)), [receipt])

    def test_download_records_body_completion_time_and_raw_bytes(self):
        class FakeResponse(BytesIO):
            status = 200
            headers = {"Content-Type": "text/plain"}
            def geturl(self):
                return URL
        class FakeOpener:
            def open(self, req, timeout):
                return FakeResponse(b"raw\r\nbytes\xff")
        with patch.object(m, "build_opener", return_value=FakeOpener()), patch.object(m, "utc_now", return_value=RETRIEVED):
            result = m.download(URL)
        self.assertEqual(result["raw"], b"raw\r\nbytes\xff")
        self.assertEqual(result["retrieved_at_utc"], RETRIEVED)

    def test_oversize_and_empty_response_rejected(self):
        class FakeResponse(BytesIO):
            status = 200
            headers = {}
            def geturl(self):
                return URL
        for raw, limit in ((b"1234", 3), (b"", 3)):
            opener = unittest.mock.Mock()
            opener.open.return_value = FakeResponse(raw)
            with patch.object(m, "build_opener", return_value=opener), self.assertRaises(m.SourceError):
                m.download(URL, max_bytes=limit)

    def test_discovery_covers_pages_without_date_order_assumption(self):
        with tempfile.TemporaryDirectory() as td:
            calls = []
            page2 = b'<a href="/sites/default/release-files/test/prog2320.txt">Jun 08 2020 - txt</a>'
            def fetch(url):
                calls.append(url)
                body = (b"Crop Progress released Monday at 4:00 p.m. Eastern time." if url == m.POLICY
                        else ARCHIVE_RAW if url == m.ARCHIVE else page2 if "?page=1" in url else RAW)
                return response(body, url)
            result = m.fetch_sources(Path(td), 5, fetch)
            self.assertEqual(result["status"], "OBSERVED_PAGINATION_END")
            self.assertEqual(result["reports_discovered"], 3)
            self.assertEqual(len(calls), 6)
            self.assertEqual(len([e for e in m.read_ledger(Path(td)) if e["role"] == "report"]), 3)

    def test_discovery_cycle_page_limit_no_links_and_failure_distinct(self):
        variants = [(ARCHIVE_RAW, 1, "PAGE_LIMIT_REACHED"),
                    (b"<html>layout changed</html>", 3, "NO_RECOGNIZED_LINKS"),
                    (b'<a rel="next" href="/publication/crop-progress">Next</a>', 3, "PAGINATION_CYCLE")]
        for raw, limit, status in variants:
            with tempfile.TemporaryDirectory() as td:
                r = m.fetch_sources(Path(td), limit, lambda url: response(raw, url))
                self.assertEqual(r["status"], status)
        with tempfile.TemporaryDirectory() as td:
            def fail(_):
                raise URLError("blocked")
            r = m.fetch_sources(Path(td), 3, fail)
            self.assertEqual(r["status"], "SOURCE_UNAVAILABLE")
            self.assertEqual(r["reports_discovered"], 0)


class ReplayAndEvidenceTests(unittest.TestCase):
    def test_unknown_fields_stay_blank_even_with_http_last_modified(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            add_report(root)
            report = m.build(root, root / "out")
            with (root / "out/nass_state_weekly.csv").open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            for row in rows:
                self.assertEqual(row["timestamp_quality"], "UNKNOWN")
                self.assertEqual(row["retrieved_at_utc"], RETRIEVED)
                self.assertEqual(row["marketing_year"], "2016/17")
                self.assertEqual(row["iso_week"], "22")
                for key in ("published_at_utc", "available_at_utc", "evidence_url", "scheduled_release_at_utc"):
                    self.assertEqual(row[key], "")
            self.assertEqual(report["verified_public_timestamp_rows"], 0)

    def test_observed_schedule_is_only_proxy_and_holiday_remains_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = b"Crop Progress is released Monday at 4:00 p.m. Eastern time."
            m.acquire(root, m.POLICY, "schedule", lambda url: response(raw, url))
            schedule = m.schedule_evidence(root, m.read_ledger(root))
            self.assertIsNotNone(schedule)
            f = m.time_fields("2016-06-06", schedule)
            self.assertEqual(f["timestamp_quality"], "OFFICIAL_SCHEDULE_PROXY")
            self.assertEqual(f["scheduled_release_at_utc"], "2016-06-06T20:00:00Z")
            self.assertEqual(m.time_fields("2016-01-04", schedule)["scheduled_release_at_utc"], "2016-01-04T21:00:00Z")
            self.assertEqual(f["published_at_utc"], "")
            self.assertEqual(f["available_at_utc"], "")
            self.assertEqual(f["evidence_url"], "")
            self.assertEqual(m.time_fields("2016-05-31", schedule)["timestamp_quality"], "UNKNOWN")

    def test_unread_unrelated_or_tampered_schedule_not_used(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            receipt = m.acquire(root, m.POLICY, "schedule", lambda url: response(b"4 p.m. unrelated text", url))
            self.assertIsNone(m.schedule_evidence(root, [receipt]))
            (root / receipt["raw_path"]).write_bytes(b"Crop Progress Monday at 4 p.m. ET")
            self.assertIsNone(m.schedule_evidence(root, [receipt]))

    def test_unrelated_schedule_paragraphs_are_not_combined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = b"<p>Crop Progress released on Monday.</p><p>Other report: 4 p.m. ET</p>"
            receipt = m.acquire(root, m.POLICY, "schedule", lambda url: response(raw, url))
            self.assertIsNone(m.schedule_evidence(root, [receipt]))

    def test_repeat_fetch_identical_edition_uses_first_real_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = add_report(root)
            add_report(root, retrieved="2026-11-14T07:00:00Z")
            report = m.build(root, root / "out")
            self.assertEqual(report["observation_rows"], 2)
            self.assertEqual(len(m.read_ledger(root)), 2)
            self.assertEqual(report["source_parse_audit"][0]["retrieved_at_utc"], first["retrieved_at_utc"])

    def test_changed_source_bytes_preserve_both_versions_and_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            add_report(root)
            add_report(root, RAW.replace(b"1 4 20 50 25", b"1 4 20 49 26") + b"\nRevised edition\n")
            report = m.build(root, root / "out")
            self.assertEqual(report["observation_rows"], 4)
            self.assertIn("VINTAGE_VALUE_CONFLICT", [i["code"] for i in report["issues"]])
            self.assertEqual(report["seasonal_coverage"][0]["distinct_state_weeks"], 2)
            self.assertEqual(len(list((root / "raw").glob("*.bin"))), 2)

    def test_banners_cannot_become_production_observations(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m.acquire(root, URL, "report", lambda _: response(RAW))
            report = m.build(root, root / "out")
            self.assertEqual(report["observation_rows"], 0)
            self.assertIn("FIXTURE_IS_NOT", report["issues"][0]["error"])

    def test_corrupt_or_absent_raw_cannot_become_rows(self):
        for mode in ("tamper", "missing"):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                receipt = add_report(root)
                raw_path = root / receipt["raw_path"]
                raw_path.write_bytes(b"changed") if mode == "tamper" else raw_path.unlink()
                report = m.build(root, root / "out")
                self.assertEqual(report["observation_rows"], 0)
                self.assertEqual(report["source_parse_audit"][0]["parse_status"], "PARSE_ERROR")

    def test_manifest_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            receipt = add_report(root)
            receipt["raw_path"] = "../../outside.txt"
            with self.assertRaisesRegex(m.SourceError, "INVALID_RAW_PATH"):
                m.checked_raw(root, receipt)

    def test_build_has_no_clock_or_network_and_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            add_report(root)
            with patch.object(m, "utc_now", side_effect=AssertionError("offline clock access")), patch.object(m, "download", side_effect=AssertionError("offline network access")):
                m.build(root, root / "out1")
                m.build(root, root / "out2")
            for path in (root / "out1").iterdir():
                self.assertEqual(path.read_bytes(), (root / "out2" / path.name).read_bytes())

    def test_missing_years_states_and_unknown_grid_not_fabricated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = m.build(root, root / "out")
            self.assertEqual(report["observation_rows"], 0)
            self.assertEqual([r["year"] for r in report["seasonal_coverage"]], list(m.YEARS))
            for year in report["seasonal_coverage"]:
                self.assertEqual(len(year["reference_states_without_accepted_rows"]), 18)
                self.assertEqual(len(year["other_states_outside_reference_scope"]), 32)
                self.assertGreater(len(year["audit_grid_weeks_without_accepted_conditions"]), 30)
            self.assertEqual(len((root / "out/nass_state_weekly.csv").read_text().splitlines()), 1)

    def test_live_download_failure_separate_from_offline_replay(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def fail(_):
                raise URLError("proxy 403")
            m.fetch_sources(root, 1, fail)
            report = m.build(root, root / "out")
            self.assertEqual(report["network_attempt_counts"], {"SOURCE_UNAVAILABLE": 2})
            self.assertEqual(report["source_parse_audit"], [])
            self.assertEqual(report["observation_rows"], 0)

    def test_checked_in_snapshot_replays_without_network(self):
        module_root = FIXTURES.parent
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            with patch.object(m, "build_opener", side_effect=AssertionError("No network during replay")):
                m.build(module_root / "data", output)
            for name in ("nass_state_weekly.csv", "quality_report.json", "quality_report.md"):
                self.assertEqual((output / name).read_bytes(), (module_root / "out" / name).read_bytes())

    def test_committed_observations_have_contract_fields_and_no_fixture_urls(self):
        module_root = FIXTURES.parent
        with (module_root / "out/nass_state_weekly.csv").open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, m.COLUMNS)
            rows = list(reader)
        report = json.loads((module_root / "out/quality_report.json").read_text())
        self.assertEqual(report["observation_rows"], len(rows))
        for row in rows:
            self.assertNotIn("fixture", row["source_url"])
            self.assertRegex(row["source_sha256"], r"^[a-f0-9]{64}$")
            self.assertIn(row["timestamp_quality"], ("UNKNOWN", "OFFICIAL_SCHEDULE_PROXY"))
            self.assertEqual(row["published_at_utc"], "")
            self.assertEqual(row["available_at_utc"], "")
            self.assertLessEqual(abs(sum(int(row[k]) for k in m.RATINGS) - 100), 1)


if __name__ == "__main__":
    unittest.main()

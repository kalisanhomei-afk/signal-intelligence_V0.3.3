"""K3.8 source listing resolution: exact date and exact official URL."""
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
from unittest.mock import patch
import unittest
from research_core.k3_8.capture import CaptureError, main, validate_spec
from research_core.k3_8.discover import extract_direct_txt


class OfficialCatalogParserTests(unittest.TestCase):
    def test_date_and_txt_filter_nass(self):
        html = """
        <a href="/sites/default/release-files/abc/prog4526.txt"
           title="Nov 09 2026 - txt">download</a>
        <a href="/sites/default/release-files/def/prog4626.txt"
           title="Nov 16 2026 - txt">download</a>
        <a href="/sites/default/release-files/def/prog4626.pdf"
           title="Nov 16 2026 - pdf">download</a>
        """
        x=extract_direct_txt(html,"NASS",date(2026,11,16))
        self.assertEqual(x,"https://esmis.nal.usda.gov/sites/default/release-files/def/prog4626.txt")

    def test_duplicate_link_same_url_not_ambiguous(self):
        html = ('<a href="/sites/default/release-files/def/prog4626.txt">Nov 16 2026 - txt</a>'
                '<a href="/sites/default/release-files/def/prog4626.txt">Nov 16 2026 - txt</a>')
        self.assertTrue(extract_direct_txt(html,"NASS",date(2026,11,16)).endswith("/prog4626.txt"))

    def test_missing_not_replaced_by_earlier_release(self):
        with self.assertRaisesRegex(CaptureError,"EXACT_RELEASE_DATE_OFFICIAL_TXT_NOT_LISTED"):
            extract_direct_txt('<a href="/a/prog4526.txt">Nov 09 2026 - txt</a>',
                               "NASS",date(2026,11,16))

    def test_ambiguous_distinct_official_txt_rejected(self):
        a=('<a href="/a/prog4626.txt">Nov 16 2026 - txt</a>'
           '<a href="/b/prog4626.txt">Nov 16 2026 - txt</a>')
        with self.assertRaisesRegex(CaptureError,"AMBIGUOUS_MULTIPLE_OFFICIAL_TXT"):
            extract_direct_txt(a,"NASS",date(2026,11,16))

    def test_wrong_domain_or_html_file_rejected(self):
        html=('<a href="https://evil.example/a.txt">Nov 16 2026 - txt</a>'
              '<a href="/sites/default/release-files/aaa/prog4626.pdf">Nov 16 2026 - txt</a>')
        with self.assertRaisesRegex(CaptureError,"EXACT_RELEASE_DATE_OFFICIAL_TXT_NOT_LISTED"):
            extract_direct_txt(html,"NASS",date(2026,11,16))

    def test_exact_date_wasde(self):
        html='<a href="/sites/default/release-files/wasde1226.txt">Dec 10 2026 - txt</a>'
        self.assertTrue(extract_direct_txt(html,"WASDE",date(2026,12,10)).endswith("wasde1226.txt"))

    def test_auto_refuses_to_query_catalog_before_release(self):
        with TemporaryDirectory() as tmp:
            params = ["--source", "NASS", "--url", "AUTO",
                      "--release-date", "2099-11-16",
                      "--not-before-utc", "2099-11-16T21:00:00Z",
                      "--output", str(Path(tmp) / "out")]
            with patch("research_core.k3_8.discover.discover_exact_txt") as resolver:
                with redirect_stdout(StringIO()):
                    status = main(params)
            self.assertEqual(status, 2)
            resolver.assert_not_called()
            self.assertFalse((Path(tmp) / "out").exists())

    def test_auto_uses_exact_catalog_url_and_marks_resolution_method(self):
        params = ["--source", "NASS", "--url", "AUTO",
                  "--release-date", "2026-11-16",
                  "--not-before-utc", "2026-11-16T21:00:00Z",
                  "--output", "not_written_mock_only"]
        fake = {"status": "ONE_SOURCE_OBSERVED_NO_BACKTEST_CERTIFICATION",
                "source_sha256": "a" * 64,
                "source_url": "https://esmis.nal.usda.gov/sites/default/release-files/demo/prog4626.txt",
                "source_url_resolution_method": "OFFICIAL_ESMIS_EXACT_DATE_LINK",
                "report_id": "NASS-CROP-PROGRESS-2026-11-16",
                "response_finished_at_utc": "2026-11-16T21:00:40Z",
                "safe_feature_not_before_utc": "2026-11-16T21:02:40Z"}
        with patch("research_core.k3_8.capture.now_utc",
                   return_value=datetime(2026,11,16,21,0,45,tzinfo=timezone.utc)):
            with patch("research_core.k3_8.discover.discover_exact_txt",return_value=fake["source_url"]) as discover:
                with patch("research_core.k3_8.capture.capture",return_value=fake) as observe:
                    with redirect_stdout(StringIO()):
                        status=main(params)
        self.assertEqual(status, 0)
        discover.assert_called_once_with("NASS",date(2026,11,16))
        self.assertEqual(observe.call_args.args[1],fake["source_url"])
        self.assertEqual(observe.call_args.kwargs["source_resolution_method"],
                         "OFFICIAL_ESMIS_EXACT_DATE_LINK")


if __name__ == "__main__":
    unittest.main()

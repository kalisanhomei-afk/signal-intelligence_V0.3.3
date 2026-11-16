"""K3.8 source listing resolution: exact date and exact official URL."""
from datetime import date
import unittest
from research_core.k3_8.capture import CaptureError
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

if __name__ == "__main__":
    unittest.main()

"""Offline regression: legacy ESMIS CropProg-YYYY report filenames.

Synthetic HTML. This is discovery-format coverage, NOT proof of 2016 source
downloads or published-at timestamp availability.
"""
import unittest
from research_core.k3_7.nass import pipeline


class LegacyLinkDiscoveryTests(unittest.TestCase):
    def test_2016_crop_prog_link_with_observed_date_metadata(self):
        html = b'''
        <a href="/sites/default/release-files/8336h188j/CropProg-05-02-2016.txt"
           title="Crop Progress - May 02 2016 - txt">Download TXT</a>
        <a href="?page=111" rel="next">Next</a>
        '''
        links, next_url, issues = pipeline.archive_links(html, pipeline.ARCHIVE + "?page=110")
        self.assertEqual(links, [
            {"report_date": "2016-05-02",
             "url": "https://esmis.nal.usda.gov/sites/default/release-files/8336h188j/CropProg-05-02-2016.txt"}
        ])
        self.assertEqual(next_url, pipeline.ARCHIVE + "?page=111")
        self.assertEqual(issues, [])

    def test_legacy_filename_alone_is_not_proof_of_publication_date(self):
        html = b'<a href="/sites/default/release-files/legacy/CropProg-05-02-2016.txt">TXT</a>'
        links, next_url, issues = pipeline.archive_links(html, pipeline.ARCHIVE)
        self.assertEqual(links, [])
        self.assertIsNone(next_url)
        self.assertEqual([x["code"] for x in issues], ["UNDATED_TXT_LINK"])

    def test_nonofficial_host_and_non_txt_remain_rejected(self):
        html = b'''
          <a href="https://example.com/CropProg-05-02-2016.txt" title="May 02 2016">Bad</a>
          <a href="/release/CropProg-05-02-2016.pdf" title="May 02 2016">PDF</a>
        '''
        links, _, issues = pipeline.archive_links(html, pipeline.ARCHIVE)
        self.assertEqual((links, issues), ([], []))


if __name__ == "__main__":
    unittest.main()

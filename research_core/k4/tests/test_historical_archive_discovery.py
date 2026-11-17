import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from research_core.k4.historical_archive_discovery import (
    Anchors, CANDIDATES, once, probe, HOSTS,
)

class HistoricalArchiveDiscoveryTests(unittest.TestCase):
    def test_all_source_hosts_are_allowlisted(self):
        self.assertEqual(set(CANDIDATES),{
            "historic_usda_zip_primary","historic_usda_zip_mirror",
            "fgis_report_index","fgis_report_index_slug"})
        self.assertEqual(HOSTS,{"www.usda.gov","usda.azureedge.us",
                                "mymarketnews.ams.usda.gov"})

    def test_unknown_host_rejected(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_NOT_ALLOWLISTED"):
            once("https://example.com/archive.zip")

    def test_http_not_found_is_gap_not_a_zero(self):
        with patch("research_core.k4.historical_archive_discovery.urlopen",
                   side_effect=HTTPError("https://www.usda.gov/404",404,"Not Found",None,None)):
            r=once(CANDIDATES["historic_usda_zip_primary"])
        self.assertEqual(r["status"],"HTTP_UNAVAILABLE")
        self.assertEqual(r["http_status"],404)

    def test_dated_archive_links_not_pit_certified(self):
        parser=Anchors()
        parser.feed('<a href="/files/WA_GR101_20251110.txt">2025-11-10</a>'
                    '<a href="/files/WA_GR101.txt">latest report</a>')
        self.assertEqual(len(parser.items),2)
        self.assertTrue(any("20251110" in x["href"] for x in parser.items))

    def test_probe_never_unlocks_training_or_trading(self):
        with patch("research_core.k4.historical_archive_discovery.once",
                   return_value={"status":"RETRIEVED_NOT_PIT","bytes":900}):
            r=probe()
        self.assertFalse(r["historical_feature_pit_certified"])
        self.assertFalse(r["training_eligible"])
        self.assertFalse(r["trade_eligible"])
        self.assertFalse(r["asof_official_raw_verified"])

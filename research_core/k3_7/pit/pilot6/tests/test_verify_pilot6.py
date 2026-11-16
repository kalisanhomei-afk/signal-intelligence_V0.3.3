"""PIT6 negative tests; synthetic bytes never enter historical source evidence."""
import io
import unittest
from zipfile import ZipFile
from research_core.k3_7.pit.pilot6.verify_pilot6 import validate_nass, validate_wasde


class TimeProvenanceFailClosedTests(unittest.TestCase):
    def nass_record(self):
        return {
            "year": 2016, "release_date": "2016-06-06",
            "official_numeric_value": "75", "national_condition_five_categories": [1,3,21,61,14],
            "metric": "national_good_excellent_pct",
        }

    def test_original_nass_text_national_table(self):
        raw = (b"Released June 6, 2016, by NASS\n"
               b"Corn Condition - Selected States: Week Ending June 5, 2016\n"
               b"18 States ......: 1 3 21 61 14\n")
        result = validate_nass(raw, self.nass_record())
        self.assertEqual(result["verified_official_raw_numeric_value"], "75")

    def test_nass_one_percent_difference_rejected(self):
        r = self.nass_record()
        raw = (b"Released June 6, 2016, by NASS\n"
               b"Corn Condition - Selected States: Week Ending June 5, 2016\n"
               b"18 States ......: 1 3 22 60 14\n")
        with self.assertRaisesRegex(AssertionError, "five ratings mismatch"):
            validate_nass(raw, r)

    def test_nass_report_date_conflict_rejected(self):
        raw = (b"Released June 13, 2016, by NASS\n"
               b"Corn Condition - Selected States: Week Ending June 12, 2016\n"
               b"18 States ......: 1 3 21 61 14\n")
        with self.assertRaisesRegex(AssertionError, "released date missing"):
            validate_nass(raw, self.nass_record())

    def test_wasde_exact_metric_filter_and_value(self):
        header = ("ReportTitle,ReleaseDate,MarketYear,Commodity,Region,Attribute,"
                  "AnnualQuarterFlag,Unit,Value,ReleaseTime\n")
        row = ("U.S. Feed Grain and Corn Supply and Use,2016-06-10,2016/17,Corn,"
               "United States,Ending Stocks,Annual,Million Bushels,2008.00,12:00:00\n")
        record = {"year": 2016, "release_date": "2016-06-10", "marketing_year": "2016/17",
                  "metric": "ending_stocks_million_bushels",
                  "official_unit": "Million Bushels", "official_numeric_value": "2008.00",
                  "source_member": "", "source_member_sha256": ""}
        self.assertEqual(validate_wasde((header+row).encode(), record)
                         ["verified_official_raw_numeric_value"], "2008.00")

    def test_wasde_disallows_future_rewritten_value(self):
        header = ("ReportTitle,ReleaseDate,MarketYear,Commodity,Region,Attribute,"
                  "AnnualQuarterFlag,Unit,Value,ReleaseTime\n")
        row = ("U.S. Feed Grain and Corn Supply and Use,2016-06-10,2016/17,Corn,"
               "United States,Ending Stocks,Annual,Million Bushels,2010.00,12:00:00\n")
        r = {"year": 2016, "release_date": "2016-06-10", "marketing_year": "2016/17",
             "metric": "ending_stocks_million_bushels", "official_unit": "Million Bushels",
             "official_numeric_value": "2008.00", "source_member": "", "source_member_sha256": ""}
        with self.assertRaisesRegex(AssertionError, "observed numerical value"):
            validate_wasde((header+row).encode(), r)


if __name__ == "__main__":
    unittest.main()

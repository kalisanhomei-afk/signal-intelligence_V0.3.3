import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vintage_backfill import manifest, parse_release_bytes, collect, validate_url

HEADER = 'WasdeNumber,ReportDate,ReportTitle,Attribute,ReliabilityProjection,Commodity,Region,MarketYear,ProjEstFlag,AnnualQuarterFlag,Value,Unit,ReleaseDate,ReleaseTime,ForecastYear,ForecastMonth\n'
def sample(month, day, value, year="2026/27"):
    return (HEADER + f'676,Oct 2026,U.S. Feed Grain and Corn Supply and Use,Ending Stocks,,Corn,United States,{year},Proj.,Annual,{value},Million Bushels,{month}-{day},12:00:00,2026,10\n').encode()

def url(month):
    return 'https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-' + month + '.csv'

class VintageTests(unittest.TestCase):
    def test_manifest_has_gap_explicit(self):
        months = [m for m,_ in manifest('2025-09','2025-11')]
        self.assertEqual(months,['2025-09','2025-11'])

    def test_one_release_parses(self):
        rows, audit = parse_release_bytes(sample('2026-10','09','1849'), '2026-10', url('2026-10'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['value'], 1849)
        self.assertEqual(rows[0]['release_at'], '2026-10-09T12:00:00-04:00')

    def test_month_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            parse_release_bytes(sample('2026-10','09','1849'), '2026-11', url('2026-11'))

    def test_url_allowlist_blocks_non_usda(self):
        with self.assertRaises(ValueError):
            validate_url('https://evil.example/oce-wasde-report-data-2026-10.csv', '2026-10')

    def test_two_reports_same_crop_year_transition(self):
        def loader(u, m):
            return sample('2026-10','09','1849') if m == '2026-10' else sample('2026-11','10','1758')
        rows, audit = collect([('2026-10',url('2026-10')),('2026-11',url('2026-11'))], loader)
        self.assertEqual(len(rows),2)
        self.assertEqual(audit['transitions'], 1)
        self.assertEqual(audit['marketing_years'], ['2026/27'])

if __name__ == '__main__':
    unittest.main()

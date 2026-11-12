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

# The tests below explicitly prevent a missing public URL from destroying
# diagnostics; source gaps must remain auditable.
class ResilienceTests(unittest.TestCase):
    def test_http_404_is_captured_with_month_and_url(self):
        from urllib.error import HTTPError
        def loader(u, m):
            if m == '2026-09':
                raise HTTPError(u, 404, 'Not Found', {}, None)
            return sample('2026-10', '09', '1849')
        rows, audit = collect([('2026-09',url('2026-09')),('2026-10',url('2026-10'))],loader)
        self.assertEqual(len(rows),1)
        self.assertEqual(audit['download_failures'][0]['month'],'2026-09')
        self.assertEqual(audit['download_failures'][0]['url'],url('2026-09'))
        self.assertEqual(audit['download_failures'][0]['category'],'HTTP_404_MISSING')
        self.assertEqual(audit['status'],'FAILED_INSUFFICIENT_HISTORY')

    def test_parser_error_is_not_silently_treated_as_404(self):
        def loader(u, m):
            return b'not-a-wasde-csv'
        rows, audit = collect([('2026-10', url('2026-10'))], loader)
        self.assertEqual(rows, [])
        self.assertEqual(audit['download_failures'][0]['category'],'PARSE_OR_VALIDATION_ERROR')
        self.assertTrue(audit['serious_source_error'])

    def test_primary_404_uses_official_usda_mirror(self):
        from urllib.error import HTTPError
        from unittest.mock import patch
        from vintage_backfill import fetch
        def fake_once(u, m):
            if 'www.usda.gov' in u:
                raise HTTPError(u,404,'Not Found',{},None)
            return sample('2026-10','09','1849')
        with patch('vintage_backfill._fetch_once', side_effect=fake_once):
            content, retrieved = fetch(url('2026-10'),'2026-10')
        self.assertIn(b'Ending Stocks',content)
        self.assertEqual(retrieved,'https://usda.azureedge.us/sites/default/files/documents/oce-wasde-report-data-2026-10.csv')

    def test_complete_404_mirror_failure_reports_both_paths(self):
        from urllib.error import HTTPError
        from unittest.mock import patch
        from vintage_backfill import fetch
        def fail_once(u, m):
            raise HTTPError(u,404,'Not Found',{},None)
        with patch('vintage_backfill._fetch_once', side_effect=fail_once):
            with self.assertRaises(FileNotFoundError) as ctx:
                fetch(url('2026-10'),'2026-10')
        self.assertIn('www.usda.gov',str(ctx.exception))
        self.assertIn('usda.azureedge.us',str(ctx.exception))

    def test_cli_failure_still_writes_audit_and_csv(self):
        import json
        import tempfile
        from unittest.mock import patch
        from vintage_backfill import main
        from urllib.error import HTTPError
        def broken(u,m):
            raise HTTPError(u,404,'Not Found',{},None)
        with tempfile.TemporaryDirectory() as d:
            dst=Path(d)/'k33-review'/'historical_vintages.csv'
            audit_file=Path(d)/'k33-review'/'vintage_archive_audit.json'
            args=['vintage_backfill.py','--start','2026-10','--end','2026-10',
                  '--output',str(dst),'--audit',str(audit_file)]
            with patch('vintage_backfill.fetch',side_effect=broken), patch.object(sys,'argv',args):
                with self.assertRaises(SystemExit):
                    main()
            self.assertTrue(dst.exists())
            self.assertTrue(audit_file.exists())
            data=json.loads(audit_file.read_text(encoding='utf-8'))
            self.assertEqual(data['download_failures'][0]['month'],'2026-10')
            self.assertEqual(data['status'],'FAILED_INSUFFICIENT_HISTORY')

if __name__ == '__main__':
    unittest.main()

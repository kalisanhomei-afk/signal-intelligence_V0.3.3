"""Deterministic tests using explicitly artificial, non-observation fixtures."""
import csv
from datetime import datetime
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pipeline as p

FIXTURE = (ROOT/'fixtures/schema_example.csv').read_bytes()
ARCHIVE = (ROOT/'fixtures/archive_example.html').read_bytes()
BASE = 'https://www.usda.gov/sites/default/files/documents/'
CSV_URL = BASE + 'oce-wasde-report-data-2022-01.csv'
ZIP_URL = BASE + 'oce-wasde-report-data-2016-01-to-2020-12.zip'
TEST_TIME = '2026-11-13T06:00:00Z'  # injected test clock, never historical time evidence


def item(raw=FIXTURE, url=CSV_URL, when=TEST_TIME):
    return p.Download(raw, url, when, url)


def transform(raw=FIXTURE, **changes):
    reader = csv.DictReader(io.StringIO(raw.decode()))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, reader.fieldnames, lineterminator='\n')
    writer.writeheader()
    for row in reader:
        row.update(changes)
        writer.writerow(row)
    return output.getvalue().encode()


def join_csv(*parts):
    return parts[0] + b''.join(part.split(b'\n', 1)[1] for part in parts[1:])


def zipped(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name, data in entries:
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            archive.writestr(entry, data)
    return output.getvalue()


def parse(raw=FIXTURE, months=None):
    return p.parse_csv(raw, item(raw), expected_months=months or ['2022-01'])


class ParserTests(unittest.TestCase):
    def test_minimum_metrics_units_and_empty_pit(self):
        rows, audits, observed = parse()
        self.assertEqual(len(rows), 14)
        self.assertTrue(p.REQUIRED_METRICS <= {r['metric'] for r in rows})
        self.assertEqual(observed, {'2022-01-12'})
        self.assertEqual(audits[0]['status'], 'PASS')
        self.assertTrue(all(c['status']=='PASS' for c in audits[0]['checks'].values()))
        for row in rows:
            self.assertEqual(row['source_sha256'], p.sha256(FIXTURE))
            self.assertEqual(row['retrieved_at_utc'], TEST_TIME)
            self.assertEqual(row['timestamp_quality'], 'UNKNOWN')
            self.assertEqual(row['quality_status'], 'PIT_UNVERIFIED')
            self.assertEqual(row['published_at_utc'], '')
            self.assertEqual(row['available_at_utc'], '')
            self.assertEqual(row['evidence_url'], '')
        self.assertEqual(next(r['unit'] for r in rows if r['metric']=='yield_bushels_per_acre'), 'Bushels')

    def test_revisions_and_estimates_never_overwritten(self):
        revised = transform(ReleaseDate='2022-02-09', ProjEstFlag='Est.')
        revised = revised.replace(b',110,Million Bushels', b',120,Million Bushels')
        revised = revised.replace(b',100,Million Bushels', b',110,Million Bushels')
        revised = revised.replace(b',1110,Million Bushels', b',1120,Million Bushels')
        raw = join_csv(FIXTURE, revised)
        rows, checks, _ = parse(raw, ['2022-01','2022-02'])
        ending = [r for r in rows if r['metric']=='ending_stocks_million_bushels']
        self.assertEqual([r['value'] for r in ending], ['110','120'])
        self.assertEqual([r['projection_estimate_flag'] for r in ending], ['Proj.','Est.'])
        self.assertEqual(len(checks), 2)

    def test_all_marketing_years_in_one_release_preserved(self):
        raw = join_csv(FIXTURE, transform(MarketYear='2020/21', ProjEstFlag=''))
        rows, checks, _ = parse(raw)
        self.assertEqual(len(rows), 28)
        self.assertEqual({r['marketing_year'] for r in rows}, {'2020/21','2021/22'})
        self.assertEqual(len(checks), 2)

    def test_required_missing_metric_is_explicit_not_filled(self):
        raw = FIXTURE.replace(b',Imports,', b',Unfamiliar import label,')
        rows, checks, _ = parse(raw)
        self.assertEqual(checks[0]['status'], 'INCOMPLETE_METRICS')
        self.assertEqual(checks[0]['missing_metrics'], ['imports_million_bushels'])
        self.assertEqual(checks[0]['unselected_attributes'], {'Unfamiliar import label':1})
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(r['quality_status']=='INCOMPLETE_METRICS' for r in rows))

    def test_bad_units_quarantine_entire_cohort(self):
        rows, checks, _ = parse(FIXTURE.replace(b'Million Acres', b'Million Hectares'))
        self.assertEqual(rows, [])
        self.assertEqual(checks[0]['status'], 'PARSE_ERROR')
        self.assertIn('UNIT_MISMATCH', checks[0]['errors'][0]['reason'])

    def test_balance_mismatch_quarantines_cohort(self):
        rows, checks, _ = parse(FIXTURE.replace(b',110,Million Bushels', b',999,Million Bushels'))
        self.assertEqual(rows, [])
        self.assertEqual(checks[0]['status'], 'BALANCE_MISMATCH')

    def test_domestic_components_and_reported_totals_checked(self):
        for before, after, label in [(b',1110,',b',1115,','reported_total_supply'),
                                     (b',500,',b',505,','domestic_components'),
                                     (b',1000,Million Bushels,2022-01-12,Annual,Proj.\nU.S. Feed Grain and Corn Supply and Use,Ending Stocks',
                                      b',1005,Million Bushels,2022-01-12,Annual,Proj.\nU.S. Feed Grain and Corn Supply and Use,Ending Stocks', 'reported_total_use')]:
            with self.subTest(label=label):
                rows, checks, _ = parse(FIXTURE.replace(before, after))
                self.assertEqual(rows, [])
                self.assertEqual(checks[0]['checks'][label]['status'], 'FAIL')

    def test_rounding_tolerance_does_not_impute(self):
        rows, checks, _ = parse(FIXTURE.replace(b',110,Million Bushels', b',112,Million Bushels'))
        self.assertEqual(checks[0]['checks']['supply_use']['residual'], '-2')
        self.assertEqual(next(r['value'] for r in rows if r['metric']=='ending_stocks_million_bushels'), '112')

    def test_area_yield_product_check(self):
        rows, checks, _ = parse(FIXTURE.replace(b',10.0,Million Acres', b',20.0,Million Acres'))
        self.assertEqual(rows, [])
        self.assertEqual(checks[0]['checks']['area_yield_production']['status'], 'FAIL')

    def test_duplicate_metric_even_identical_is_rejected(self):
        for line in [FIXTURE.splitlines(keepends=True)[1],
                     FIXTURE.splitlines(keepends=True)[1].replace(b',11,',b',12,')]:
            with self.subTest(line=line):
                rows, checks, _ = parse(FIXTURE + line)
                self.assertEqual(rows, [])
                self.assertIn('DUPLICATE_METRIC', checks[0]['errors'][0]['reason'])

    def test_missing_nonfinite_negative_and_malformed_numbers_rejected(self):
        for token in (b'', b'NaN', b'Infinity', b'-1', b'1e3', b'1,00'):
            with self.subTest(token=token):
                # Quote malformed comma cells to keep the CSV structure valid.
                replacement = b'"'+token+b'"' if b',' in token else token
                rows, checks, _ = parse(FIXTURE.replace(b',110,Million Bushels', b','+replacement+b',Million Bushels'))
                self.assertFalse(rows)
                self.assertEqual(checks[0]['status'], 'PARSE_ERROR')
        self.assertEqual(p.number('1,234.5'), p.Decimal('1234.5'))

    def test_bom_crlf_date_and_marketing_year_formats(self):
        raw = transform(ReleaseDate='1/12/2022', MarketYear='2021/2022')
        rows, _, _ = parse(b'\xef\xbb\xbf'+raw.replace(b'\n',b'\r\n'))
        self.assertEqual(len(rows), 14)
        self.assertTrue(all(r['release_date']=='2022-01-12' and r['marketing_year']=='2021/22' for r in rows))

    def test_source_date_and_marketing_year_fail_closed(self):
        for changes in ({'ReleaseDate':'2022-02-09'}, {'ReleaseDate':'January 12'},
                        {'MarketYear':'2021/23'}, {'MarketYear':'2021'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse(transform(**changes))

    def test_only_pilot_annual_us_corn_table_selected(self):
        for changes in ({'ReportTitle':'World Corn Supply and Use'}, {'Commodity':'Wheat'},
                        {'Region':'World'}, {'AnnualQuarterFlag':'Quarterly'},
                        {'ReleaseDate':'2019-01-12'}):
            with self.subTest(changes=changes):
                rows, _, _ = parse(transform(**changes))
                self.assertFalse(rows)

    def test_schema_drift_and_malformed_csv_fail_closed(self):
        for raw in (FIXTURE.replace(b'ReleaseDate',b'ReportDate',1), b'<html>Access denied</html>',
                    FIXTURE.replace(b'ProjEstFlag',b'Value',1), FIXTURE+b'truncated,row\n'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                parse(raw)

    def test_extra_nonpilot_attributes_are_logged(self):
        line = transform(Attribute='Avg. Farm Price').splitlines(keepends=True)[1]
        rows, checks, _ = parse(FIXTURE+line)
        self.assertEqual(len(rows), 14)
        self.assertEqual(checks[0]['unselected_attributes'], {'Avg. Farm Price':1})


class SourceTests(unittest.TestCase):
    def test_discovery_only_uses_observed_official_pilot_links(self):
        found = p.discover(ARCHIVE, p.ARCHIVE_URL)
        self.assertEqual(len(found), 2)
        self.assertEqual({r['url'] for r in found}, {ZIP_URL,CSV_URL})
        self.assertEqual(len(next(r for r in found if r['kind']=='historical_zip')['months']),24)
        self.assertEqual(next(r for r in found if r['kind']=='monthly_csv')['months'],['2022-01'])
        self.assertEqual(p.discover(b'<html>no download links</html>',p.ARCHIVE_URL),[])

    def test_versioned_csv_links_are_discovered_separately(self):
        raw = ARCHIVE + b'<a href="/sites/default/files/documents/oce-wasde-report-data-2022-01-V2.csv">corrected</a>'
        found = p.discover(raw,p.ARCHIVE_URL)
        self.assertEqual(len(found),3)

    def test_urls_and_redirects_checked_before_request(self):
        for url in ('http://www.usda.gov/a', 'https://www.usda.gov.evil.org/a',
                    'https://user@www.usda.gov/a', 'https://www.usda.gov:444/a',
                    'https://www.usda.gov/a#fragment'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                p.check_url(url)
        with self.assertRaises(ValueError):
            p.OfficialRedirects().redirect_request(None,None,302,'',{},'https://example.invalid/x')

    def test_download_enforces_size_url_and_actual_clock(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def geturl(self): return CSV_URL
            def read(self,limit): return FIXTURE
        with patch.object(p,'build_opener') as opener, patch.object(p,'utc_now',return_value=TEST_TIME):
            opener.return_value.open.return_value=Response()
            result=p.download(CSV_URL)
            self.assertEqual(result.retrieved_at_utc,TEST_TIME)
            self.assertEqual(result.raw,FIXTURE)
        for when in ('2026-11-13T06:00:00','2026-11-13T06:00:00+08:00'):
            with self.subTest(when=when), self.assertRaises(ValueError):
                item(when=when)
        with patch.object(p,'MAX_BYTES',1), self.assertRaises(ValueError):
            item()

    def test_zip_filters_nonpilot_years_and_preserves_raw_and_member_hashes(self):
        rawcsv = join_csv(transform(ReleaseDate='2016-01-12',MarketYear='2015/16'),
                          transform(ReleaseDate='2020-01-10',MarketYear='2019/20'),
                          transform(ReleaseDate='2019-01-10',MarketYear='2018/19'))
        rawzip=zipped([('history.csv',rawcsv),('readme.txt',b'not data')])
        spec=next(r for r in p.discover(ARCHIVE,p.ARCHIVE_URL) if r['kind']=='historical_zip')
        rows, checks, observed=p.parse_source(item(rawzip,ZIP_URL),spec)
        self.assertEqual(len(rows),28)
        self.assertEqual(len(checks),2)
        self.assertEqual(observed,{'2016-01-12','2020-01-10'})
        self.assertTrue(all(r['source_sha256']==p.sha256(rawzip) and
                            r['source_member_sha256']==p.sha256(rawcsv) and
                            r['source_member']=='history.csv' for r in rows))

    def test_zip_invalid_unsafe_duplicate_and_oversized_rejected(self):
        for raw in (b'not a zip',zipped([('../escape.csv',FIXTURE)]),zipped([('readme.txt',b'x')])):
            with self.subTest(raw=raw[:5]), self.assertRaises((ValueError,zipfile.BadZipFile)):
                list(p.csv_members(raw,'historical_zip'))
        with patch.object(p,'MAX_UNPACKED',1), self.assertRaises(ValueError):
            list(p.csv_members(zipped([('data.csv',FIXTURE)]),'historical_zip'))

    def test_duplicate_metric_across_zip_members_rejected(self):
        raw=zipped([('a.csv',FIXTURE),('b.csv',FIXTURE)])
        with self.assertRaisesRegex(ValueError,'across ZIP members'):
            p.parse_source(item(raw,ZIP_URL),{'kind':'historical_zip','months':['2022-01']})

    def test_cache_preserves_versions_and_new_acquisition_times(self):
        with tempfile.TemporaryDirectory() as td:
            cache=Path(td)
            a=p.save_download(item(),cache)
            b=p.save_download(item(when='2026-11-14T06:00:00Z'),cache)
            c=p.save_download(item(FIXTURE+b'\n'),cache)
            self.assertEqual(a['raw_file'],b['raw_file'])
            self.assertNotEqual(a['receipt_file'],b['receipt_file'])
            self.assertNotEqual(a['retrieved_at_utc'],b['retrieved_at_utc'])
            self.assertNotEqual(a['raw_file'],c['raw_file'])
            (cache/a['raw_file']).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                p.save_download(item(),cache)


class CollectionTests(unittest.TestCase):
    def run_collection(self, fetch, cache):
        with patch.object(p,'utc_now',return_value=TEST_TIME):
            return p.collect(fetch=fetch,raw_dir=cache)

    def example_fetch(self,url):
        if url==p.ARCHIVE_URL: return item(ARCHIVE,url)
        if url==CSV_URL: return item()
        raise URLError('artificial offline source failure')

    def test_source_unavailable_has_36_gaps_no_fake_provenance(self):
        def blocked(url): raise URLError('CONNECT 403 test example')
        with tempfile.TemporaryDirectory() as td:
            rows, manifest=self.run_collection(blocked,Path(td))
            self.assertFalse(rows)
            self.assertEqual(manifest['coverage_counts'],{'SOURCE_UNAVAILABLE':36})
            self.assertEqual(manifest['verified_pit_records'],0)
            self.assertEqual(manifest['status'],'PARTIAL_OR_BLOCKED')
            self.assertNotIn('retrieved_at_utc',manifest['archive'])
            self.assertNotIn('source_sha256',manifest['archive'])

    def test_http_200_error_page_is_not_proof_of_missing_releases(self):
        with tempfile.TemporaryDirectory() as td:
            rows, manifest=self.run_collection(lambda url:item(b'<html>Access denied</html>',url),Path(td))
            self.assertFalse(rows)
            self.assertEqual(manifest['archive']['status'],'PARSE_ERROR')
            self.assertEqual(manifest['coverage_counts'],{'PARSE_ERROR':36})
            self.assertEqual(manifest['archive']['source_sha256'],p.sha256(b'<html>Access denied</html>'))

    def test_missing_link_unavailable_and_404_are_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            rows, manifest=self.run_collection(self.example_fetch,Path(td))
            coverage={r['month']:r['status'] for r in manifest['coverage']}
            self.assertEqual(coverage['2022-01'],'OBSERVED')
            self.assertEqual(coverage['2022-02'],'MISSING_OFFICIAL_RELEASE')
            self.assertEqual(coverage['2016-01'],'SOURCE_UNAVAILABLE')
            self.assertEqual(len(rows),14)
        def missing(url):
            if url==p.ARCHIVE_URL: return item(ARCHIVE,url)
            raise HTTPError(url,404,'not found',{},None)
        with tempfile.TemporaryDirectory() as td:
            _, manifest=self.run_collection(missing,Path(td))
            self.assertEqual({s['status'] for s in manifest['sources']},{'MISSING_SOURCE_RESOURCE'})
            self.assertEqual(manifest['coverage'][0]['status'],'SOURCE_UNAVAILABLE')

    def test_parse_error_preserves_raw_hash_receipt_and_no_data(self):
        def bad(url):
            if url==p.ARCHIVE_URL: return item(ARCHIVE,url)
            return item(b'bad format',url)
        with tempfile.TemporaryDirectory() as td:
            rows, manifest=self.run_collection(bad,Path(td))
            self.assertFalse(rows)
            self.assertEqual({s['status'] for s in manifest['sources']},{'PARSE_ERROR'})
            self.assertTrue(all(s['source_sha256']==p.sha256(b'bad format') for s in manifest['sources']))
            self.assertEqual(manifest['coverage'][0]['status'],'PARSE_ERROR')

    def test_incomplete_cohort_does_not_pass_coverage_gate(self):
        def incomplete(url):
            if url==p.ARCHIVE_URL: return item(ARCHIVE,url)
            if url==CSV_URL: return item(FIXTURE.replace(b',Imports,',b',Unknown label,'))
            raise URLError('offline')
        with tempfile.TemporaryDirectory() as td:
            _, manifest=self.run_collection(incomplete,Path(td))
            self.assertEqual(next(c['status'] for c in manifest['coverage'] if c['month']=='2022-01'),
                             'INCOMPLETE_OR_REJECTED_COHORT')

    def test_complete_fixture_pilot_and_all_months(self):
        links=b''.join(f'<a href="{BASE}oce-wasde-report-data-2022-{m:02}.csv">x</a>'.encode() for m in range(1,13))
        archive=ARCHIVE+links
        history=join_csv(*(transform(ReleaseDate=f'{y}-{m:02}-12',MarketYear=f'{y-1}/{str(y)[-2:]}')
                           for y in (2016,2020) for m in range(1,13)))
        def full(url):
            if url==p.ARCHIVE_URL: return item(archive,url)
            if url==ZIP_URL: return item(zipped([('history.csv',history)]),url)
            month=url.split('data-')[1][:7]
            return item(transform(ReleaseDate=month+'-12'),url)
        with tempfile.TemporaryDirectory() as td:
            rows, manifest=self.run_collection(full,Path(td))
            self.assertEqual(len(rows),36*14)
            self.assertEqual(manifest['coverage_counts'],{'OBSERVED':36})
            self.assertEqual(manifest['status'],'COLLECTED_PIT_UNVERIFIED')
            self.assertEqual(manifest['verified_pit_records'],0)

    def test_source_versions_retained_and_flagged(self):
        corrected=CSV_URL.replace('.csv','-V2.csv')
        archive=ARCHIVE+f'<a href="{corrected}">correction</a>'.encode()
        def versions(url):
            if url==p.ARCHIVE_URL: return item(archive,url)
            if url in (CSV_URL,corrected): return item(FIXTURE+(b'\n' if url==corrected else b''),url)
            raise URLError('offline')
        with tempfile.TemporaryDirectory() as td:
            rows, manifest=self.run_collection(versions,Path(td))
            self.assertEqual(len(rows),28)
            self.assertEqual(len(manifest['source_version_conflicts']),14)
            self.assertTrue(all(r['quality_status']=='SOURCE_VERSION_CONFLICT' for r in rows))

    def test_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'out'
            p.write_outputs(path,[],{'test_only':True})
            before=(path/'wasde_vintages.csv').read_bytes()
            with self.assertRaises(FileExistsError):
                p.write_outputs(path,[],{})
            self.assertEqual((path/'wasde_vintages.csv').read_bytes(),before)
            result=subprocess.run([sys.executable,str(ROOT/'pipeline.py'),'--output',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('not empty',result.stderr)

    def test_offline_replay_is_deterministic_and_has_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rows, manifest=self.run_collection(self.example_fetch,root/'raw')
            manifest['mode']='OFFLINE_SYNTHETIC_TEST_ONLY'
            p.write_outputs(root/'first',rows,manifest)
            with patch.object(p,'download',side_effect=AssertionError('NO NETWORK')):
                a, report=p.replay(root/'first/manifest.json',root/'raw')
                b, _=p.replay(root/'first/manifest.json',root/'raw')
            self.assertEqual(rows,a)
            self.assertEqual(a,b)
            self.assertEqual(report['mode'],'OFFLINE_REPLAY')
            self.assertTrue(all(r['retrieved_at_utc']==TEST_TIME for r in a))
            p.write_outputs(root/'second',a,report)
            self.assertEqual((root/'first/wasde_vintages.csv').read_bytes(),
                             (root/'second/wasde_vintages.csv').read_bytes())
            result=subprocess.run([sys.executable,str(ROOT/'pipeline.py'),'--replay',str(root/'first/manifest.json'),
                                   '--raw-dir',str(root/'raw'),'--output',str(root/'cli')],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)  # intentionally partial test archive
            self.assertEqual((root/'cli/wasde_vintages.csv').read_bytes(),(root/'first/wasde_vintages.csv').read_bytes())

    def test_replay_detects_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rows, manifest=self.run_collection(self.example_fetch,root/'raw')
            p.write_outputs(root/'out',rows,manifest)
            (root/'raw'/manifest['archive']['raw_file']).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
                p.replay(root/'out/manifest.json',root/'raw')


if __name__=='__main__':
    unittest.main()

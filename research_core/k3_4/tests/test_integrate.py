import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import date

MOD = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MOD))
import integrate as m

TEXT=b'''Crop Progress\nReleased October 5, 2026, by the National Agricultural Statistics Service\nCorn Mature - Selected States\n18 States ........: 23 24 25 26\nCorn Condition - Selected States: Week Ending October 4, 2026\n[These 18 States planted 91% of the 2025 corn acreage]\nState : Very poor : Poor : Fair : Good : Excellent\nColorado ....: 6 31 22 41 0\n18 States ......:      6          12          28          42          12\nPrevious week ..:      6          11          26          44          13\nSoybeans Harvested - Selected States\n18 States ......:     70  20  5  5\n'''

def balance_fixture():
    fields=['ReportTitle','Attribute','Commodity','Region','MarketYear','Value','Unit','ReleaseDate','AnnualQuarterFlag']
    buf=io.StringIO(); writer=csv.DictWriter(buf,fieldnames=fields);writer.writeheader()
    vals={
        'Beginning Stocks':(2095,'Million Bushels'),
        'Production':(16034,'Million Bushels'),
        'Imports':(25,'Million Bushels'),
        'Supply, Total':(18154,'Million Bushels'),
        'Use, Total':(16305,'Million Bushels'),
        'Ending Stocks':(1849,'Million Bushels'),
        'Area Harvested':(88.5,'Million Acres'),
        'Yield per Harvested Acre':(181.2,'Bushels'),
        'Exports':(3300,'Million Bushels'),
    }
    for a,(v,u) in vals.items():
        writer.writerow(dict(ReportTitle='U.S. Feed Grain and Corn Supply and Use',Attribute=a,Commodity='Corn',Region='United States',MarketYear='2026/27',Value=v,Unit=u,ReleaseDate='2026-10-09',AnnualQuarterFlag='Annual'))
    # deceptively similar row in world balance must be discarded
    writer.writerow(dict(ReportTitle='World Corn Supply and Use',Attribute='Ending Stocks',Commodity='Corn',Region='United States',MarketYear='2026/27',Value=46.97,Unit='Million Metric Tons',ReleaseDate='2026-10-09',AnnualQuarterFlag='Annual'))
    return buf.getvalue().encode('utf8')

class K34Test(unittest.TestCase):
    def test_nass_real_oct_excerpt(self):
        r=m.parse_nass_txt(TEXT,'https://esmis.nal.usda.gov/sites/default/release-files/796095/prog4026.txt',date(2026,10,5))
        self.assertEqual(r['good_excellent_pct'],54)
        self.assertEqual(r['state_count'],18)
        self.assertEqual(r['available_at_proxy_utc'],'2026-10-06T12:00:00Z')
    def test_nass_discard_wrong_crop(self):
        with self.assertRaisesRegex(ValueError,'NO_CORN_CONDITION_BLOCK'):
            m.parse_nass_txt(TEXT.replace(b'Corn Condition',b'Soybean Condition'),'https://esmis.nal.usda.gov/sites/default/release-files/x/prog4026.txt')
    def test_nass_reject_missing_or_bad_row(self):
        with self.assertRaises(ValueError):m.parse_nass_txt(TEXT.replace(b'6          12          28          42          12',b'6          12          28          42          20'),'https://esmis.nal.usda.gov/sites/default/release-files/796095/prog4026.txt')
    def test_no_wrong_release_date(self):
        with self.assertRaisesRegex(ValueError,'mismatch'):m.parse_nass_txt(TEXT,'https://esmis.nal.usda.gov/sites/default/release-files/796095/prog4026.txt',date(2026,10,6))
    def test_archive_links(self):
        h='''<table><tr><td>Oct 05 2026</td><td><a href="/sites/default/release-files/796095/prog4026.txt">Oct 05 2026 - txt</a></td></tr><tr><td><a href="/sites/default/release-files/796095/prog4026.pdf">Oct 05 2026 - pdf</a></td></tr></table>'''
        self.assertEqual(m.archive_links(h),[(date(2026,10,5),'https://esmis.nal.usda.gov/sites/default/release-files/796095/prog4026.txt')])
    def test_archive_page_traversal_stops_at_older_year(self):
        pages=[
            '<a href="/sites/default/release-files/1/prog1126.txt">Mar 15 2026 - txt</a>',
            '<a href="/sites/default/release-files/2/prog5222.txt">Dec 25 2022 - txt</a>',
        ]
        calls=[]
        def fetch(url,max_bytes=None):
            calls.append(url)
            return pages[len(calls)-1].encode('utf8')
        found,log=m.discover_nass(2023,2026,8,fetch=fetch)
        self.assertEqual(len(found),1)
        self.assertEqual(len(calls),2)
        self.assertEqual(log[-1]['status'],'OK')
    def test_nass_unreleased_condition_is_explicit_skip(self):
        with self.assertRaisesRegex(ValueError,'NO_CORN_CONDITION_BLOCK'):
            m.parse_nass_txt(b'Crop Progress\nReleased November 9, 2026\nCorn Harvested - Selected States',
                             'https://esmis.nal.usda.gov/sites/default/release-files/1/prog4626.txt')
    def test_bad_host_rejected(self):
        self.assertFalse(m.allowed('https://esmis.nal.usda.gov.evil.org/x'))
        self.assertFalse(m.allowed('http://www.usda.gov/x'))
    def test_balance_columns_and_mass_balance(self):
        r=m.parse_wasde_csv(balance_fixture(),'https://www.usda.gov/a.csv','2026/27','2026-10-09')
        self.assertEqual(r['ending_stocks_million_bushels'],1849)
        self.assertEqual(r['yield_bushels_per_acre'],181.2)
        self.assertEqual(r['balance_residual_million_bushels'],0)
        self.assertEqual(r['quality_status'],'PASS_ROUNDING_TOLERANCE')
    def test_balance_missing_value_rejected(self):
        fake=balance_fixture().replace(b'Beginning Stocks',b'Wrong Stock Label')
        with self.assertRaisesRegex(ValueError,'Missing balance values'):
            m.parse_wasde_csv(fake,'https://www.usda.gov/a.csv','2026/27','2026-10-09')
    def test_stock_records_46(self):
        rows=m.stock_rows(MOD/'inputs/historical_vintages.csv')
        self.assertEqual(len(rows),46)
        self.assertEqual(len(m.transitions(rows)),41)
    def test_k31_four_records(self):
        rows=m.parse_manual_k31(MOD/'inputs/k31_selected_observations.json')
        self.assertEqual(len(rows),4)
        self.assertEqual([r['good_excellent_pct'] for r in rows],[67,61,56,54])
    def test_k31_vs_official_conflict(self):
        old=m.parse_manual_k31(MOD/'inputs/k31_selected_observations.json')
        bad=dict(old[0]);bad['good_excellent_pct']=99
        joined,err=m.combine_nass([bad],old)
        self.assertEqual(len(err),1)
        self.assertEqual(joined[0]['good_excellent_pct'],67)
    def test_join_never_uses_nass_after_origin(self):
        stocks=m.stock_rows(MOD/'inputs/historical_vintages.csv')
        k31=m.parse_manual_k31(MOD/'inputs/k31_selected_observations.json')
        joined=m.make_join(stocks,k31)
        self.assertEqual(len(joined),41)
        for row in joined:
            self.assertEqual(row['target_is_future_of_origin'],'true')
            self.assertEqual(row['pit_status'],'PROXY_ONLY_NOT_INDEPENDENTLY_VERIFIED')
            if row['nass_available_proxy_utc']:
                self.assertLess(row['nass_available_proxy_utc'],row['forecast_origin_proxy_utc'])
    def test_offline_job_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            args=m.argparse.Namespace(stocks_csv=str(MOD/'inputs/historical_vintages.csv'),audit_json=str(MOD/'inputs/vintage_archive_audit.json'),
                 k31_json=str(MOD/'inputs/k31_selected_observations.json'),output=td,fetch_nass=False,fetch_wasde=False,start_year=2023,end_year=2026,max_pages=23,max_reports=180)
            s=m.run(args)
            self.assertEqual(s['base_K33_stocks'],46)
            self.assertEqual(s['base_K33_transitions'],41)
            self.assertEqual(s['nass_total_usable'],4)
            self.assertEqual(s['join_pit_verified'],0)
            self.assertTrue((Path(td)/'audit.json').exists())
            self.assertEqual(s['status'],'RESEARCH_ONLY_PIT_UNVERIFIED')

if __name__=='__main__':unittest.main()

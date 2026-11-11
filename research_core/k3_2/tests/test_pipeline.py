import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
import pipeline as k32
import historical_import as imp

class BalanceSheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=k32.load_csv(BASE/'inputs'/'official_corn_balances.csv')

    def test_two_official_releases_reconcile(self):
        bal=k32.validate_balances(self.rows)
        self.assertEqual([x['ending_stocks_million_bushels'] for x in bal],[1849.0,1758.0])
        self.assertTrue(all(x['residual']==0 for x in bal))

    def test_oct_to_nov_stock_bridge(self):
        a,b=k32.validate_balances(self.rows)
        c=k32.bridge(a,b)
        self.assertEqual(c['ending_stocks_delta'],-91)
        self.assertEqual(c['contributions_to_stock_delta'],{'beginning_stocks':0,'production':-141,'imports':0,'domestic_use':25,'exports':25})

    def test_break_balance_fails_closed(self):
        row=copy.deepcopy(self.rows[0]);row['ending_stocks_million_bushels']='9999'
        with self.assertRaisesRegex(ValueError,'identity failed'):k32.validate_balances([row])

    def test_bad_unit_value_fails(self):
        row=copy.deepcopy(self.rows[0]);row['exports_million_bushels']='3275000'
        with self.assertRaises(ValueError):k32.validate_balances([row])

    def test_duplicate_release_fails(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):k32.validate_balances([self.rows[0],self.rows[0]])

    def test_timezone_must_be_present(self):
        row=copy.deepcopy(self.rows[0]);row['release_at']='2026-10-09T12:00:00'
        with self.assertRaisesRegex(ValueError,'timezone'):k32.validate_balances([row])

    def test_cross_marketing_year_bridge_forbidden(self):
        a,b=k32.validate_balances(self.rows)
        b['marketing_year']='2025/26'
        with self.assertRaisesRegex(ValueError,'distinct'):k32.bridge(a,b)

    def test_k31_crosscheck_does_not_promote_samples_to_official(self):
        p=BASE.parent/'k3_1'/'inputs'/'wasde_vintages.csv'
        if not p.is_file():self.skipTest('K3.1 not installed in local fixture')
        a=k32.validate_balances(self.rows)
        s=k32.k31_summary(p,a)
        self.assertEqual(s['status'],'CROSSCHECKED')
        self.assertEqual(s['monthly_transitions'],4)
        self.assertAlmostEqual(s['previous_vintage_naive_mae_million_bushels'],149)

    def test_history_does_not_claim_ready_for_two_vintages(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'history.csv'
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=['release_at','marketing_year','metric','value','unit','source_url','verification']);w.writeheader()
                for release,value in [('2025-09-11T12:00:00-04:00','2000'),('2025-10-09T12:00:00-04:00','2300')]:
                    w.writerow({'release_at':release,'marketing_year':'2025/26','metric':'ending_stocks','value':value,'unit':'million_bushels','source_url':'https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2026-10.csv','verification':'official_consolidated_vintage'})
            x=k32.load_historical(p)
            self.assertEqual(x['transitions'],1)
            self.assertFalse(x['backtest_ready'])

    def test_generate_html_is_static_and_nontrading(self):
        with tempfile.TemporaryDirectory() as d:
            a=k32.generate(BASE/'inputs'/'official_corn_balances.csv',None,None,Path(d))
            self.assertFalse(a['trading_signal'])
            self.assertFalse(a['forecast_model_trained'])
            h=(Path(d)/'review.html').read_text(encoding='utf-8')
            self.assertIn('存量流量',h)
            self.assertNotIn('<script',h)

class OfficialCsvIntakeTests(unittest.TestCase):
    def test_official_url_restricted(self):
        imp.allowlist_url('https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2026-10.csv')
        for s in ('https://evil.example/wasde.csv','http://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2026-10.csv','https://www.usda.gov.evil.example/sites/default/files/documents/oce-wasde-report-data-2026-10.csv','https://www.usda.gov/admin'): 
            with self.assertRaises(ValueError):imp.allowlist_url(s)

    def test_import_filters_table_region_and_projection(self):
        cols=['ReleaseDate','ReportTitle','Commodity','Region','MarketYear','Attribute','Value','Unit','ProjEstFlag']
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'usda.csv';o=Path(d)/'vintages.csv';a=Path(d)/'audit.json'
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
                def row(**kw):
                    val={'ReleaseDate':'2025-09-12','ReportTitle':'U.S. Feed Grain and Corn Supply and Use','Commodity':'Corn','Region':'United States','MarketYear':'2025/26','Attribute':'Ending Stocks','Value':'2100','Unit':'Million Bushels','ProjEstFlag':'Proj.'}
                    val.update(kw);w.writerow(val)
                row();row(Region='World');row(ProjEstFlag='Est.');row(ReleaseDate='2025-10-09',Value='2230')
            u='https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2026-10.csv'
            rep=imp.ingest(p,u,o,a)
            self.assertEqual(rep['rows_exported'],2)
            self.assertEqual(len(k32.load_csv(o)),2)
            self.assertEqual(k32.load_historical(o)['transitions'],1)
            self.assertIn('input_sha256',json.loads(a.read_text(encoding='utf-8')))

    def test_conflicting_duplicate_is_rejected(self):
        cols=['ReleaseDate','ReportTitle','Commodity','Region','MarketYear','Attribute','Value','Unit','ProjEstFlag']
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'usda.csv'
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
                for v in [100,200]:w.writerow({'ReleaseDate':'2025-09-12','ReportTitle':'U.S. Feed Grain and Corn Supply and Use','Commodity':'Corn','Region':'United States','MarketYear':'2025/26','Attribute':'Ending Stocks','Value':v,'Unit':'Million Bushels','ProjEstFlag':'Proj.'})
            with self.assertRaisesRegex(ValueError,'Conflicting'):
                imp.ingest(p,'https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2026-10.csv',Path(d)/'output.csv',Path(d)/'audit.json')

if __name__=='__main__':unittest.main()

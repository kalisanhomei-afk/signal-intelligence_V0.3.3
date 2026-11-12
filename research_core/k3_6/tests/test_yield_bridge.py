"""Offline reproducibility and anti-leakage checks for K3.6."""
import csv
import io
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import yield_bridge as k36


class TestK36(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=ROOT/'inputs'
        cls.fixed,cls.all_rows,cls.hashes=k36.build_data(cls.inputs)

    def test_expected_input_hashes(self):
        self.assertEqual(self.hashes['k341_fixed_21'], k36.EXPECTED_SHA['exploratory_fixed_cohort.csv'])

    def test_fixed_cohort_size(self):
        self.assertEqual((len(self.fixed),len(self.all_rows)),(21,41))

    def test_four_marketing_years(self):
        self.assertEqual(sorted(set(r['marketing_year'] for r in self.fixed)),k36.COHORT_YEARS)

    def test_same_year_release_edges(self):
        for row in self.all_rows:
            self.assertLess(k36.utc(row['base_release_utc']),k36.utc(row['forecast_origin_utc']))
            self.assertLess(k36.utc(row['forecast_origin_utc']),k36.utc(row['target_release_utc']))

    def test_no_future_nass_in_fixed_cohort(self):
        for row in self.fixed:
            self.assertEqual(row['feature_status'],'ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY')
            self.assertFalse(row['pit_certified'])

    def test_yield_nonzero_counts(self):
        self.assertEqual(sum(abs(r['delta_yield_bu_acre'])>1e-7 for r in self.fixed),16)
        self.assertEqual(sum(abs(r['delta_yield_bu_acre'])>1e-7 for r in self.all_rows),19)

    def test_stock_flow_bridge_identity(self):
        for r in self.all_rows:
            computed=(r['delta_beginning_stocks_million_bushels']+
                      r['delta_production_million_bushels']+
                      r['delta_imports_million_bushels']-
                      r['delta_domestic_use_million_bushels']-
                      r['delta_exports_million_bushels']+
                      r['ex_post_stocks_accounting_residual'])
            self.assertAlmostEqual(computed,r['delta_ending_stocks_million_bushels'],places=6)

    def test_area_yield_bridge_identity(self):
        for r in self.all_rows:
            p=(r['ex_post_yield_effect_million_bushels']+
               r['ex_post_area_effect_million_bushels']+
               r['ex_post_interaction_effect_million_bushels']+
               r['ex_post_production_rounding_residual'])
            self.assertAlmostEqual(p,r['delta_production_million_bushels'],places=3)

    def test_reference_oct_nov_2026(self):
        record=next(r for r in self.fixed if r['base_release_utc'].startswith('2026-10-09'))
        self.assertAlmostEqual(record['delta_yield_bu_acre'],-1.6)
        self.assertEqual(record['delta_production_million_bushels'],-141)
        self.assertEqual(record['delta_exports_million_bushels'],-25)
        self.assertEqual(record['delta_domestic_use_million_bushels'],-25)
        self.assertEqual(record['delta_ending_stocks_million_bushels'],-91)

    def test_irregular_report_interval_is_explicit(self):
        irregular=[r for r in self.all_rows if r['irregular_release_gap_over_45_days']]
        self.assertEqual(len(irregular),1)
        self.assertEqual(irregular[0]['marketing_year'],'2025/26')
        self.assertGreater(irregular[0]['observed_release_gap_days'],63)

    def test_2023_area_counterexample(self):
        r=next(r for r in self.fixed if r['base_release_utc'].startswith('2023-06-09'))
        self.assertLess(r['delta_yield_bu_acre'],0)
        self.assertGreater(r['delta_production_million_bushels'],0)

    def test_frozen_hash_tamper_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'exploratory_fixed_cohort.csv'
            p.write_bytes((self.inputs/'exploratory_fixed_cohort.csv').read_bytes()+b'\nINVALID\n')
            with self.assertRaisesRegex(ValueError,'FROZEN_HASH_MISMATCH'):
                k36.read_frozen(p,k36.EXPECTED_SHA['exploratory_fixed_cohort.csv'],21)

    def test_refuses_naive_datetime(self):
        with self.assertRaisesRegex(ValueError,'Naive datetime'):
            k36.utc('2026-09-01T15:00:00')

    def test_refuses_future_nass(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Frozen source is validated before edits; direct transition enforces timing.
            import zipfile
            rows,_=k36.read_frozen(self.inputs/'exploratory_fixed_cohort.csv',
                                     k36.EXPECTED_SHA['exploratory_fixed_cohort.csv'],21)
            w,_=k36.read_frozen(self.inputs/'wasde_corn_balance.csv',
                                 k36.EXPECTED_SHA['wasde_corn_balance.csv'],46)
            by={(v['release_date'],v['marketing_year']):v for v in w}
            a=dict(rows[0]);a['selected_nass_usable_after_utc']='2030-01-01T00:00:00Z'
            with self.assertRaisesRegex(ValueError,'FUTURE_NASS_FEATURE'):
                k36.transition(a,by)

    def test_refuses_target_mismatch(self):
        rows,_=k36.read_frozen(self.inputs/'exploratory_fixed_cohort.csv',
                                 k36.EXPECTED_SHA['exploratory_fixed_cohort.csv'],21)
        w,_=k36.read_frozen(self.inputs/'wasde_corn_balance.csv',
                             k36.EXPECTED_SHA['wasde_corn_balance.csv'],46)
        by={(v['release_date'],v['marketing_year']):v for v in w}
        a=dict(rows[0]);a['target_ending_stocks']='99999'
        with self.assertRaisesRegex(ValueError,'TARGET_STOCKS_DISAGREE'):
            k36.transition(a,by)

    def test_ridge_predicts_finite(self):
        m=k36.train_ridge(self.fixed[:6]);p=k36.predict_ridge(m,self.fixed[6]);self.assertTrue(math.isfinite(p))

    def test_15_predictions_and_three_folds(self):
        pred,trace,metrics,allmetrics=k36.walk_forward(self.fixed)
        self.assertEqual([r['train_n'] for r in trace],[6,12,16])
        self.assertEqual([r['test_n'] for r in trace],[6,4,5])
        self.assertEqual(len(pred),15)
        self.assertEqual(len(metrics),9)

    def test_yield_persistence_baseline(self):
        *_,metrics=k36.walk_forward(self.fixed)
        self.assertAlmostEqual(metrics['A']['mae'],1.526667,places=5)

    def test_no_pit_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=k36.run(self.inputs,Path(tmp))
            self.assertFalse(report['pit_certified'])
            self.assertEqual(report['status'],k36.STATUS)
            self.assertEqual(set(k36.OUTPUTS),set(p.name for p in Path(tmp).iterdir()))

    def test_rerun_identical_outputs(self):
        with tempfile.TemporaryDirectory() as x,tempfile.TemporaryDirectory() as y:
            k36.run(self.inputs,Path(x));k36.run(self.inputs,Path(y))
            for name in k36.OUTPUTS:
                self.assertEqual((Path(x)/name).read_bytes(),(Path(y)/name).read_bytes())


if __name__=='__main__':unittest.main()

import copy
import csv
import io
import json
import math
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import walk_forward as w

HERE=Path(__file__).resolve().parents[1]
INPUT=HERE/'inputs/exploratory_fixed_cohort.csv'
SOURCE=HERE/'inputs/k341_source_review.json'

class FrozenInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.obs,cls.sha=w.load_cohort(INPUT)

    def make_mutated(self,mutator):
        raw=INPUT.read_bytes().decode('utf-8-sig')
        rec=list(csv.DictReader(io.StringIO(raw)))
        mutator(rec)
        out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=list(rec[0]));writer.writeheader();writer.writerows(rec)
        return out.getvalue().encode()

    def load_modified(self, data):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.csv'; p.write_bytes(data)
            return w.load_cohort(p,frozen_sha='')

    def test_expected_frozen_checksum(self): self.assertEqual(self.sha,w.FROZEN_SHA256_CANONICAL)
    def test_21_rows(self): self.assertEqual(len(self.obs),21)
    def test_cohort_counts(self):
        self.assertEqual({y:sum(o.marketing_year==y for o in self.obs) for y in {'2023/24','2024/25','2025/26','2026/27'}},
                         {'2023/24':6,'2024/25':6,'2025/26':4,'2026/27':5})
    def test_all_asof(self):
        for o in self.obs:
            self.assertLessEqual(w.parse_utc(o.nass_usable),w.parse_utc(o.origin))
            self.assertLess(w.parse_utc(o.origin),w.parse_utc(o.target_release))
    def test_all_not_pit_certified(self): self.assertTrue(all(not o.pit_certified for o in self.obs))
    def test_raw_input_line_ending_normalization(self):
        a=INPUT.read_bytes()
        normalized=w.normalized_bytes(a)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'normalized.csv';p.write_bytes(normalized)
            obs,sha=w.load_cohort(p)
            self.assertEqual(len(obs),21);self.assertEqual(sha,self.sha)
    def test_tampering_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'changed.csv';p.write_bytes(INPUT.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'FROZEN_INPUT_HASH_MISMATCH'):
                w.load_cohort(p)
    def test_wrong_delta_rejected(self):
        mutated=self.make_mutated(lambda rec: rec[0].__setitem__('target_delta_million_bushels','12345'))
        with self.assertRaisesRegex(ValueError,'Delta inconsistency'):self.load_modified(mutated)
    def test_future_nass_rejected(self):
        mutated=self.make_mutated(lambda rec:rec[0].__setitem__('selected_nass_usable_after_utc','2035-01-01T00:00:00Z'))
        with self.assertRaisesRegex(ValueError,'RELEASE_ORDER_OR_ASOF_VIOLATION'):self.load_modified(mutated)
    def test_claimed_pit_certified_rejected(self):
        mutated=self.make_mutated(lambda rec:rec[0].__setitem__('pit_certified','true'))
        with self.assertRaisesRegex(ValueError,'claims PIT certification'):self.load_modified(mutated)
    def test_duplicate_origin_rejected(self):
        mutated=self.make_mutated(lambda rec: rec[1].update(rec[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate forecast origin'):self.load_modified(mutated)

class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        obs,_=w.load_cohort(INPUT)
        cls.obs=obs
        cls.pred,cls.trace,cls.mets=w.run_backtest(obs)
    def test_15_test_rows(self):self.assertEqual(len(self.pred),15)
    def test_locked_baseline_mae(self):self.assertEqual(self.mets['overall']['A']['mae'],115.2)
    def test_training_counts(self):self.assertEqual([x['n_train'] for x in self.trace],[6,12,16])
    def test_test_year_counts(self):self.assertEqual([x['n_test'] for x in self.trace],[6,4,5])
    def test_predictions_are_finite(self):
        for p in self.pred:
            for m in ['A','B','C']:self.assertTrue(math.isfinite(float(p['predict_delta_'+m])))
    def test_mean_model_uses_training_only(self):
        for t in self.trace:
            train=[o.delta for o in self.obs if w.year_start(o.marketing_year)<w.year_start(t['held_out_marketing_year'])]
            self.assertAlmostEqual(t['B_mean_historical_delta'],sum(train)/len(train),places=5)
    def test_no_heldout_label_leakage(self):
        for t in self.trace:
            self.assertLess(w.parse_utc(t['max_train_label_release']),w.parse_utc(t['min_test_origin']))
    def test_ridge_no_training_labels_from_holdout(self):
        train=[o for o in self.obs if o.marketing_year=='2023/24']
        base=w.train_ridge(train)
        extended=copy.copy(train)
        test=[o for o in self.obs if o.marketing_year=='2024/25'][0]
        score1=w.predict_ridge(base,test)
        altered=replace(test,delta=1e9)
        score2=w.predict_ridge(base,altered)
        self.assertAlmostEqual(score1,score2)
    def test_alpha_preset(self):
        with self.assertRaisesRegex(ValueError,'Alpha'):w.train_ridge(self.obs[:6],alpha=0)
    def test_frozen_output_files(self):
        with tempfile.TemporaryDirectory() as d:
            o=Path(d);review=w.run(INPUT,SOURCE,o)
            self.assertEqual(review['heldout_rows'],15)
            self.assertEqual(review['certified_pit_records'],0)
            self.assertFalse(review['pit_certified'])
            self.assertEqual(len(list(o.iterdir())),5)
            for fn in ['review.html','review.json','predictions.csv','training_trace.csv','year_metrics.csv']:
                self.assertGreater((o/fn).stat().st_size,100)
    def test_source_status_guard(self):
        with tempfile.TemporaryDirectory() as d:
            r=json.loads(SOURCE.read_text());r['pit_independently_certified']=127
            j=Path(d)/'source.json';j.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'source data quality'):w.run(INPUT,j,Path(d)/'out')
    def test_three_years_evaluated(self):
        self.assertEqual(list(self.mets['by_marketing_year']),['2024/25','2025/26','2026/27'])

if __name__=='__main__':unittest.main()

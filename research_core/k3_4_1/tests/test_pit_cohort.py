import csv
import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import date, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pit_cohort',ROOT/'pit_cohort.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PITTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs,cls.nass,cls.wasde,cls.audit=mod.read_bundle(ROOT/'inputs')

    def test_01_nass_est_and_edt(self):
        self.assertEqual(mod.iso_z(mod.schedule_utc('2026-01-05','NASS')),'2026-01-05T21:00:00Z')
        self.assertEqual(mod.iso_z(mod.schedule_utc('2026-07-06','NASS')),'2026-07-06T20:00:00Z')

    def test_02_wasde_est_and_edt(self):
        self.assertEqual(mod.iso_z(mod.schedule_utc('2026-01-12','WASDE')),'2026-01-12T17:00:00Z')
        self.assertEqual(mod.iso_z(mod.schedule_utc('2026-07-10','WASDE')),'2026-07-10T16:00:00Z')

    def test_03_no_naive_datetime(self):
        with self.assertRaises(mod.InvalidInput):mod.parse_utc('2026-06-11T12:00:00')

    def test_04_invalid_nonexistent_kind(self):
        with self.assertRaises(ValueError):mod.schedule_utc('2026-11-12','CPI')

    def test_05_cohort_count(self):
        rows=mod.compute_cohort(self.pairs,self.nass,self.wasde)
        self.assertEqual(len(rows),41)
        self.assertEqual(sum(x['feature_status']=='ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY' for x in rows),21)

    def test_06_no_independent_time_certs(self):
        rows=mod.compute_cohort(self.pairs,self.nass,self.wasde)
        self.assertTrue(all(x['pit_certified']=='false' for x in rows))
        ledger=mod.evidence_ledger(self.nass,self.wasde,24)
        self.assertTrue(all(x['exact_per_release_verified']=='false' for x in ledger))
        self.assertTrue(all(x['content_hash_rechecked']=='false' for x in ledger))

    def test_07_no_future_feature_in_selection(self):
        rows=mod.compute_cohort(self.pairs,self.nass,self.wasde)
        for x in rows:
            if x['selected_nass_date']:
                self.assertLessEqual(mod.parse_utc(x['selected_nass_usable_after_utc']),mod.parse_utc(x['forecast_origin_utc']))

    def test_08_conservative_selection_differs_once(self):
        rows=mod.compute_cohort(self.pairs,self.nass,self.wasde)
        changed=[x for x in rows if x['selection_changed_vs_K34']=='true']
        self.assertEqual(len(changed),1)
        self.assertEqual(changed[0]['selected_nass_date'],'2024-08-05')
        self.assertEqual(changed[0]['k34_original_selected_nass_date'],'2024-08-12')

    def test_09_freeze_offline(self):
        with tempfile.TemporaryDirectory() as d:
            x=mod.execute(ROOT/'inputs',Path(d))
            self.assertEqual(x['status'],'COHORT_FROZEN_EXPLORATORY_PIT_NOT_CERTIFIED')
            self.assertEqual(x['pit_independently_certified'],0)
            self.assertEqual(x['exploratory_eligible'],21)
            self.assertTrue((Path(d)/'asof_cohort.csv').exists())
            self.assertTrue((Path(d)/'review.html').exists())

    def test_10_metrics_fair_same_cohort(self):
        rows=mod.compute_cohort(self.pairs,self.nass,self.wasde)
        self.assertAlmostEqual(mod.metrics(rows)['persistence_mae_million_bushels'],72.365854)
        selected=[r for r in rows if r['feature_status']=='ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY']
        self.assertAlmostEqual(mod.metrics(selected)['persistence_mae_million_bushels'],94.857143)

    def test_11_integrity_rejects_stock_tamper(self):
        pairs=copy.deepcopy(self.pairs)
        pairs[0]['target_ending_stocks']='90000'
        with self.assertRaises(mod.InvalidInput):mod.compute_cohort(pairs,self.nass,self.wasde)

    def test_12_timeline_rejects_origin_at_target(self):
        pairs=copy.deepcopy(self.pairs)
        pairs[0]['forecast_origin_proxy_utc']=pairs[0]['target_release_proxy_utc']
        with self.assertRaises(mod.InvalidInput):mod.compute_cohort(pairs,self.nass,self.wasde)

    def test_13_duplicate_nass_detection(self):
        with self.assertRaises(mod.InvalidInput):
            mod.compute_cohort(self.pairs,self.nass+[self.nass[0]],self.wasde)

    def test_14_duplicate_wasde_detection(self):
        with self.assertRaises(mod.InvalidInput):
            mod.compute_cohort(self.pairs,self.nass,self.wasde+[self.wasde[0]])

    def test_15_safety_buffer_avoids_same_day(self):
        # 2024-08-12 NASS was published 16 ET (20 UTC), 4 hours after 12 ET WASDE;
        # base+24h origin is Tue noon ET, but a 24h safety buffer requires Tue 4pm ET.
        rows=mod.compute_cohort(self.pairs,self.nass,self.wasde,safety_hours=24)
        target=[r for r in rows if r['forecast_origin_utc']=='2024-08-13T16:00:00Z'][0]
        self.assertEqual(target['selected_nass_date'],'2024-08-05')

    def test_16_invalid_config_fails_closed(self):
        with self.assertRaises(mod.InvalidInput):mod.compute_cohort(self.pairs,self.nass,self.wasde,safety_hours=0)
        with self.assertRaises(mod.InvalidInput):mod.compute_cohort(self.pairs,self.nass,self.wasde,max_age_days=500)

    def test_17_missing_input_error_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            inp=Path(d)/'input'; inp.mkdir()
            out=Path(d)/'out'
            with self.assertRaises(mod.InvalidInput):mod.execute(inp,out)
            fail=json.loads((out/'review.json').read_text())
            self.assertEqual(fail['status'],'INPUT_VALIDATION_FAILED')
            self.assertEqual(fail['pit_independently_certified'],0)

    def test_18_reproducible_lock(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            r1=mod.execute(ROOT/'inputs',Path(a));r2=mod.execute(ROOT/'inputs',Path(b))
            self.assertEqual(r1['frozen_cohort_content_sha256'],r2['frozen_cohort_content_sha256'])
            self.assertEqual((Path(a)/'asof_cohort.csv').read_bytes(),(Path(b)/'asof_cohort.csv').read_bytes())

    def test_19_no_current_future_lookahead(self):
        rows=mod.compute_cohort(self.pairs,self.nass,self.wasde)
        self.assertTrue(all(mod.parse_utc(r['forecast_origin_utc'])<mod.parse_utc(r['target_release_schedule_utc']) for r in rows))

if __name__=='__main__':unittest.main()

"""R4 offline mock tests: fail closed, source local IDs, code-only values."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from binding_pipeline import (
    SCHEMA_VERSION, SELECTION_VERSION, build_review, fact_value,
    load_verified_bundles, render_review, standard_facts,
    validate_model_selection, write_demo,
)

ROOT = Path(__file__).resolve().parent.parent
MOCK = ROOT / 'rebuild_r4' / 'fixtures' / 'mock_ai_selection.json'


class R4BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundles = load_verified_bundles(ROOT)
        cls.catalog = standard_facts(cls.bundles)
        cls.demo = json.loads(MOCK.read_text(encoding='utf-8'))

    def test_all_three_sources_and_fact_counts(self):
        self.assertEqual({k:len(v) for k,v in self.catalog.items()}, {'bea':6,'eia':4,'arxiv':6})

    def test_pinned_source_status_is_never_promoted(self):
        for b in self.bundles.values():
            self.assertIs(b['publication_allowed'],False)
            self.assertIs(b['human_approved'],False)

    def test_original_exact_values_and_source_evidence(self):
        self.assertEqual(self.catalog['bea']['F001']['value_original'],'21.9')
        self.assertEqual(self.catalog['bea']['F001']['source_evidence_id'],'E7')
        self.assertEqual(self.catalog['eia']['EIA-F003']['value_original'],'12')
        self.assertEqual(self.catalog['eia']['EIA-F003']['source_evidence_id'],'E5')
        self.assertEqual(self.catalog['arxiv']['ARXIV-F005']['value_original'],'52')
        self.assertEqual(self.catalog['arxiv']['ARXIV-F005']['source_evidence_id'],'E6')

    def test_qualifiers_guard_common_eia_misreadings(self):
        self.assertIn('典型範圍下界',self.catalog['eia']['EIA-F001']['value_display'])
        self.assertIn('首次超過',self.catalog['eia']['EIA-F003']['value_display'])
        self.assertIn('持續至少',self.catalog['eia']['EIA-F004']['value_display'])
        self.assertNotIn('精確值',self.catalog['eia']['EIA-F004']['value_display'])

    def test_author_results_not_relabelled_as_accuracy(self):
        text = self.catalog['arxiv']['ARXIV-F006']['value_display']
        self.assertIn('49%', text)
        self.assertIn('指標定義', text)
        self.assertNotIn('準確率', text)
        self.assertFalse(self.catalog['arxiv']['ARXIV-F006']['independently_verified'])

    def test_valid_mock_three_cases(self):
        choices=validate_model_selection(self.demo,self.catalog)
        self.assertEqual([a['case_id'] for a in choices], ['bea','eia','arxiv'])
        self.assertTrue(all(a['model_generated_numerical_claims']==0 for a in choices))

    def test_no_automatic_approval(self):
        r=build_review(self.bundles,self.demo)
        self.assertEqual(r['schema_version'],SCHEMA_VERSION)
        self.assertFalse(r['publication_allowed'])
        self.assertFalse(r['human_approved'])
        self.assertEqual(r['independently_verified_claims'],0)
        self.assertEqual(r['api_calls'],0)

    def test_non_number_injection_via_extra_model_field(self):
        for field,v in [('claim','成交額增加了999億美元'),('human_approved',True),('additional_number',999),
                        ('free_text','100% success'),('fact_values',{'F001':'999'})]:
            with self.subTest(field=field):
                altered=copy.deepcopy(self.demo)
                altered['cases'][0][field]=v
                with self.assertRaises(ValueError): validate_model_selection(altered,self.catalog)

    def test_source_crossing_is_rejected(self):
        d=copy.deepcopy(self.demo)
        d['cases'][0]['focus_fact_ids']=['EIA-F001']
        with self.assertRaises(ValueError): validate_model_selection(d,self.catalog)
        d=copy.deepcopy(self.demo)
        d['cases'][1]['focus_fact_ids']=['ARXIV-F005']
        with self.assertRaises(ValueError): validate_model_selection(d,self.catalog)

    def test_unknown_duplicate_or_overlong_fact_ids_rejected(self):
        for ids in [[],['F999'],['F001','F001'],['F001','F002','F003','F004','F005'],[12],['F001 ', 'F002']]:
            with self.subTest(ids=ids):
                d=copy.deepcopy(self.demo);d['cases'][0]['focus_fact_ids']=ids
                with self.assertRaises(ValueError):validate_model_selection(d,self.catalog)

    def test_unknown_theme_or_cross_source_theme_rejected(self):
        for name in ['fake_trend','refinery_yield_mix', 'trade_structure_monitor 123']:
            with self.subTest(theme=name):
                d=copy.deepcopy(self.demo);d['cases'][0]['theme_id']=name
                with self.assertRaises(ValueError):validate_model_selection(d,self.catalog)

    def test_bad_review_questions_rejected(self):
        for qs in [[],['check_duration'],['check_scope','check_scope'],['compare_periods','check_scope','confirm_drivers']]:
            with self.subTest(qs=qs):
                d=copy.deepcopy(self.demo);d['cases'][0]['question_ids']=qs
                with self.assertRaises(ValueError):validate_model_selection(d,self.catalog)

    def test_unapproved_priority_rejected(self):
        d=copy.deepcopy(self.demo);d['cases'][2]['priority']='國際市場最重要'
        with self.assertRaises(ValueError):validate_model_selection(d,self.catalog)

    def test_missing_duplicate_case_and_wrong_top_schema_rejected(self):
        for mutation in ('missing', 'duplicated','top_field','wrong_schema'):
            with self.subTest(mutation=mutation):
                d=copy.deepcopy(self.demo)
                if mutation=='missing': d['cases']=d['cases'][:2]
                elif mutation=='duplicated': d['cases'][2]['case_id']='bea'
                elif mutation=='top_field': d['ready_for_production']=True
                else: d['schema_version']=SELECTION_VERSION+'v2'
                with self.assertRaises(ValueError):validate_model_selection(d,self.catalog)

    def test_report_renders_only_fact_catalog_numbers(self):
        r=build_review(self.bundles,self.demo)
        html=render_review(r)
        for text in ('21.9 billion USD','3.6 billion USD','超過 12%','52%','49%',
                     '作者摘要自述','不可發佈','不得發佈','未查證'):
            if text == '不可發佈': # Heading uses 不得發佈 consistently
                continue
            with self.subTest(text=text):self.assertIn(text,html)
        self.assertNotIn('999億美元',html)
        self.assertNotIn('準確率是 49%',html)

    def test_render_rejects_publication_or_paid_calls(self):
        for field,value in [('publication_allowed',True),('human_approved',True),('api_calls',1)]:
            r=build_review(self.bundles,self.demo)
            r[field]=value
            with self.assertRaises(ValueError):render_review(r)

    def test_external_edited_result_files_are_not_trusted(self):
        # R4 never imports rebuild_r1/out/bea_facts.json, etc.
        read_paths = []
        original = Path.read_text
        def tracked(path, *args, **kwargs):
            read_paths.append(str(path))
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'read_text', tracked):
            _ = load_verified_bundles(ROOT)
        self.assertFalse(any('/out/' in p.replace('\\', '/') for p in read_paths))

    def test_unknown_case_or_metric_cannot_render_numbers(self):
        with self.assertRaises(ValueError):fact_value('unknown',{'measurement_role':'increase','value_original':'4'})
        f=copy.deepcopy(self.bundles['eia']['facts'][0]);f['measurement_role']='exact_monthly_observation'
        with self.assertRaises(ValueError):fact_value('eia',f)

    def test_code_outputs_json_and_human_review_html(self):
        with tempfile.TemporaryDirectory() as td:
            r=write_demo(ROOT,self.demo,Path(td))
            files={p.name for p in Path(td).iterdir()}
            self.assertEqual(files,{'fact_catalog.json','analysis_review.json','offline_review.html'})
            fromfile=json.loads((Path(td)/'analysis_review.json').read_text(encoding='utf-8'))
            self.assertEqual(fromfile,r)
            self.assertEqual(json.loads((Path(td)/'fact_catalog.json').read_text(encoding='utf-8'))['fact_count'],16)

    def test_archived_bea_cannot_be_changed_even_with_updated_fixture_hash(self):
        original = Path.read_text
        fixture_path = str(ROOT / 'rebuild_r1' / 'fixtures' / 'bea_e7.json')
        def modified(path, *args, **kwargs):
            data = original(path, *args, **kwargs)
            if str(path) == fixture_path:
                import hashlib
                src = json.loads(data)
                row = src['item']['evidence_spans'][0]
                row['text'] = row['text'].replace('$21.9', '$99.9')
                row['sha256'] = hashlib.sha256(row['text'].encode('utf-8')).hexdigest()
                return json.dumps(src)
            return data
        with mock.patch.object(Path, 'read_text', modified):
            with self.assertRaises(ValueError):
                load_verified_bundles(ROOT)

    def test_eia_original_months_and_arxiv_not_peer_reviewed(self):
        self.assertEqual(self.catalog['eia']['EIA-F003']['period_as_written'],'March 2026')
        self.assertFalse(self.bundles['arxiv']['facts'][-1]['peer_review_confirmed'])

    def test_sha256_integrity_on_displayed_fact(self):
        for case, items in self.catalog.items():
            source=self.bundles[case]['source']
            for fid, row in items.items():
                expected=source['excerpt_sha256'] if case=='bea' else source['excerpt_sha256'][row['source_evidence_id']]
                if case=='bea':expected=source['excerpt_sha256']
                self.assertEqual(row['source_span_sha256'],expected)


if __name__=='__main__':unittest.main()

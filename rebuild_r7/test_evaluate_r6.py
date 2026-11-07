#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import unittest
from evaluate_r6 import evaluate,render_html,ROOT

class EditorialGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=json.loads((ROOT/'fixtures/r6_live_result_sanitized.json').read_text(encoding='utf8'))
    def test_actual_r6_technical_but_no_editorial_go(self):
        r=evaluate(self.case)
        self.assertTrue(r['r6_technical_pass'])
        self.assertFalse(r['r7_editorial_quality_pass'])
        self.assertFalse(r['publication_allowed'])
        self.assertEqual(r['facts_selected'],4)
    def test_period_not_present(self):
        r=evaluate(self.case);self.assertEqual(set(r['facts_missing_period']),set(self.case['focus_fact_ids']))
    def test_scope_unresolved(self):
        r=evaluate(self.case);self.assertEqual(r['facts_scope_unresolved'],['F005','F006'])
    def test_mismatched_fact_reference_rejected(self):
        d=copy.deepcopy(self.case);d['focus_fact_ids']=['F001']
        with self.assertRaisesRegex(ValueError,'fact_list_does_not_match_focus_ids'):evaluate(d)
    def test_cannot_autopublish(self):
        d=copy.deepcopy(self.case);d['publication_allowed']=True
        with self.assertRaisesRegex(ValueError,'unsafe_publication_state'):evaluate(d)
    def test_no_new_numeric_claims_is_required_for_technical(self):
        d=copy.deepcopy(self.case);d['model_generated_numerical_claims']=1
        self.assertFalse(evaluate(d)['r6_technical_pass'])
    def test_provenance_missing_is_not_a_technical_pass(self):
        d=copy.deepcopy(self.case);d['facts'][0]['source_evidence_id']=''
        self.assertFalse(evaluate(d)['r6_technical_pass'])
    def test_duplicate_ids_rejected(self):
        d=copy.deepcopy(self.case);d['focus_fact_ids'][1]=d['focus_fact_ids'][0]
        with self.assertRaisesRegex(ValueError,'fact_ids_invalid'):evaluate(d)
    def test_html_no_github_api_or_external_asset(self):
        d=copy.deepcopy(self.case)
        rendered=render_html(evaluate(d),d)
        self.assertIn('正式發佈：NO-GO',rendered)
        self.assertIn('publication_allowed:false',rendered)
        self.assertNotIn('fetch(',rendered)
        self.assertNotIn('script src=',rendered)
    def test_missing_human_review_is_no_go(self):
        r=evaluate(self.case)
        self.assertFalse(next(c for c in r['checks'] if c['code']=='human_signoff')['passed'])

if __name__=='__main__':unittest.main()

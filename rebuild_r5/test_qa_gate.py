"""R5 adversarial cases. All offline, no API and no writes to original R1-R4 files."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest import mock

from qa_gate import (
    GATE_VERSION, MAX_SELECTION_BYTES, PreflightError, check_pins, normalized_digest,
    parse_selection, qa_html, run_case,
)

ROOT = Path(__file__).resolve().parent.parent
SELECTION = ROOT/'rebuild_r4/fixtures/mock_ai_selection.json'


class R5OfflineQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SELECTION.read_bytes()
        cls.doc = parse_selection(cls.raw)

    def assert_refuses(self, value):
        with self.assertRaises(PreflightError):
            run_case(ROOT,json.dumps(value,ensure_ascii=False).encode('utf-8'))

    def test_pinned_archived_sources(self):
        hashes=check_pins(ROOT)
        self.assertEqual(len(hashes),8)
        self.assertEqual(hashes['rebuild_r4/fixtures/mock_ai_selection.json'],normalized_digest(SELECTION))

    def test_known_good_three_sources(self):
        facts,review,page=run_case(ROOT,self.raw)
        self.assertEqual(sum(map(len,facts.values())),16)
        self.assertEqual(len(review['cases']),3)
        self.assertIn('BEA',page)
        self.assertIn('EIA',page)
        self.assertIn('arXiv',page)

    def test_deterministic_replay(self):
        a,b,page1=run_case(ROOT,self.raw)
        aa,bb,page2=run_case(ROOT,self.raw)
        self.assertEqual(a,aa)
        self.assertEqual(b,bb)
        self.assertEqual(page1,page2)

    def test_malformed_json(self):
        for bad in (b'',b'{',b'null',b'[]',b'NaN',b'{"a":Infinity}',b'\xff\x00'):
            with self.subTest(payload=bad[:20]):
                with self.assertRaises(PreflightError):parse_selection(bad)

    def test_duplicate_object_keys_rejected(self):
        for bad in (b'{"schema_version":"x","schema_version":"x","cases":[]}',
                    b'{"cases":[{"case_id":"bea","case_id":"eia"}]}'):
            with self.subTest(bad=bad):
                with self.assertRaises(PreflightError):parse_selection(bad)

    def test_oversize_selection_rejected(self):
        with self.assertRaises(PreflightError):parse_selection(b' '* (MAX_SELECTION_BYTES+1))

    def test_extra_model_generated_numbers_rejected(self):
        for name,value in [('additional_amount',999.5),('free_text','9 billion'),
                           ('current_value','999'),('verified',True),('facts',{'F001':99})]:
            x=copy.deepcopy(self.doc);x['cases'][0][name]=value
            with self.subTest(name=name):self.assert_refuses(x)

    def test_cross_source_number_and_fact_reference(self):
        for badid in ('EIA-F001','ARXIV-F005','F999'):
            x=copy.deepcopy(self.doc);x['cases'][0]['focus_fact_ids']=[badid]
            with self.subTest(id=badid):self.assert_refuses(x)

    def test_reject_duplicate_and_missing_ids(self):
        for ids in ([],['F001','F001'],['F001']*5):
            x=copy.deepcopy(self.doc);x['cases'][0]['focus_fact_ids']=ids
            with self.subTest(ids=ids):self.assert_refuses(x)

    def test_reject_unhashable_and_wrong_types_fail_closed(self):
        for name,value in [('case_id',['bea']),('priority',{'a':1}),
                           ('focus_fact_ids',[{'a':'F001'}]),('theme_id',['trade_structure_monitor']),
                           ('question_ids',[['check_scope']])]:
            x=copy.deepcopy(self.doc);x['cases'][0][name]=value
            with self.subTest(field=name):self.assert_refuses(x)

    def test_reject_missing_and_extra_cases(self):
        for mode in ('missing','extra','duplicate'):
            x=copy.deepcopy(self.doc)
            if mode=='missing':x['cases'].pop()
            elif mode=='extra':x['cases'].append(copy.deepcopy(x['cases'][0]))
            else:x['cases'][1]['case_id']='bea'
            with self.subTest(mode=mode):self.assert_refuses(x)

    def test_reject_cross_source_theme(self):
        x=copy.deepcopy(self.doc);x['cases'][0]['theme_id']='refinery_yield_mix'
        self.assert_refuses(x)

    def test_reject_fake_priority_and_approval(self):
        for name,value in [('priority','重要經濟決策'),('human_approved',True),
                           ('publication_allowed',True)]:
            x=copy.deepcopy(self.doc);x['cases'][0][name]=value
            with self.subTest(name=name):self.assert_refuses(x)

    def test_html_injection_refused(self):
        x=copy.deepcopy(self.doc)
        x['cases'][0]['theme_id']='<script>alert(1)</script>'
        self.assert_refuses(x)

    def test_source_snapshot_modify_rejected(self):
        # Create a minimal copy; the user's R1-R4 remains unchanged.
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)
            for d in ('rebuild_r1','rebuild_r2','rebuild_r3','rebuild_r4'):
                shutil.copytree(ROOT/d,target/d,ignore=shutil.ignore_patterns('__pycache__','out','*.pyc'))
            for path,needle,replacement in [
                ('rebuild_r1/fixtures/bea_e7.json',b'21.9',b'99.9'),
                ('rebuild_r2/fixtures/eia_yields_e2_e5.json',b'12',b'15'),
                ('rebuild_r3/fixtures/arxiv_mesa_abstract_e1_e6.json',b'52',b'92'),
            ]:
                fp=target/path
                before=fp.read_bytes()
                self.assertIn(needle,before)
                fp.write_bytes(before.replace(needle,replacement,1))
                with self.subTest(path=path):
                    with self.assertRaisesRegex(PreflightError,'drift_detected'):
                        check_pins(target)
                fp.write_bytes(before)

    def test_r4_code_drift_detected(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            for name in ('rebuild_r1','rebuild_r2','rebuild_r3','rebuild_r4'):
                shutil.copytree(ROOT/name,base/name,ignore=shutil.ignore_patterns('__pycache__','out'))
            p=base/'rebuild_r4/binding_pipeline.py'
            p.write_bytes(p.read_bytes()+b'\n# unauthorized drift\n')
            with self.assertRaisesRegex(PreflightError,'drift_detected'):
                check_pins(base)

    def test_tampered_generated_out_not_used(self):
        # Raise immediately if R5 or R4 ever trusts an editable generated out/*.json.
        original_read = Path.read_text
        def deny_cached_output(path, *args, **kwargs):
            self.assertNotIn('/out/',str(path).replace('\\','/'))
            return original_read(path, *args, **kwargs)
        with mock.patch.object(Path, 'read_text', deny_cached_output):
            facts,_,_=run_case(ROOT,self.raw)
        self.assertEqual(facts['bea']['F001']['value_original'],'21.9')

    def test_no_network_dependency(self):
        with mock.patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            _,review,_=run_case(ROOT,self.raw)
        self.assertEqual(review['api_calls'],0)

    def test_no_api_no_automatic_approval(self):
        _,review,_=run_case(ROOT,self.raw)
        self.assertIs(review['publication_allowed'],False)
        self.assertIs(review['human_approved'],False)
        self.assertEqual(review['independently_verified_claims'],0)
        self.assertTrue(all(c['model_generated_numerical_claims']==0 for c in review['cases']))

    def test_eia_threshold_and_arxiv_claim_limitations(self):
        facts,_,_=run_case(ROOT,self.raw)
        self.assertIn('不是精確測值',facts['eia']['EIA-F003']['value_display'])
        self.assertIn('不是當月實測值',facts['eia']['EIA-F001']['value_display'])
        self.assertIn('作者摘要自述',facts['arxiv']['ARXIV-F005']['value_display'])
        self.assertNotIn('準確率',facts['arxiv']['ARXIV-F005']['value_display'])

    def test_qa_html_marks_development_not_validated(self):
        page=qa_html({'decision':'OFFLINE_PASS_R6_CANDIDATE','total_tests':1,'fact_count':16,
                      'suites':[{'suite':'R5','tests_run':1,'status':'PASS'}],
                      'replay_status':'PASS','pinned_status':'PASS'})
        self.assertIn('不可發布',page)
        self.assertIn('未執行 OpenAI API',page)
        self.assertIn('R7',page)


if __name__ == '__main__':
    unittest.main()

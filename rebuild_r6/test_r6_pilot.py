"""R6 contract tests: all local, no network, no API billing."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE))
import r6_pilot as r6
R4,R5=r6._load_dependencies(ROOT)


def fixture_selection():
    return json.loads((ROOT/'rebuild_r4/fixtures/mock_ai_selection.json').read_text(encoding='utf-8'))['cases'][0]


def response_of(selection):
    return {'id':'resp_mock_unit_test', 'status':'completed', 'output':[
        {'type':'message','content':[{'type':'output_text','text':json.dumps(selection,ensure_ascii=False)}]}
    ],'usage':{'input_tokens':42,'output_tokens':31,'total_tokens':73}}


class R6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundles=R4.load_verified_bundles(ROOT)
        cls.catalog=R4.standard_facts(cls.bundles)
        cls.bea=fixture_selection()

    def test_schema_is_strict_only_enums_and_ids(self):
        schema=r6.model_schema(list(self.catalog['bea']))
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']),set(r6.BEA_FIELDS))
        self.assertEqual(schema['properties']['case_id']['enum'],['bea'])

    def test_payload_spec_json_schema_correct(self):
        payload=r6.build_request(self.catalog['bea'],'September trade excerpt')
        self.assertEqual(payload['model'],r6.MODEL)
        self.assertIs(payload['store'],False)
        self.assertEqual(payload['text']['format']['type'],'json_schema')
        self.assertTrue(payload['text']['format']['strict'])
        self.assertNotIn('authorization',str(payload).lower())

    def test_good_selection(self):
        out=r6.validate_selection(self.bea,self.catalog,R4,ROOT)
        self.assertEqual(out['focus_fact_ids'],['F001','F002'])

    def test_cross_source_and_unknown_fact_refused(self):
        for bad in ['EIA-F001','ARXIV-F005','F999']:
            sel=copy.deepcopy(self.bea)
            sel['focus_fact_ids']=[bad]
            with self.subTest(bad=bad), self.assertRaises(r6.R6Error):
                r6.validate_selection(sel,self.catalog,R4,ROOT)

    def test_added_model_generated_prose_or_number_rejected(self):
        for extra,value in [('claim','貿易逆差999億'),('amount','3.6'),('publish',True),('editorial',{'note':'guess'})]:
            sel=copy.deepcopy(self.bea)
            sel[extra]=value
            with self.subTest(extra=extra),self.assertRaises(r6.R6Error):
                r6.validate_selection(sel,self.catalog,R4,ROOT)

    def test_invalid_case_and_theme_rejected(self):
        sel=copy.deepcopy(self.bea)
        sel['case_id']='eia'
        with self.assertRaises(r6.R6Error):r6.validate_selection(sel,self.catalog,R4,ROOT)
        sel=copy.deepcopy(self.bea)
        sel['theme_id']='fuel_price_risk'
        with self.assertRaises(r6.R6Error):r6.validate_selection(sel,self.catalog,R4,ROOT)

    def test_duplicate_and_overlength_fact_ids_rejected(self):
        for vals in [['F001','F001'],[],['F001','F002','F003','F004','F005']]:
            sel=copy.deepcopy(self.bea)
            sel['focus_fact_ids']=vals
            with self.subTest(ids=vals),self.assertRaises(r6.R6Error):
                r6.validate_selection(sel,self.catalog,R4,ROOT)

    def test_response_parser_refusal(self):
        refused={'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'No'}]}]}
        with self.assertRaises(r6.R6Error):r6.parse_model_response(refused)

    def test_response_parser_incomplete(self):
        wrong=response_of(self.bea)
        wrong['status']='incomplete'
        with self.assertRaises(r6.R6Error):r6.parse_model_response(wrong)

    def test_response_parser_duplicate_json_key(self):
        resp={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"case_id":"bea","case_id":"bea"}'}]}]}
        with self.assertRaises(r6.R6Error):r6.parse_model_response(resp)

    def test_response_parser_good(self):
        self.assertEqual(r6.parse_model_response(response_of(self.bea)),self.bea)

    def test_response_parser_multiple_blocks_rejected(self):
        resp=response_of(self.bea)
        resp['output'][0]['content'].append(copy.deepcopy(resp['output'][0]['content'][0]))
        with self.assertRaises(r6.R6Error):r6.parse_model_response(resp)

    def test_report_all_numbers_from_catalog(self):
        report=r6.make_report(self.bundles,self.catalog,self.bea,R4,live=True,response=response_of(self.bea),root=ROOT)
        self.assertEqual(report['api_calls_attempted'],1)
        self.assertEqual(report['independent_confirmations'],0)
        self.assertIs(report['publication_allowed'],False)
        self.assertEqual(report['facts'][0]['value_original'],'21.9')
        self.assertEqual(report['model_generated_numerical_claims'],0)
        html_doc=r6.render_html(report)
        self.assertIn('21.9 billion USD',html_doc)
        self.assertNotIn('999億',html_doc)

    def test_report_publication_forbidden(self):
        report=r6.make_report(self.bundles,self.catalog,self.bea,R4,live=False,response=None,root=ROOT)
        report['publication_allowed']=True
        with self.assertRaises(r6.R6Error):r6.render_html(report)

    def test_api_http_error_sanitized(self):
        from urllib.error import HTTPError
        def fake_opener(*args,**kwargs):
            raise HTTPError('https://api.openai.com/v1/responses',401,'Secret:sk-sensitive',None,None)
        with self.assertRaises(r6.R6Error) as cm:
            r6._request_once({},'sk-sensitive',opener=fake_opener)
        self.assertEqual(str(cm.exception),'api_http_401')

    def test_dry_run_never_calls_api(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(R5,'run_gate',return_value={'decision':'OFFLINE_PASS_R6_CANDIDATE'}):
            def cannot_call(*args,**kwargs):
                raise AssertionError('offline_must_not_send_network')
            result=r6.run(ROOT,Path(td),live=False,api_request=cannot_call)
            self.assertEqual(result['api_calls_attempted'],0)
            self.assertEqual(result['status'],'OFFLINE_MOCK_ONLY')

    def test_live_calls_api_exactly_once(self):
        calls=[]
        def fake_request(payload,key):
            calls.append((payload,key))
            return response_of(self.bea)
        with tempfile.TemporaryDirectory() as td, mock.patch.object(R5,'run_gate',return_value={'decision':'OFFLINE_PASS_R6_CANDIDATE'}):
            result=r6.run(ROOT,Path(td),live=True,api_key='sk-mock-unit-test',api_request=fake_request,require_approval=False)
            self.assertEqual(len(calls),1)
            self.assertEqual(result['api_calls_attempted'],1)
            self.assertEqual(result['status'],'TECHNICAL_SMOKE_PASSED_HUMAN_REVIEW_REQUIRED')
            txt=(Path(td)/'r6_result.json').read_text(encoding='utf-8')
            self.assertNotIn('sk-mock-unit-test',txt)
            self.assertTrue((Path(td)/'r6_review.html').exists())

    def test_r5_blocked_no_api(self):
        called=[]
        with tempfile.TemporaryDirectory() as td,mock.patch.object(R5,'run_gate',return_value={'decision':'BLOCKED_NO_R6'}):
            with self.assertRaises(r6.R6Error):
                r6.run(ROOT,Path(td),live=True,api_key='sk-mock',api_request=lambda *_:called.append('called'),require_approval=False)
            self.assertEqual(called,[])
            data=json.loads((Path(td)/'r6_result.json').read_text(encoding='utf-8'))
            self.assertEqual(data['api_calls_attempted'],0)

    def test_missing_key_no_api(self):
        called=[]
        with tempfile.TemporaryDirectory() as td,mock.patch.object(R5,'run_gate',return_value={'decision':'OFFLINE_PASS_R6_CANDIDATE'}):
            with self.assertRaises(r6.R6Error):
                r6.run(ROOT,Path(td),live=True,api_key='',api_request=lambda *_:called.append('called'),require_approval=False)
            self.assertEqual(called,[])

if __name__=='__main__':unittest.main()

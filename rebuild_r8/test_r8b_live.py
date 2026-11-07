"""Network-free smoke and adversarial tests for R8-B."""
from __future__ import annotations
import copy
import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

import r8_offline as r8a
import r8b_live as b
import r8b_gate as g

class FakeResponse:
    def __init__(self, data): self.payload = json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, size=None): return self.payload

class R8BTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = r8a.fact_catalog()
        cls.draft = r8a.read_json(r8a.FIX / 'mock_analysis_drafts.json')['drafts'][0]

    def api_data(self, draft=None):
        return {'id': 'resp_test_123456', 'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(draft or self.draft, ensure_ascii=False)}]}],
                'usage': {'input_tokens': 12, 'output_tokens': 50, 'total_tokens': 62}}

    def test_schema_root_strict(self):
        s=b.schema_for_bea(self.cat)
        self.assertFalse(s['additionalProperties'])
        self.assertEqual(s['required'], list(s['properties']))

    def test_nested_schema_strict(self):
        def walk(x):
            if isinstance(x, dict):
                if x.get('type')=='object':
                    self.assertEqual(set(x['required']), set(x['properties']))
                    self.assertIs(x['additionalProperties'],False)
                for t in x.values():walk(t)
            if isinstance(x,list):
                for t in x: walk(t)
        walk(b.schema_for_bea(self.cat))

    def test_model_observation_can_only_select_fact_ids(self):
        observation = b.schema_for_bea(self.cat)['properties']['observation']
        self.assertEqual(set(observation['properties']), {'fact_ids'})
        self.assertIs(observation['additionalProperties'], False)

    def test_observation_rendered_by_program_from_fact_ids(self):
        raw = copy.deepcopy(self.draft)
        raw['observation'] = {'fact_ids': ['F001', 'F002']}
        assembled = b.bind_model_observation(raw)
        result = b.report_bundle(assembled, self.cat, 'LIVE_MODEL_UNVERIFIED')
        self.assertEqual(result['observation_text_origin'], 'PROGRAM_RENDERED_FROM_FACT_IDS')
        self.assertEqual(result['draft']['observation']['text'], b.PROGRAM_OBSERVATION_TEXT)
        self.assertEqual(result['facts_bound_by_code']['F001']['value_original'], '21.9')
        self.assertEqual(result['facts_bound_by_code']['F002']['value_original'], '3.6')
        self.assertFalse(result['publication_allowed'])

    def test_actual_rejection_pattern_is_not_silently_sanitized(self):
        raw = copy.deepcopy(self.draft)
        raw['observation'] = {
            'text': '逆差為二十一點九十億美元（F001），增加三點六十億美元（F002）。',
            'fact_ids': ['F001', 'F002'],
        }
        with self.assertRaisesRegex(b.R8BError, 'MODEL_OBSERVATION_SCHEMA_MISMATCH'):
            b.bind_model_observation(raw)

    def test_invalid_fact_id_rejected_after_program_binding(self):
        raw = copy.deepcopy(self.draft)
        raw['observation'] = {'fact_ids': ['F999']}
        with self.assertRaisesRegex(b.R8BError, 'INVALID_OR_CROSS_CASE_FACT'):
            b.safe_schema_and_fact_draft(b.bind_model_observation(raw), self.cat)

    def test_free_analysis_numbers_remain_blocked(self):
        raw = copy.deepcopy(self.draft)
        raw['observation'] = {'fact_ids': ['F001']}
        raw['interpretation']['text'] += ' 因此推測增加二十一億美元。'
        with self.assertRaisesRegex(b.R8BError, 'MODEL_GENERATED_NUMBER'):
            b.safe_schema_and_fact_draft(b.bind_model_observation(raw), self.cat)

    def test_fact_id_inside_free_analysis_text_blocked(self):
        raw = copy.deepcopy(self.draft)
        raw['observation'] = {'fact_ids': ['F001']}
        raw['interpretation']['text'] += ' 請查看F001。'
        with self.assertRaisesRegex(b.R8BError, 'MODEL_GENERATED_NUMBER'):
            b.safe_schema_and_fact_draft(b.bind_model_observation(raw), self.cat)

    def test_schema_only_bea_ids(self):
        a=b.schema_for_bea(self.cat)['properties']['importance']['properties']['fact_ids']['items']['enum']
        self.assertEqual(a, sorted(self.cat['sources']['bea']))

    def test_payload_offline_builds(self):
        p=b.build_payload(self.cat)
        self.assertEqual(p['text']['format']['type'],'json_schema')
        self.assertTrue(p['text']['format']['strict'])
        self.assertFalse(p['store'])
        self.assertEqual(p['model'],'gpt-4.1-mini')

    def test_no_tools_and_no_web(self):
        p=b.build_payload(self.cat)
        self.assertNotIn('tools',p)
        self.assertNotIn('web_search',json.dumps(p))

    def test_response_parses(self):
        self.assertEqual(b.parse_response(self.api_data())['case_id'],'bea')

    def test_response_refusal(self):
        d=self.api_data()
        d['output'][0]['content']=[{'type':'refusal','refusal':'no'}]
        with self.assertRaisesRegex(b.R8BError,'MODEL_REFUSAL'):b.parse_response(d)

    def test_response_incomplete(self):
        d=self.api_data();d['status']='incomplete'
        with self.assertRaisesRegex(b.R8BError,'INCOMPLETE_RESPONSE'):b.parse_response(d)

    def test_response_empty(self):
        d=self.api_data();d['output']=[]
        with self.assertRaisesRegex(b.R8BError,'EMPTY_OUTPUT'):b.parse_response(d)

    def test_response_invalid_json(self):
        d=self.api_data();d['output'][0]['content'][0]['text']='not json'
        with self.assertRaisesRegex(b.R8BError,'MODEL_JSON_INVALID'):b.parse_response(d)

    def test_mock_passes(self):
        out=b.report_bundle(self.draft, self.cat,'HAND_WRITTEN_MOCK_NOT_MODEL')
        self.assertEqual(out['fact_ids'],['F001','F002'])
        self.assertEqual(out['api_calls_attempted'],0)
        self.assertFalse(out['publication_allowed'])

    def test_live_bundle_unverified(self):
        out=b.report_bundle(self.draft,self.cat,'LIVE_MODEL_UNVERIFIED',{'total_tokens':62})
        self.assertFalse(out['human_approved'])
        self.assertEqual(out['usage']['total_tokens'],62)
        self.assertEqual(out['api_calls_attempted'],1)

    def test_foreign_case_fact_fails(self):
        d=copy.deepcopy(self.draft);d['impact']['fact_ids']=['EIA-F001']
        with self.assertRaises(b.R8BError):b.safe_schema_and_fact_draft(d,self.cat)

    def test_unknown_id_fails(self):
        d=copy.deepcopy(self.draft);d['importance']['fact_ids']=['F999']
        with self.assertRaises(b.R8BError):b.safe_schema_and_fact_draft(d,self.cat)

    def test_hallucinated_number_fails(self):
        d=copy.deepcopy(self.draft);d['importance']['reason']+=' 7%'
        with self.assertRaisesRegex(b.R8BError,'MODEL_GENERATED_NUMBER'):b.safe_schema_and_fact_draft(d,self.cat)

    def test_guaranteed_prediction_fails(self):
        d=copy.deepcopy(self.draft);d['impact']['text']+=' 一定會漲價。'
        with self.assertRaisesRegex(b.R8BError,'UNSUPPORTED_CERTAINTY'):b.safe_schema_and_fact_draft(d,self.cat)

    def test_publication_allowed_fails(self):
        d=copy.deepcopy(self.draft);d['publication_allowed']=True
        with self.assertRaisesRegex(b.R8BError,'PUBLICATION_DENIED'):b.safe_schema_and_fact_draft(d,self.cat)

    def test_invalid_claim_type_fails(self):
        d=copy.deepcopy(self.draft);d['impact']['claim_type']='fact'
        with self.assertRaisesRegex(b.R8BError,'WRONG_CLAIM_TYPE'):b.safe_schema_and_fact_draft(d,self.cat)

    def test_missing_assumptions_fails(self):
        d=copy.deepcopy(self.draft);d['impact']['assumptions']=[]
        with self.assertRaisesRegex(b.R8BError,'MISSING_ASSUMPTIONS'):b.safe_schema_and_fact_draft(d,self.cat)

    def test_invalid_json_schema_fields_fails(self):
        d=copy.deepcopy(self.draft);d['unsupported']=7
        with self.assertRaisesRegex(b.R8BError,'INVALID_SCHEMA'):b.safe_schema_and_fact_draft(d,self.cat)

    def test_html_escapes_free_text(self):
        bundle=b.report_bundle(self.draft,self.cat,'HAND_WRITTEN_MOCK_NOT_MODEL')
        bundle['draft']['limitations'][0]='<script>alert(1)</script>'
        html=b.render_html(bundle)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)

    def test_html_human_review_and_release_block(self):
        bundle=b.report_bundle(self.draft,self.cat,'HAND_WRITTEN_MOCK_NOT_MODEL')
        page=b.render_html(bundle)
        self.assertIn('publication_allowed:false',page)
        self.assertIn('人工品質評分',page)

    def test_live_without_gate_denied(self):
        with patch.dict(os.environ, {'SIGNAL_R8B_ALLOW_PAID_CALL':'NO'}):
            with self.assertRaisesRegex(b.R8BError,'PAID_GATE_CLOSED'):b.run_live()

    def test_api_key_missing_denied(self):
        with self.assertRaisesRegex(b.R8BError,'NO_API_KEY'):b.one_api_request({},'')

    def test_api_exactly_one_request(self):
        calls=[]
        def opener(request, timeout):
            calls.append(request.full_url)
            return FakeResponse(self.api_data())
        p=b.build_payload(self.cat)
        result=b.one_api_request(p,'test-secret',opener=opener)
        self.assertEqual(len(calls),1)
        self.assertEqual(b.parse_response(result)['case_id'],'bea')

    def test_api_http_error_no_retry(self):
        calls=[]
        def opener(request, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(request.full_url,429,'rate limit',None,None)
        with self.assertRaisesRegex(b.R8BError,'HTTP 429'):
            b.one_api_request(b.build_payload(self.cat),'test-secret',opener=opener)
        self.assertEqual(len(calls),1)

    def test_failed_report_safe(self):
        out=b.failure_bundle('MODEL_JSON_INVALID','input corrupt',1,'sha')
        self.assertFalse(out['publication_allowed'])
        self.assertIn('狀態：MODEL_JSON_INVALID',b.render_html(out))

    def test_gate_valid_no_to_yes(self):
        c=g.decide(g.BRANCH,'1',g.ARM_MESSAGE,[g.APPROVAL_PATH],
                   'APPROVE_R8B_ONE_CALL=NO','APPROVE_R8B_ONE_CALL=YES')
        self.assertTrue(c.approved)

    def test_gate_wrong_branch(self):
        c=g.decide('refs/heads/main','1',g.ARM_MESSAGE,[g.APPROVAL_PATH],
                   'APPROVE_R8B_ONE_CALL=NO','APPROVE_R8B_ONE_CALL=YES')
        self.assertFalse(c.approved)

    def test_gate_rerun(self):
        c=g.decide(g.BRANCH,'2',g.ARM_MESSAGE,[g.APPROVAL_PATH],
                   'APPROVE_R8B_ONE_CALL=NO','APPROVE_R8B_ONE_CALL=YES')
        self.assertFalse(c.approved)

    def test_gate_extra_changed_files(self):
        c=g.decide(g.BRANCH,'1',g.ARM_MESSAGE,[g.APPROVAL_PATH,'rebuild_r8/r8b_live.py'],
                   'APPROVE_R8B_ONE_CALL=NO','APPROVE_R8B_ONE_CALL=YES')
        self.assertFalse(c.approved)

    def test_gate_stale_yes(self):
        c=g.decide(g.BRANCH,'1',g.ARM_MESSAGE,[g.APPROVAL_PATH],
                   'APPROVE_R8B_ONE_CALL=YES','APPROVE_R8B_ONE_CALL=YES')
        self.assertFalse(c.approved)

    def test_gate_message_mismatch(self):
        c=g.decide(g.BRANCH,'1','something else',[g.APPROVAL_PATH],
                   'APPROVE_R8B_ONE_CALL=NO','APPROVE_R8B_ONE_CALL=YES')
        self.assertFalse(c.approved)

    def test_gate_sha_mismatch(self):
        c=g.decide(g.BRANCH,'1',g.ARM_MESSAGE,[g.APPROVAL_PATH],
                   'APPROVE_R8B_ONE_CALL=NO','APPROVE_R8B_ONE_CALL=YES',sha_matches=False)
        self.assertFalse(c.approved)

if __name__=='__main__': unittest.main()

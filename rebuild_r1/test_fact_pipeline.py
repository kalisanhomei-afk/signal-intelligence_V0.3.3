import copy
import hashlib
import json
from pathlib import Path
import unittest

from fact_pipeline import extract, validate, validate_analysis, render_html

FIXTURE = Path(__file__).parent / "fixtures" / "bea_e7.json"

class FactPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_exact_numbers_and_provenance(self):
        facts = extract(self.source)
        self.assertEqual({f['fact_id']:f['value_original'] for f in facts['facts']},
                         {'F001':'21.9','F002':'3.6','F003':'5.3','F004':'0.6','F005':'27.3','F006':'4.2'})
        self.assertFalse(facts['publication_allowed'])
        self.assertEqual(facts['source']['period_as_written'], 'September')
        self.assertIsNone(facts['source']['period_year_in_excerpt'])
        validate(facts, self.source)

    def test_modified_evidence_fails_hash(self):
        source=copy.deepcopy(self.source); source['item']['evidence_spans'][0]['text'] += ' Fake.'
        with self.assertRaises(ValueError): extract(source)

    def test_unapproved_url_fails(self):
        source=copy.deepcopy(self.source); source['item']['url']='https://unknown.example/data'
        with self.assertRaises(ValueError): extract(source)

    def test_no_generic_number_extraction_from_unmatched_text(self):
        source=copy.deepcopy(self.source)
        s=source['item']['evidence_spans'][0];s['text']='Exports increased $9 billion in 2026.'
        s['sha256']=hashlib.sha256(s['text'].encode()).hexdigest()
        with self.assertRaises(ValueError): extract(source)

    def test_changed_unit_value_evidence_id_fails(self):
        f=extract(self.source)
        for field, value in [('unit_original','USD million'),('value_original','22.0'),('source_evidence_id','E99'),('measurement_role','decrease')]:
            with self.subTest(field=field):
                g=copy.deepcopy(f);g['facts'][0][field]=value
                with self.assertRaises(ValueError):validate(g,self.source)

    def test_no_auto_verified_publication(self):
        f=extract(self.source);f['publication_allowed']=True
        with self.assertRaises(ValueError):validate(f,self.source)

    def test_mock_ai_valid_references_without_new_digits(self):
        f=extract(self.source)
        mock={'priority':'追蹤','focus_fact_ids':['F001','F002'],
              'hypothesis':'若這項變化持續，值得檢查其對貿易結構與供應鏈的影響。',
              'unknowns':'尚未查證原因與統計基準，也沒有獨立外部佐證。'}
        self.assertEqual(validate_analysis(mock,f),mock)
        self.assertIn('F001',render_html(f,mock))

    def test_mock_ai_rejects_fabricated_digit_or_id(self):
        f=extract(self.source)
        mock={'priority':'追蹤','focus_fact_ids':['F001'],
              'hypothesis':'若這項變化持續，值得關注。','unknowns':'仍缺乏獨立證據。'}
        for key,value in [('hypothesis','若明年增長 999%，應注意。'),('focus_fact_ids',['F777']),('priority','全球最重要')]:
            with self.subTest(key=key):
                x=copy.deepcopy(mock);x[key]=value
                with self.assertRaises(ValueError): validate_analysis(x,f)

    def test_review_report_is_not_published(self):
        f=extract(self.source)
        content=render_html(f)
        self.assertIn('禁止自動發佈',content)
        self.assertIn('USD billion',content)

if __name__=='__main__': unittest.main()

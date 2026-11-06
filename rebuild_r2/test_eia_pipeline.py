import copy
import hashlib
import json
from pathlib import Path
import unittest
from eia_pipeline import extract, validate, render_html

FIXTURE = Path(__file__).parent / 'fixtures' / 'eia_yields_e2_e5.json'


class R2EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_four_facts_and_original_units(self):
        b = extract(self.source)
        self.assertEqual({f['fact_id']:f['value_original'] for f in b['facts']},
                         {'EIA-F001':'45','EIA-F002':'50','EIA-F003':'12','EIA-F004':'12'})
        self.assertTrue(all(f['unit_original']=='percent (%)' for f in b['facts']))

    def test_threshold_not_misrepresented_as_exact_observation(self):
        b=extract(self.source)
        facts=b['facts']
        self.assertEqual(facts[2]['measurement_role'],'first_exceeded_threshold')
        self.assertEqual(facts[3]['measurement_role'],'continued_at_or_above_threshold')
        self.assertEqual(facts[2]['period_as_written'],'March 2026')
        self.assertEqual(facts[3]['period_as_written'],'March 2026 through August 2026')
        self.assertEqual(facts[0]['measurement_role'],'typical_range_lower_bound')

    def test_evidence_ids_and_hashes_present(self):
        b=extract(self.source)
        self.assertEqual([x['source_evidence_id'] for x in b['facts']], ['E2','E2','E5','E5'])
        self.assertEqual(b['source']['excerpt_sha256']['E2'],self.source['item']['evidence_spans'][0]['sha256'])
        self.assertFalse(b['publication_allowed'])
        self.assertFalse(b['human_approved'])

    def test_changed_source_url_rejected(self):
        s=copy.deepcopy(self.source)
        s['item']['url']='https://example.com/todayinenergy/detail.php?id=68424'
        with self.assertRaises(ValueError): extract(s)

    def test_unread_source_rejected(self):
        s=copy.deepcopy(self.source);s['item']['body_read']=False
        with self.assertRaises(ValueError): extract(s)

    def test_missing_and_additional_span_rejected(self):
        for newrows in [self.source['item']['evidence_spans'][:1],
                        self.source['item']['evidence_spans']+[self.source['item']['evidence_spans'][0]]]:
            with self.subTest(n=len(newrows)):
                s=copy.deepcopy(self.source);s['item']['evidence_spans']=newrows
                with self.assertRaises(ValueError):extract(s)

    def test_modified_text_even_if_local_hash_updated_rejected(self):
        s=copy.deepcopy(self.source)
        row=s['item']['evidence_spans'][1]
        row['text']=row['text'].replace('12%', '13%')
        row['sha256']=hashlib.sha256(row['text'].encode('utf-8')).hexdigest()
        with self.assertRaises(ValueError):extract(s)

    def test_modified_typical_gasoline_range_rejected(self):
        s=copy.deepcopy(self.source)
        row=s['item']['evidence_spans'][0]
        row['text']=row['text'].replace('45%–50%', '44%–51%')
        row['sha256']=hashlib.sha256(row['text'].encode('utf-8')).hexdigest()
        with self.assertRaises(ValueError):extract(s)

    def test_corrupted_fact_unit_or_value_rejected(self):
        b=extract(self.source)
        for key,value in [('value_original','99'),('unit_original','USD'),('source_evidence_id','E99'),
                          ('period_as_written','February 2026'),('measurement_role','exact_observed_value')]:
            with self.subTest(key=key):
                bad=copy.deepcopy(b);bad['facts'][2][key]=value
                with self.assertRaises(ValueError):validate(bad,self.source)

    def test_cannot_mark_as_approved(self):
        b=extract(self.source)
        for key in ['human_approved','publication_allowed']:
            bad=copy.deepcopy(b);bad[key]=True
            with self.assertRaises(ValueError):validate(bad,self.source)

    def test_report_is_offline_and_has_caveats(self):
        r=render_html(extract(self.source))
        for token in ['EIA-F001','EIA-F004','典型範圍','12%','不自動產生市場與價格推論']:
            self.assertIn(token,r)

if __name__=='__main__':unittest.main()

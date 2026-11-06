"""Offline fail-closed tests, no API or network."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from arxiv_pipeline import checked_abstract, extract, validate, render_html

FIXTURE = Path(__file__).parent / 'fixtures' / 'arxiv_mesa_abstract_e1_e6.json'


class ArxivR3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_extracts_six_author_attributed_records(self):
        b = extract(self.source)
        self.assertEqual({f['fact_id']: f['value_normalized'] for f in b['facts']}, {
            'ARXIV-F001': 5, 'ARXIV-F002': 4, 'ARXIV-F003': 2,
            'ARXIV-F004': 7, 'ARXIV-F005': 52, 'ARXIV-F006': 49,
        })
        self.assertTrue(all(f['claim_attribution'] == 'authors_abstract_self_report' for f in b['facts']))

    def test_percentages_not_relabelled_as_accuracy_or_success_rate(self):
        b = extract(self.source)
        for f in b['facts'][-2:]:
            self.assertEqual(f['unit_original'], 'percent (%)')
            self.assertFalse(f['metric_definition_verified'])
            self.assertEqual(f['measurement_role'], 'authors_reported_best_result')
        self.assertEqual(b['claim_groups'][2]['metric_name'], 'not_specified_in_archived_abstract')

    def test_five_suites_and_four_axes_not_nine(self):
        b = extract(self.source)
        self.assertEqual(b['facts'][0]['value_normalized'], 5)
        self.assertEqual(b['facts'][1]['value_normalized'], 4)
        self.assertEqual(len(b['claim_groups'][0]['axes_as_written']), 4)

    def test_citation_ids_are_original_excerpt_ids(self):
        b = extract(self.source)
        self.assertEqual([f['source_evidence_id'] for f in b['facts']], ['E4','E4','E5','E6','E6','E6'])
        for f in b['facts']:
            self.assertEqual(f['source_span_sha256'], b['source']['excerpt_sha256'][f['source_evidence_id']])
        self.assertEqual(len(b['raw_excerpts']), 6)

    def test_not_verified_or_published(self):
        b = extract(self.source)
        self.assertIs(b['publication_allowed'], False)
        self.assertIs(b['human_approved'], False)
        self.assertTrue(all(f['independently_verified'] is False for f in b['facts']))
        self.assertTrue(all(f['peer_review_confirmed'] is False for f in b['facts']))

    def test_rejects_unlisted_source(self):
        s = copy.deepcopy(self.source)
        s['item']['url'] = 'https://example.org/abs/2611.05567'
        with self.assertRaises(ValueError): extract(s)

    def test_rejects_changed_source_title(self):
        s = copy.deepcopy(self.source)
        s['item']['title'] = 'Different robotics paper'
        with self.assertRaises(ValueError): extract(s)

    def test_rejects_non_abstract_input(self):
        s = copy.deepcopy(self.source)
        s['item']['kind'] = 'html'
        with self.assertRaises(ValueError): extract(s)

    def test_rejects_changed_body_read_status(self):
        s = copy.deepcopy(self.source)
        s['item']['body_read'] = True
        with self.assertRaises(ValueError): extract(s)

    def test_rejects_removed_duplicate_and_extra_snippets(self):
        for mode in ('missing', 'duplicate', 'extra'):
            with self.subTest(mode=mode):
                s = copy.deepcopy(self.source)
                if mode == 'missing':
                    s['item']['evidence_spans'] = s['item']['evidence_spans'][:-1]
                elif mode == 'duplicate':
                    s['item']['evidence_spans'][-1] = s['item']['evidence_spans'][0]
                else:
                    s['item']['evidence_spans'].append({'id': 'E7', 'text': 'new', 'sha256': 'hash'})
                with self.assertRaises(ValueError): extract(s)

    def test_rejects_changed_numbers_even_with_recomputed_local_hash(self):
        for old, new in [('52%', '82%'), ('49%', '99%'), ('seven', 'eight')]:
            with self.subTest(old=old):
                s = copy.deepcopy(self.source)
                row = s['item']['evidence_spans'][-1]
                row['text'] = row['text'].replace(old, new)
                row['sha256'] = hashlib.sha256(row['text'].encode('utf-8')).hexdigest()
                with self.assertRaises(ValueError): extract(s)

    def test_rejects_changed_author_excerpt_and_hash(self):
        s = copy.deepcopy(self.source)
        row = s['item']['evidence_spans'][3]
        row['text'] = row['text'].replace('five', 'nine')
        row['sha256'] = hashlib.sha256(row['text'].encode('utf-8')).hexdigest()
        with self.assertRaises(ValueError): extract(s)

    def test_rejects_corrupted_fact_number_or_unit_or_context(self):
        b = extract(self.source)
        for field, value in [
            ('value_normalized', 100), ('value_original','100'), ('unit_original','success rate (%)'),
            ('context','MESA'), ('source_evidence_id','E4'), ('metric_definition_verified',True),
            ('peer_review_confirmed',True), ('independently_verified',True),
        ]:
            with self.subTest(field=field):
                bad = copy.deepcopy(b)
                bad['facts'][-1][field] = value
                with self.assertRaises(ValueError): validate(bad, self.source)

    def test_rejects_approval_and_publishing_flags(self):
        b = extract(self.source)
        for key in ('human_approved', 'publication_allowed'):
            bad = copy.deepcopy(b)
            bad[key] = True
            with self.assertRaises(ValueError): validate(bad, self.source)

    def test_rejects_tampered_claim_groups_and_new_claims(self):
        b = extract(self.source)
        bad = copy.deepcopy(b)
        bad['claim_groups'][2]['metric_name'] = 'success_rate'
        with self.assertRaises(ValueError): validate(bad, self.source)
        bad = copy.deepcopy(b)
        bad['facts'].append({'fact_id':'ARXIV-F999','value_normalized':99})
        with self.assertRaises(ValueError): validate(bad, self.source)

    def test_html_says_author_not_validated(self):
        text = render_html(extract(self.source))
        for token in ('作者摘要', '不可發布', '52%', '49%', 'ARXIV-F005', '準確率', '成功率', '五個 suite'):
            self.assertIn(token, text)

    def test_render_rejects_approved_flag(self):
        b = extract(self.source)
        b['human_approved'] = True
        with self.assertRaises(ValueError): render_html(b)


if __name__ == '__main__':
    unittest.main()

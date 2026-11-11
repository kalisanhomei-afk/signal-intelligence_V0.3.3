"""K3 tests with actual official release-version numeric fixtures (not simulated market prices)."""
from __future__ import annotations
import copy
from decimal import Decimal
import unittest
from research_core.contracts import ContractError
from research_core.stockflow import REQUIRED
from research_core.k3.engine import (
    load_fixture, extract_current_projection, build_k1_archive,
    release_at, ordered_releases,component_attribution,persistence_benchmark,
)

class RealVintages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_fixture()
        cls.states = ordered_releases(cls.doc)

    def bad(self,mutator,code):
        doc=copy.deepcopy(self.doc)
        mutator(doc)
        with self.assertRaises(ContractError) as e:
            build_k1_archive(doc)
        self.assertEqual(e.exception.code,code)

    def test_four_real_releases(self):
        self.assertEqual(len(self.states),4)
        self.assertEqual([x['publication'][:10] for x in self.states],
                         ['2026-07-10','2026-08-12','2026-09-11','2026-10-09'])
    def test_stock_estimates_source(self):
        self.assertEqual([int(x['values']['ending_stocks']) for x in self.states],
                         [1790,1653,1567,1849])
    def test_production_source(self):
        self.assertEqual([int(x['values']['production']) for x in self.states],
                         [16000,16013,15800,16034])
    def test_expected_unit(self):
        self.assertTrue(all(x['unit']=='million_bushels' for x in self.states))
    def test_single_market_year(self):
        self.assertTrue(all(x['market_year']=='MY2026/27' for x in self.states))
    def test_https_authoritative(self):
        self.assertTrue(all('esmis.nal.usda.gov' in x['source_uri'] for x in self.states))
    def test_k1_observation_count(self):
        obs,snaps=build_k1_archive(self.doc)
        self.assertEqual(len(obs),24)
        self.assertEqual(len(snaps),4)
        self.assertEqual({o.series_id for o in obs},set(REQUIRED))
    def test_later_retrieval_than_publication(self):
        obs,snaps=build_k1_archive(self.doc)
        self.assertTrue(all(x.retrieved_at.startswith('2026-11') for x in snaps.values()))
    def test_before_first_release_unavailable(self):
        self.assertIsNone(release_at(self.doc,'2026-07-10T11:59:00-04:00'))
    def test_at_first_release_available_public(self):
        self.assertEqual(release_at(self.doc,'2026-07-10T12:00:00-04:00')['values']['ending_stocks'],'1790')
    def test_before_next_release_previous_remains(self):
        self.assertEqual(release_at(self.doc,'2026-08-12T11:59:00-04:00')['values']['ending_stocks'],'1790')
    def test_cross_timezone_selection(self):
        self.assertEqual(release_at(self.doc,'2026-09-30T23:00:00+08:00')['values']['ending_stocks'],'1567')
    def test_system_replay_no_backdating(self):
        self.assertIsNone(release_at(self.doc,'2026-10-20T00:00:00+00:00',policy='system_replay'))
    def test_public_replay_distinct(self):
        self.assertEqual(release_at(self.doc,'2026-10-20T00:00:00+00:00',policy='public_replay')['values']['ending_stocks'],'1849')
    def test_system_replay_after_actual_archive_import(self):
        self.assertEqual(release_at(self.doc,'2026-11-12T00:00:00+00:00',policy='system_replay')['values']['ending_stocks'],'1849')
    def test_invalid_policy_rejected(self):
        with self.assertRaises(ContractError) as e:
            release_at(self.doc,'2026-10-20T00:00:00+00:00',policy='lax')
        self.assertEqual(e.exception.code,'K3_POLICY')
    def test_naive_asof_rejected(self):
        with self.assertRaises(ContractError):
            release_at(self.doc,'2026-10-20T00:00:00')
    def test_scope_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('geography','WORLD'),'K3_SCOPE_MISMATCH')
    def test_duplicate_release_rejected(self):
        self.bad(lambda d:d['sources'].append(copy.deepcopy(d['sources'][0])),'K3_DUPLICATE_RELEASE')
    def test_unsupported_domain_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('source_uri','https://example.org/abc.txt'),'K3_SOURCE_INVALID')
    def test_invalid_transcription_status_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('excerpt_kind','OFFICIAL_RAW_FILE_HASH'),'K3_TRANSCRIPTION_STATUS')
    def test_missing_row_rejected(self):
        def mutate(d):
            d['sources'][0]['excerpt']='\n'.join(x for x in d['sources'][0]['excerpt'].splitlines() if not x.startswith('Ending Stocks'))
        self.bad(mutate,'K3_ROW_MISSING_OR_DUPLICATE')
    def test_duplicated_row_rejected(self):
        def mutate(d):
            text=d['sources'][0]['excerpt']
            d['sources'][0]['excerpt']=text+'\n'+next(x for x in text.splitlines() if x.startswith('Ending Stocks'))
        self.bad(mutate,'K3_ROW_MISSING_OR_DUPLICATE')
    def test_fake_stocks_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('excerpt',d['sources'][0]['excerpt'].replace('1551 2020 1960 1790','1551 2020 1960 1791')),'K3_STOCKFLOW_BALANCE')
    def test_fake_production_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('excerpt',d['sources'][0]['excerpt'].replace('14892 17021 15995 16000','14892 17021 15995 16001')),'K3_SUPPLY_TOTAL')
    def test_malformed_row_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('excerpt',d['sources'][0]['excerpt'].replace('14892 17021 15995 16000','14892 17021 wrong 16000')),'K3_ROW_AMBIGUOUS')
    def test_release_date_mismatch_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('release_date','2026-07-11'),'K3_RELEASE_MISMATCH')
    def test_retrieved_before_publication_rejected(self):
        self.bad(lambda d:d['sources'][0].__setitem__('retrieved_at','2026-07-01T00:00:00+00:00'),'K3_INVALID_TIME_ORDER')
    def test_empty_observations_rejected(self):
        doc=copy.deepcopy(self.doc);doc['sources']=doc['sources'][:1]
        with self.assertRaises(ContractError):build_k1_archive(doc)
    def test_revision_values(self):
        rev=[component_attribution(a,b) for a,b in zip(self.states[:-1],self.states[1:])]
        self.assertEqual([int(x['stock_revision']) for x in rev],[-137,-86,282])
    def test_oct_revision_contributions(self):
        r=component_attribution(self.states[-2],self.states[-1])['accounting_contributions']
        self.assertEqual(r,{'beginning_stocks':'173','production':'234','imports':'0','domestic_use':'-100','exports':'-25'})
    def test_rev_cannot_reverse_time(self):
        with self.assertRaises(ContractError):component_attribution(self.states[1],self.states[0])
    def test_rev_causality_not_proven(self):
        r=component_attribution(self.states[0],self.states[1])
        self.assertFalse(r['causal_identification'])
    def test_persistence_errors(self):
        b=persistence_benchmark(self.states)
        self.assertEqual([int(x['error_actual_minus_predicted']) for x in b['forecasts']],[-137,-86,282])
        self.assertEqual(b['sample_count'],3)
    def test_mae(self):
        b=persistence_benchmark(self.states)
        self.assertEqual(Decimal(b['mae_million_bushels']),Decimal(505)/3)
    def test_not_true_outcome(self):
        b=persistence_benchmark(self.states)
        self.assertTrue(all(not x['verified_realized_inventory'] for x in b['forecasts']))
    def test_no_investment_signal(self):
        b=persistence_benchmark(self.states)
        self.assertFalse(b['model_has_outperformance_evidence'])
        self.assertTrue(all(not x['is_investment_signal'] for x in b['forecasts']))
    def test_benchmark_insufficient_sample(self):
        with self.assertRaises(ContractError):persistence_benchmark(self.states[:1])
    def test_tamper_scope_comparison(self):
        a=copy.deepcopy(self.states[0]);b=copy.deepcopy(self.states[1]);b['unit']='metric_tons'
        with self.assertRaises(ContractError):component_attribution(a,b)
    def test_source_current_last_column(self):
        vals=extract_current_projection(self.doc['sources'][3])
        self.assertEqual(vals['harvested_area'],Decimal('88.5'))
        self.assertEqual(vals['yield_per_acre'],Decimal('181.2'))
    def test_rename_header_must_fail(self):
        doc=copy.deepcopy(self.doc)
        doc['sources'][0]['excerpt']=doc['sources'][0]['excerpt'].replace('CORN\n','SOYBEANS\n')
        with self.assertRaises(ContractError) as e:build_k1_archive(doc)
        self.assertEqual(e.exception.code,'K3_SOURCE_STRUCTURE')
    def test_k3_preview_is_local_only(self):
        doc=copy.deepcopy(self.doc)
        self.assertFalse(doc.get('publication_allowed',False))

if __name__=='__main__':unittest.main()

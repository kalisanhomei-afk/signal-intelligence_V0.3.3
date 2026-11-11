import copy
import unittest
from decimal import Decimal
from research_core.contracts import ContractError
from research_core.k31.engine import load_source, validate_source, select_latest_pair, assemble_study

class TestK31(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=load_source()
        cls.records=validate_source(cls.src)
        cls.study=assemble_study()

    def reject(self, mutator, code):
        doc=copy.deepcopy(self.src)
        mutator(doc)
        with self.assertRaises(ContractError) as err:
            validate_source(doc)
        self.assertEqual(err.exception.code, code)

    def test_no_fabricated_system_retrieval_time(self):
        self.assertIsNone(self.src["retrieved_by_project_at"])
    def test_real_four_editions(self):
        self.assertEqual(len(self.records),4)
    def test_good_excellent_by_source(self):
        self.assertEqual([r['good_excellent_pct'] for r in self.records],[67,61,56,54])
    def test_unit_percent_sums(self):
        self.assertTrue(all(sum(r[k] for k in ('very_poor','poor','fair','good','excellent'))==100 for r in self.records))
    def test_all_usda_links(self):
        self.assertTrue(all('esmis.nal.usda.gov' in r['source_uri'] for r in self.records))
    def test_conservative_public_proxy(self):
        self.assertEqual(self.records[0]['available_at_proxy_utc'],'2026-07-07T12:00:00+00:00')
    def test_no_early_availability(self):
        self.assertFalse(select_latest_pair(self.records,'2026-07-07T11:59:59+00:00'))
    def test_release_available_at_proxy(self):
        self.assertEqual(len(select_latest_pair(self.records,'2026-07-07T12:00:00+00:00')),1)
    def test_just_before_sep_proxy_previous(self):
        a=select_latest_pair(self.records,'2026-09-09T11:59:59+00:00')
        self.assertEqual(a[-1]['source_date'],'2026-08-10')
    def test_sep_proxy_enabled(self):
        self.assertEqual(select_latest_pair(self.records,'2026-09-09T12:00:00+00:00')[-1]['source_date'],'2026-09-08')
    def test_oct_after_september_origin_blocked(self):
        a=select_latest_pair(self.records,'2026-09-11T12:00:00-04:00')
        self.assertEqual(a[-1]['source_date'],'2026-09-08')
        self.assertNotIn('2026-10-05',[x['source_date'] for x in a])
    def test_source_percent_rejected(self):
        self.reject(lambda d:d['records'][0].__setitem__('good',54),'K31_PERCENT')
    def test_row_numbers_rejected(self):
        def mutate(d):
            d['records'][0]['good']=54;d['records'][0]['excellent']=13
        self.reject(mutate,'K31_ROW_MISMATCH')
    def test_duplicate_rejected(self):
        self.reject(lambda d:d['records'].append(copy.deepcopy(d['records'][0])),'K31_DUPLICATE')
    def test_fake_source_rejected(self):
        self.reject(lambda d:d['records'][0].__setitem__('source_uri','https://example.com/a.txt'),'K31_URL')
    def test_proxy_backdating_rejected(self):
        self.reject(lambda d:d['records'][0].__setitem__('available_at_proxy_utc','2026-07-06T12:00:00+00:00'),'K31_PROXY')
    def test_unreasonable_week_rejected(self):
        self.reject(lambda d:d['records'][0].__setitem__('week_ending','2026-07-06'),'K31_WEEK')
    def test_scope_rejected(self):
        self.reject(lambda d:d.__setitem__('series','SOY'),'K31_SERIES')
    def test_provenance_rejected(self):
        self.reject(lambda d:d.__setitem__('data_status','DOWNLOADED_FULL_USDA_FILE'),'K31_PROVENANCE')
    def test_mode_rejected(self):
        self.reject(lambda d:d.__setitem__('purpose','LIVE_CAPTURE'),'K31_MODE')
    def test_2026_yields_from_k3(self):
        x=self.study['trials']
        self.assertEqual([(t['current_wasde_yield_bushels_per_acre'],t['next_wasde_yield_estimate_bushels_per_acre']) for t in x], [('183.0','180.7'),('180.7','178.5'),('178.5','181.2')])
    def test_target_is_next_wasde_not_final(self):
        self.assertTrue(all(t['not_a_realized_yield'] for t in self.study['trials']))
    def test_three_origins(self):
        self.assertEqual(self.study['comparison']['target_count'],3)
    def test_one_abstention(self):
        self.assertIsNone(self.study['trials'][0]['direction_correct_if_testable'])
    def test_direction_signals(self):
        self.assertEqual([t['mechanical_hypothesis_next_yield_revision'] for t in self.study['trials']], ['ABSTAIN_INSUFFICIENT_PRIOR_SIGNAL','DOWN','DOWN'])
    def test_only_two_comparables(self):
        self.assertEqual(self.study['comparison']['direction_tested_count'],2)
    def test_one_hit_one_miss(self):
        self.assertEqual([t['direction_correct_if_testable'] for t in self.study['trials']],[None,True,False])
    def test_baseline_mae(self):
        self.assertEqual(Decimal(self.study['comparison']['baseline_mae_bu_per_acre']),Decimal('2.4'))
    def test_no_false_outperformance(self):
        self.assertIsNone(self.study['comparison']['model_outperforms_baseline'])
    def test_no_trading(self):
        self.assertFalse(self.study['publication_allowed']);self.assertFalse(self.study['trade_allowed'])
    def test_no_param_fit(self):
        self.assertTrue(self.study['no_parameter_fitting'])
    def test_latest_unscored_not_claimed_success(self):
        obs=self.study['latest_unscored_origin']
        self.assertEqual(obs['source_date'],'2026-10-05')
        self.assertEqual(obs['selected_edition_delta_pp'],-2)
        self.assertEqual(obs['evaluation_status'],'NOT_SCORED_NEXT_WASDE_NOT_IN_FROZEN_K3_DATASET')
    def test_four_leads_preserved(self):
        self.assertEqual(len(self.study['all_lead_observations']),4)
    def test_unreleased_future_wasde_not_used(self):
        self.assertEqual(self.study['trials'][-1]['target_release'][:10],'2026-10-09')

if __name__=='__main__':unittest.main()

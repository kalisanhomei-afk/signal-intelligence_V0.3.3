"""K2 strict offline tests against the actual K1 synthetic fixture and contracts."""
import json
import unittest
from dataclasses import replace
from pathlib import Path
from decimal import Decimal

from research_core.contracts import ContractError, Observation, SourceSnapshot
from research_core.k2.engine import (
    DATA_TYPE, ScenarioSpec, state_at, forward_scenario, reverse_diagnostic,
    close_loop, fmt
)

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures' / 'synthetic_corn_vintages.json'
EARLY = '2026-01-11T12:00:00-05:00'
LATE = '2026-01-16T12:00:00-05:00'


def fixture_data():
    d = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert d['fixture_type'] == DATA_TYPE
    snapshots = {x['snapshot_id']: SourceSnapshot(**{k: v for k, v in x.items() if k != 'raw_payload_utf8'}) for x in d['snapshots']}
    observations = [Observation(**x) for x in d['observations']]
    return observations, snapshots


class K2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs, cls.snaps = fixture_data()
        cls.early = state_at(cls.obs, cls.snaps, EARLY)
        cls.late = state_at(cls.obs, cls.snaps, LATE)

    def spec(self, **kwargs):
        return ScenarioSpec('K2-TEST', EARLY, kwargs or {'production': '-80'}, 'synthetic exploratory what-if')

    def assert_code(self, code, func):
        with self.assertRaises(ContractError) as caught:
            func()
        self.assertEqual(caught.exception.code, code)

    def test_01_early_vintage_v1(self): self.assertEqual(self.early.vintage_id, 'v1')
    def test_02_late_vintage_v2(self): self.assertEqual(self.late.vintage_id, 'v2')
    def test_03_k1_early_value(self): self.assertEqual(self.early.values['production'], '15000')
    def test_04_k1_revision_value(self): self.assertEqual(self.late.values['production'], '14900')
    def test_05_asof_before_first_reject(self):
        self.assert_code('INCOMPLETE_STOCKFLOW', lambda: state_at(self.obs, self.snaps, '2026-01-09T00:00:00-05:00'))
    def test_06_later_source_cannot_be_used_early(self):
        self.assertNotEqual(self.early.observation_ids['production'], self.late.observation_ids['production'])
    def test_07_scope_is_fixed(self): self.assertEqual(self.early.period, self.late.period)
    def test_08_zero_shock_keeps_balance(self):
        res = forward_scenario(self.early, self.spec(production='0'))
        self.assertEqual(res['counterfactual_ending_stocks'], '1625')
    def test_09_declared_negative_production(self):
        res = forward_scenario(self.early, self.spec(production='-80'))
        self.assertEqual(res['counterfactual_ending_stocks'], '1545')
        self.assertEqual(res['delta_ending_stocks'], '-80')
    def test_10_higher_domestic_use_reduces_stocks(self):
        self.assertEqual(forward_scenario(self.early, self.spec(domestic_use='100'))['delta_ending_stocks'], '-100')
    def test_11_higher_exports_reduces_stocks(self):
        self.assertEqual(forward_scenario(self.early, self.spec(exports='100'))['delta_ending_stocks'], '-100')
    def test_12_higher_imports_increases_stocks(self):
        self.assertEqual(forward_scenario(self.early, self.spec(imports='100'))['delta_ending_stocks'], '100')
    def test_13_multi_shock_accounting(self):
        res = forward_scenario(self.early, self.spec(production='-40', exports='60', imports='10'))
        self.assertEqual(res['delta_ending_stocks'], '-90')
    def test_14_base_immutability(self):
        forward_scenario(self.early, self.spec(production='-20'))
        self.assertEqual(self.early.values['production'], '15000')
    def test_15_direct_ending_stock_shock_forbidden(self):
        self.assert_code('SHOCK_TO_TARGET_FORBIDDEN', lambda: self.spec(ending_stocks='-20'))
    def test_16_unknown_driver_forbidden(self):
        self.assert_code('SHOCK_TO_TARGET_FORBIDDEN', lambda: self.spec(magic='5'))
    def test_17_decimal_must_be_string(self):
        self.assert_code('DECIMAL_AS_STRING_REQUIRED', lambda: self.spec(production=10))
    def test_18_nonfinite_forbidden(self):
        self.assert_code('NONFINITE_VALUE', lambda: self.spec(production='NaN'))
    def test_19_negative_flow_forbidden(self):
        self.assert_code('NEGATIVE_SCENARIO_INPUT', lambda: forward_scenario(self.early, self.spec(production='-16000')))
    def test_20_negative_end_stock_forbidden(self):
        self.assert_code('NEGATIVE_PROJECTED_STOCK', lambda: forward_scenario(self.early, self.spec(production='-2000')))
    def test_21_asof_mismatch_forbidden(self):
        spec = ScenarioSpec('S', LATE, {'production': '-80'}, 'test')
        self.assert_code('ASOF_MISMATCH', lambda: forward_scenario(self.early, spec))
    def test_22_uncalibrated_scenario_cannot_claim_forecast(self):
        self.assert_code('UNVERIFIED_FORECAST', lambda: ScenarioSpec('S', EARLY, {'production': '-80'}, 'test', 'CALIBRATED'))
    def test_23_scenario_rejects_empty_shock(self):
        self.assert_code('INVALID_SCENARIO', lambda: ScenarioSpec('S', EARLY, {}, 'test'))
    def test_24_reverse_observed_stock_revision(self):
        result = reverse_diagnostic(self.early, self.late)
        self.assertEqual(result['observed_ending_stock_change'], '-100')
    def test_25_reverse_accounts_for_production(self):
        result = reverse_diagnostic(self.early, self.late)
        self.assertEqual(len(result['accounting_contributors']), 1)
        self.assertEqual(result['accounting_contributors'][0]['series_id'], 'production')
        self.assertEqual(result['accounting_contributors'][0]['accounting_contribution_to_ending_stocks'], '-100')
    def test_26_reverse_does_not_prove_causality(self):
        result = reverse_diagnostic(self.early, self.late)
        self.assertFalse(result['causality_confirmed'])
        self.assertTrue(all(x['status'] == 'UNTESTED_CANDIDATE' for x in result['upstream_candidate_causes']))
    def test_27_reverse_causal_link_contract(self):
        result = reverse_diagnostic(self.early, self.late)
        self.assertTrue(all(x['evidence_status'] == 'hypothesis' for x in result['k1_causal_hypotheses']))
    def test_28_backward_comparison_forbidden(self):
        self.assert_code('INVALID_COMPARISON_ORDER', lambda: reverse_diagnostic(self.late, self.early))
    def test_29_same_vintage_forbidden(self):
        self.assert_code('NO_NEW_VINTAGE', lambda: reverse_diagnostic(self.early, replace(self.early, as_of=LATE)))
    def test_30_reverse_scope_mismatch(self):
        self.assert_code('DIFFERENT_SCOPE', lambda: reverse_diagnostic(self.early, replace(self.late, unit='metric_tons')))
    def test_31_reverse_unit_mismatch(self):
        self.assert_code('DIFFERENT_SCOPE', lambda: reverse_diagnostic(self.early, replace(self.late, period='MY2026/27')))
    def test_32_loop_residual(self):
        fwd = forward_scenario(self.early, self.spec(production='-80'))
        rev = reverse_diagnostic(self.early, self.late)
        res = close_loop(fwd, rev)
        self.assertEqual(res['revision_delta_residual_observed_minus_scenario'], '-20')
    def test_33_loop_stops_future_scenario(self):
        fwd = forward_scenario(self.early, self.spec(production='-80'))
        rev = reverse_diagnostic(self.early, self.late)
        fwd['as_of'] = LATE
        self.assert_code('ASOF_MISMATCH', lambda: close_loop(fwd, rev))
    def test_34_loop_prevents_scope_mismatch(self):
        fwd = forward_scenario(self.early, self.spec(production='-80'))
        rev = reverse_diagnostic(self.early, self.late)
        fwd['unit'] = 'metric_tons'
        self.assert_code('DIFFERENT_SCOPE', lambda: close_loop(fwd, rev))
    def test_35_loop_not_investment_signal(self):
        fwd = forward_scenario(self.early, self.spec(production='-80'))
        rev = reverse_diagnostic(self.early, self.late)
        res = close_loop(fwd, rev)
        self.assertFalse(res['investment_signal'])
        self.assertEqual(res['predictive_edge'], 'NOT_TESTED_SINGLE_SYNTHETIC_CASE')
    def test_36_bad_source_status_rejected(self):
        fake = replace(self.snaps['SYN-CORN-v1'], source_type='official')
        self.assert_code('K2_SYNTHETIC_ONLY', lambda: state_at(self.obs, {**self.snaps, 'SYN-CORN-v1': fake}, EARLY))
    def test_37_missing_source_rejected(self):
        self.assert_code('MISSING_SOURCE', lambda: state_at(self.obs, {'SYN-CORN-v1': self.snaps['SYN-CORN-v1']}, EARLY))
    def test_38_missing_observation_rejected(self):
        self.assert_code('INCOMPLETE_STOCKFLOW', lambda: state_at([o for o in self.obs if o.series_id != 'exports'], self.snaps, EARLY))
    def test_39_revised_version_is_not_early_system_input(self):
        self.assertTrue(all(v.startswith('SYN-v1') for v in self.early.observation_ids.values()))
    def test_40_no_market_forecast_fields(self):
        fwd = forward_scenario(self.early, self.spec(production='-80'))
        self.assertNotIn('predicted_futures_price', fwd)
        self.assertFalse(fwd['forecast_claim'])
    def test_41_no_probability_claim(self):
        fwd = forward_scenario(self.early, self.spec(production='-80'))
        self.assertFalse(fwd['probabilities_calibrated'])
    def test_42_decimal_normalize(self):
        self.assertEqual(fmt(Decimal('-0.50')), '-0.5')
        self.assertEqual(fmt(Decimal('0.000')), '0')


if __name__ == '__main__':
    unittest.main()

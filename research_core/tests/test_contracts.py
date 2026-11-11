import unittest
from dataclasses import replace
from research_core.contracts import (
    ContractError, SourceSnapshot, Observation, EventSignal, CausalLink,
    ForecastRun, InvestmentHypothesis, DecisionRecord, instant, number,
)
from research_core.fixtures.build_fixture import create_fixture


def snapshots_and_observations():
    fixture = create_fixture()
    snapshots = [SourceSnapshot(**{k: v for k, v in s.items() if k != "raw_payload_utf8"}) for s in fixture["snapshots"]]
    observations = [Observation(**o) for o in fixture["observations"]]
    return fixture, snapshots, observations


def code(error):
    return error.exception.code


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.snapshots, self.observations = snapshots_and_observations()
        self.obs = self.observations[0]
        self.snap = self.snapshots[0]

    def test_synthetic_fixture_valid(self):
        self.assertEqual(len(self.observations), 12)
        self.assertEqual(len(self.snapshots), 2)

    def test_time_with_timezone(self):
        self.assertEqual(instant("2026-01-10T14:00:00Z"), instant("2026-01-10T09:00:00-05:00"))

    def test_no_naive_time(self):
        with self.assertRaises(ContractError) as e:
            instant("2026-01-10T12:00:00")
        self.assertEqual(code(e), "NAIVE_TIME")

    def test_invalid_iso_time(self):
        with self.assertRaises(ContractError) as e:
            instant("not-a-date")
        self.assertEqual(code(e), "INVALID_TIME")

    def test_empty_time(self):
        with self.assertRaises(ContractError) as e:
            instant("")
        self.assertEqual(code(e), "MISSING_FIELD")

    def test_decimal_string_not_float(self):
        with self.assertRaises(ContractError) as e:
            number(21.9)
        self.assertEqual(code(e), "DECIMAL_AS_STRING_REQUIRED")

    def test_nonfinite_value_rejected(self):
        with self.assertRaises(ContractError) as e:
            number("Infinity")
        self.assertEqual(code(e), "NONFINITE_VALUE")

    def test_invalid_decimal_rejected(self):
        with self.assertRaises(ContractError) as e:
            number("21.9 dollars")
        self.assertEqual(code(e), "INVALID_DECIMAL")

    def test_snapshot_hash_full_sha256_required(self):
        with self.assertRaises(ContractError) as e:
            replace(self.snap, payload_sha256="abc")
        self.assertEqual(code(e), "INVALID_HASH")

    def test_snapshot_retrieval_after_publication(self):
        with self.assertRaises(ContractError) as e:
            replace(self.snap, retrieved_at="2026-01-09T08:00:00-05:00")
        self.assertEqual(code(e), "TIME_ORDER")

    def test_snapshot_schema_version(self):
        with self.assertRaises(ContractError) as e:
            replace(self.snap, schema_version="0.9")
        self.assertEqual(code(e), "SCHEMA_VERSION")

    def test_observation_requires_period(self):
        with self.assertRaises(ContractError) as e:
            replace(self.obs, period="")
        self.assertEqual(code(e), "MISSING_FIELD")

    def test_observation_requires_unit(self):
        with self.assertRaises(ContractError) as e:
            replace(self.obs, unit="")
        self.assertEqual(code(e), "MISSING_FIELD")

    def test_monthly_period_disguised_as_marketing_year(self):
        with self.assertRaises(ContractError) as e:
            replace(self.obs, period="2026-01", frequency="marketing_year")
        self.assertEqual(code(e), "PERIOD_FORMAT_MISMATCH")

    def test_invalid_marketing_year_end(self):
        with self.assertRaises(ContractError) as e:
            replace(self.obs, period="MY2025/27")
        self.assertEqual(code(e), "PERIOD_FORMAT_MISMATCH")

    def test_observation_valid_frequency(self):
        with self.assertRaises(ContractError) as e:
            replace(self.obs, frequency="sometimes")
        self.assertEqual(code(e), "INVALID_FREQUENCY")

    def test_observation_status_must_be_supported(self):
        with self.assertRaises(ContractError) as e:
            replace(self.obs, data_status="fully_verified_by_AI")
        self.assertEqual(code(e), "INVALID_STATUS")

    def test_event_multiple_unverified_causes_ok(self):
        event = EventSignal("EV1", "2026-01-12T10:00:00-05:00", "price_jump", [self.obs.observation_id], ["weather", "policy", "positioning"])
        self.assertEqual(event.causal_status, "unverified_candidates")

    def test_reverse_causal_claim_rejected(self):
        with self.assertRaises(ContractError) as e:
            EventSignal("EV1", "2026-01-12T10:00:00-05:00", "price_jump", [self.obs.observation_id], ["supply_shock"], causal_status="confirmed_cause")
        self.assertEqual(code(e), "CAUSAL_OVERCLAIM")

    def test_duplicate_evidence_ids_rejected(self):
        with self.assertRaises(ContractError) as e:
            EventSignal("EV1", "2026-01-12T10:00:00-05:00", "price_jump", ["X", "X"], [])
        self.assertEqual(code(e), "DUPLICATE_REFERENCE")

    def test_causal_hypothesis_explicit(self):
        link = CausalLink("L1", "rainfall", "yield", "causal_hypothesis", "6 weeks", "US corn", "hypothesis")
        self.assertEqual(link.evidence_status, "hypothesis")

    def test_causal_evidence_without_method_rejected(self):
        with self.assertRaises(ContractError) as e:
            CausalLink("L1", "price", "production", "causal_evidence", "1 season", "US corn", "causally_identified", ["OBS-1"])
        self.assertEqual(code(e), "CAUSAL_OVERCLAIM")

    def test_causal_evidence_without_support_rejected(self):
        with self.assertRaises(ContractError) as e:
            CausalLink("L1", "price", "production", "causal_evidence", "1 season", "US corn", "causally_identified", [], "identified experiment")
        self.assertEqual(code(e), "CAUSAL_OVERCLAIM")

    def test_causal_status_conflict_rejected(self):
        with self.assertRaises(ContractError) as e:
            CausalLink("L1", "rainfall", "yield", "empirical_association", "6 weeks", "US corn", "causally_identified")
        self.assertEqual(code(e), "CAUSAL_STATUS_MISMATCH")

    def test_identified_causal_link_requires_method(self):
        link = CausalLink("L1", "rainfall", "yield", "causal_evidence", "6 weeks", "US corn", "causally_identified", ["PAPER-1"], "instrumental variables under stated scope")
        self.assertEqual(len(link.supporting_evidence_ids), 1)

    def sample_forecast(self):
        return ForecastRun("F1", "2026-01-12T10:00:00-05:00", "ending_stocks", "MY2025/26", 30, "fixture-v1", [self.obs.observation_id], "1400", "1600", "1800", "persistence")

    def test_forecast_contract_valid(self):
        self.assertEqual(self.sample_forecast().horizon_days, 30)

    def test_forecast_quantile_order(self):
        with self.assertRaises(ContractError) as e:
            replace(self.sample_forecast(), p10="1700", p50="1600")
        self.assertEqual(code(e), "INVALID_QUANTILES")

    def test_forecast_zero_horizon(self):
        with self.assertRaises(ContractError) as e:
            replace(self.sample_forecast(), horizon_days=0)
        self.assertEqual(code(e), "INVALID_HORIZON")

    def test_forecast_no_real_trading_prediction_in_k1(self):
        with self.assertRaises(ContractError) as e:
            replace(self.sample_forecast(), data_status="official_estimate")
        self.assertEqual(code(e), "NO_REAL_FORECAST_IN_K1")

    def test_hypothesis_requires_invalidation(self):
        with self.assertRaises(ContractError) as e:
            InvestmentHypothesis("H1", "2026-01-12T10:00:00-05:00", "hypothesis", "corn", "2 months", ["OBS-1"], ["weather recovers"], "")
        self.assertEqual(code(e), "MISSING_FIELD")

    def test_hypothesis_cannot_be_declared_verified(self):
        with self.assertRaises(ContractError) as e:
            InvestmentHypothesis("H1", "2026-01-12T10:00:00-05:00", "hypothesis", "corn", "2 months", ["OBS-1"], ["weather recovers"], "inventory rises", status="confirmed_signal")
        self.assertEqual(code(e), "NOT_APPROVED")

    def sample_decision(self):
        return DecisionRecord("D1", "H1", "2026-01-12T10:00:00-05:00", "SYNTHETIC-CORN-CONTRACT", "2026-01-12T09:55:00-05:00", "4.10", "USD", "paper hold", "0.01", "max 1% paper allocation")

    def test_decision_paper_only(self):
        with self.assertRaises(ContractError) as e:
            replace(self.sample_decision(), paper_only=False)
        self.assertEqual(code(e), "NO_LIVE_TRADING")

    def test_decision_no_future_price(self):
        with self.assertRaises(ContractError) as e:
            replace(self.sample_decision(), price_as_of="2026-01-13T10:00:00-05:00")
        self.assertEqual(code(e), "FUTURE_PRICE")


if __name__ == "__main__":
    unittest.main()

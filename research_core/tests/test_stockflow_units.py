import unittest
from dataclasses import replace
from research_core.tests.test_contracts import snapshots_and_observations
from research_core.contracts import ContractError
from research_core.units import convert, ConversionSpec
from research_core.stockflow import check_balance


class StockFlowAndUnitsTests(unittest.TestCase):
    def setUp(self):
        _, _, all_obs = snapshots_and_observations()
        self.v1 = all_obs[:6]
        self.v2 = all_obs[6:]

    def test_v1_ledger_balanced(self):
        result = check_balance(self.v1)
        self.assertTrue(result.balanced)
        self.assertEqual(result.calculated_ending, "1625")

    def test_v2_ledger_balanced(self):
        result = check_balance(self.v2)
        self.assertTrue(result.balanced)
        self.assertEqual(result.calculated_ending, "1525")

    def test_bad_ending_is_an_issue_not_silent_fix(self):
        broken = [replace(o, value="1700") if o.series_id == "ending_stocks" else o for o in self.v1]
        result = check_balance(broken)
        self.assertFalse(result.balanced)
        self.assertEqual(result.reported_ending, "1700")
        self.assertEqual(result.calculated_ending, "1625")

    def test_tolerance_is_explicit(self):
        broken = [replace(o, value="1625.5") if o.series_id == "ending_stocks" else o for o in self.v1]
        self.assertFalse(check_balance(broken).balanced)
        self.assertTrue(check_balance(broken, tolerance="0.5").balanced)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ContractError) as e:
            check_balance(self.v1, tolerance="-1")
        self.assertEqual(e.exception.code, "INVALID_TOLERANCE")

    def test_mixed_month_and_marketing_year_rejected(self):
        broken = [replace(o, frequency="month", period="2026-01") if o.series_id == "imports" else o for o in self.v1]
        with self.assertRaises(ContractError) as e:
            check_balance(broken)
        self.assertEqual(e.exception.code, "PERIOD_MISMATCH")

    def test_mixed_period_rejected(self):
        broken = [replace(o, period="MY2024/25") if o.series_id == "imports" else o for o in self.v1]
        with self.assertRaises(ContractError) as e:
            check_balance(broken)
        self.assertEqual(e.exception.code, "PERIOD_MISMATCH")

    def test_mixed_unit_rejected(self):
        broken = [replace(o, unit="metric_tons") if o.series_id == "imports" else o for o in self.v1]
        with self.assertRaises(ContractError) as e:
            check_balance(broken)
        self.assertEqual(e.exception.code, "UNIT_MISMATCH")

    def test_mixed_vintage_rejected(self):
        broken = [self.v2[1] if o.series_id == "production" else o for o in self.v1]
        with self.assertRaises(ContractError) as e:
            check_balance(broken)
        self.assertEqual(e.exception.code, "SCOPE_OR_VINTAGE_MISMATCH")

    def test_scope_mismatch_rejected(self):
        broken = [replace(o, geography="TW") if o.series_id == "imports" else o for o in self.v1]
        with self.assertRaises(ContractError) as e:
            check_balance(broken)
        self.assertEqual(e.exception.code, "SCOPE_OR_VINTAGE_MISMATCH")

    def test_basis_mismatch_rejected(self):
        broken = [replace(o, measurement_basis="different") if o.series_id == "imports" else o for o in self.v1]
        with self.assertRaises(ContractError) as e:
            check_balance(broken)
        self.assertEqual(e.exception.code, "SCOPE_OR_VINTAGE_MISMATCH")

    def test_missing_component_rejected(self):
        with self.assertRaises(ContractError) as e:
            check_balance(self.v1[:5])
        self.assertEqual(e.exception.code, "MISSING_COMPONENT")

    def test_negative_component_rejected(self):
        broken = [replace(o, value="-1") if o.series_id == "imports" else o for o in self.v1]
        with self.assertRaises(ContractError) as e:
            check_balance(broken)
        self.assertEqual(e.exception.code, "NEGATIVE_STOCKFLOW")

    def test_duplicate_component_rejected(self):
        with self.assertRaises(ContractError) as e:
            check_balance(self.v1 + [self.v1[0]])
        self.assertEqual(e.exception.code, "DUPLICATE_SERIES")

    def test_exact_bushel_scale_conversion(self):
        self.assertEqual(convert("1.5", "million_bushels", "bushels", commodity="corn"), "1500000.0")

    def test_exact_reverse_scale_conversion(self):
        self.assertEqual(convert("1500000", "bushels", "million_bushels", commodity="corn"), "1.5")

    def test_implicit_bushels_to_tonnes_rejected(self):
        with self.assertRaises(ContractError) as e:
            convert("100", "bushels", "metric_tons", commodity="corn")
        self.assertEqual(e.exception.code, "INCOMPATIBLE_UNIT")

    def test_documented_custom_conversion_accepted(self):
        example = ConversionSpec("bushels", "metric_tons", "0.02", "corn", "SYNTHETIC_TEST_CONVERSION_NOT_REAL")
        self.assertEqual(convert("100", "bushels", "metric_tons", commodity="corn", conversion=example), "2.00")

    def test_wrong_commodity_conversion_rejected(self):
        example = ConversionSpec("bushels", "metric_tons", "0.02", "wheat", "TEST_ONLY")
        with self.assertRaises(ContractError) as e:
            convert("100", "bushels", "metric_tons", commodity="corn", conversion=example)
        self.assertEqual(e.exception.code, "CONVERSION_SCOPE_MISMATCH")

    def test_negative_factor_rejected(self):
        with self.assertRaises(ContractError) as e:
            ConversionSpec("bushels", "metric_tons", "-1", "corn", "TEST_ONLY")
        self.assertEqual(e.exception.code, "INVALID_CONVERSION")


if __name__ == "__main__":
    unittest.main()

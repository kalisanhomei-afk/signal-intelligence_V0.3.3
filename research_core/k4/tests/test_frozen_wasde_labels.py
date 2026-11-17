"""K4.6 frozen official WASDE outcome-label snapshot contract tests.

These labels are not ex-ante features; they never grant backtest/PIT eligibility.
"""
import json
import re
from decimal import Decimal
from pathlib import Path
import unittest

SNAPSHOT = Path(__file__).resolve().parents[1] / "cases" / "2021-2025-official-wasde-december-corn-revision-evidence.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")

class FrozenOfficialLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_labels_not_pit_or_predictive_features(self):
        d = self.data
        self.assertEqual(d["schema"], "signal-k46-usda-as-reported-december-corn-revision-evidence-v1")
        self.assertTrue(d["observations_retrieved_after_the_events"])
        self.assertFalse(d["prospective_fgis_feature_vintages_verified"])
        self.assertFalse(d["training_or_backtest_eligible"])
        self.assertFalse(d["investment_edge_verified"])
        self.assertFalse(d["trade_eligible"])

    def test_five_unambiguous_years_no_null_as_zero(self):
        r = self.data["observations"]
        self.assertEqual([x["marketing_year"] for x in r],
                         ["2021/22","2022/23","2023/24","2024/25","2025/26"])
        self.assertEqual(self.data["unavailable_years"],
                         ["2017/18","2018/19","2019/20","2020/21"])
        self.assertEqual(len({x["marketing_year"] for x in r}), 5)

    def test_revisions_account_and_sources_have_bytes_hashes(self):
        for row in self.data["observations"]:
            with self.subTest(year=row["marketing_year"]):
                exports_diff = Decimal(row["dec_exports_mbu"]) - Decimal(row["nov_exports_mbu"])
                stocks_diff = Decimal(row["dec_ending_stocks_mbu"]) - Decimal(row["nov_ending_stocks_mbu"])
                self.assertEqual(exports_diff, Decimal(row["delta_exports_mbu"]))
                self.assertEqual(stocks_diff, Decimal(row["delta_ending_stocks_mbu"]))
                self.assertEqual(stocks_diff+exports_diff, Decimal(row["other_net_stock_change_mbu"]))
                self.assertLess(row["nov_release_date"], row["dec_release_date"])
                for month in ("nov","dec"):
                    self.assertRegex(row["source_raw_sha256"][month], SHA256)
                    self.assertTrue(row["source_csv_urls"][month].startswith(
                        "https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-"))
                self.assertNotIn("independent_pit_features_verified", row)

    def test_true_zero_is_explicit_only_for_2021(self):
        rows={r["marketing_year"]:r for r in self.data["observations"]}
        self.assertEqual(Decimal(rows["2021/22"]["delta_exports_mbu"]),0)
        self.assertEqual(Decimal(rows["2021/22"]["delta_ending_stocks_mbu"]),0)
        self.assertEqual(Decimal(rows["2024/25"]["delta_exports_mbu"]),150)
        self.assertEqual(Decimal(rows["2024/25"]["delta_ending_stocks_mbu"]),-200)

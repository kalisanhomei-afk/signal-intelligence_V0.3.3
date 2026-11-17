import copy
import json
from pathlib import Path
import unittest
from research_core.k4.nine_year_revision_catalog import OLDER,NEWER,combine

def evidence():
    return json.loads(OLDER.read_text(encoding="utf-8")),json.loads(NEWER.read_text(encoding="utf-8"))

class NineYearCatalogTests(unittest.TestCase):
    def test_nine_years_and_revisions_reconciled(self):
        o,n=evidence();r=combine(o,n)
        self.assertEqual(r["marketing_years"],9)
        self.assertEqual(r["years_complete"][0],"2017/18")
        self.assertEqual(r["years_complete"][-1],"2025/26")
        self.assertEqual(r["export_revision_nonzero_years"],
                         ["2022/23","2023/24","2024/25","2025/26"])
        self.assertEqual(r["stocks_revision_nonzero_years"],
                         ["2017/18","2018/19","2022/23","2023/24","2024/25","2025/26"])
        self.assertEqual(r["other_balance_nonzero_years"],
                         ["2017/18","2018/19","2024/25"])

    def test_result_never_autocertifies_pit_or_strategy(self):
        o,n=evidence();r=combine(o,n)
        for k in ("fgis_features_by_announcement_asof_available",
                  "independent_historical_pit_certified",
                  "model_calibrated","out_of_sample_edge_verified",
                  "formal_backtest_eligible","trade_eligible"):
            self.assertIs(r[k],False)

    def test_missing_year_not_a_zero(self):
        o,n=evidence();o["rows"]=o["rows"][:-1]
        with self.assertRaisesRegex(ValueError,"YEAR_GAP_OR_DUPLICATE"):combine(o,n)

    def test_misleading_marketing_year_rejected(self):
        o,n=evidence();o["rows"][0]["marketing_year"]="2016/17"
        with self.assertRaisesRegex(ValueError,"YEAR_GAP_OR_DUPLICATE"):combine(o,n)

    def test_revision_tampering_rejected(self):
        o,n=evidence();o["rows"][0]["delta_ending_stocks_mbu"]=999
        with self.assertRaisesRegex(ValueError,"REVISION_RECONCILIATION_FAILURE"):combine(o,n)

    def test_other_balance_not_wholly_export_rejected(self):
        o,n=evidence();n["observations"][3]["other_net_stock_change_mbu"]=0
        with self.assertRaisesRegex(ValueError,"NON_EXPORT_BALANCE"):combine(o,n)

    def test_pit_claims_rejected(self):
        o,n=evidence();n["prospective_fgis_feature_vintages_verified"]=True
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_PIT_PROMOTION"):combine(o,n)

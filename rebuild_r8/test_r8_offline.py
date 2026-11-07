"""R8-A offline only. This does not test model quality or real-world truth."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r8_offline as r8


class R8OfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = r8.fact_catalog()
        cls.inputs = r8.read_json(r8.FIX / "mock_analysis_drafts.json")["drafts"]

    def draft(self, case="bea"):
        return copy.deepcopy(next(d for d in self.inputs if d["case_id"] == case))

    def assert_code(self, obj, code):
        with self.assertRaises(r8.DraftError) as caught:
            r8.validate_draft(obj, self.catalog)
        self.assertEqual(caught.exception.code, code)

    def test_full_fixture_pipeline_and_zero_api(self):
        out = r8.make_result(copy.deepcopy(self.inputs), self.catalog)
        self.assertEqual(out["api_calls_attempted"], 0)
        self.assertEqual(out["real_ai_drafts"], 0)
        self.assertEqual(out["mock_drafts"], 3)
        self.assertIs(out["publication_allowed"], False)
        self.assertFalse(out["human_approved"])

    def test_exact_catalog_count(self):
        self.assertEqual(self.catalog["fact_count"], 16)
        self.assertEqual({k: len(v) for k,v in self.catalog["sources"].items()}, {"bea": 6, "eia": 4, "arxiv": 6})

    def test_r4_catalog_sha_pin(self):
        self.assertEqual(r8.sha_file(r8.FIX / "fact_catalog_snapshot.json"), r8.EXPECTED_SOURCE_SNAPSHOT_SHA256)

    def test_every_mock_validates(self):
        for case in r8.CASE_NAMES:
            with self.subTest(case=case):
                self.assertEqual(r8.validate_draft(self.draft(case), self.catalog)["case_id"], case)

    def test_unknown_fact_id_fails(self):
        d = self.draft(); d["observation"]["fact_ids"] = ["F999"]
        self.assert_code(d, "INVALID_OR_CROSS_CASE_FACT")

    def test_cross_case_id_fails(self):
        d = self.draft(); d["importance"]["fact_ids"] = ["EIA-F001"]
        self.assert_code(d, "INVALID_OR_CROSS_CASE_FACT")

    def test_duplicate_fact_id_fails(self):
        d = self.draft(); d["impact"]["fact_ids"] = ["F001", "F001"]
        self.assert_code(d, "INVALID_FACT_IDS")

    def test_empty_fact_id_fails(self):
        d = self.draft(); d["observation"]["fact_ids"] = []
        self.assert_code(d, "INVALID_FACT_IDS")

    def test_digit_in_narrative_fails(self):
        d = self.draft(); d["impact"]["text"] = "商品變化將使收益上升 12%，需要特別關注。"
        self.assert_code(d, "MODEL_GENERATED_NUMBER")

    def test_digit_in_check_fails(self):
        d = self.draft(); d["next_checks"][0]["decision_test"] = "查明 2026 年的商品類別變化是否顯著"
        self.assert_code(d, "MODEL_GENERATED_NUMBER")

    def test_written_money_fails(self):
        d = self.draft(); d["interpretation"]["text"] = "官方數據指出已經增加三億美元，可能造成市場變化。"
        self.assert_code(d, "MODEL_GENERATED_NUMBER")

    def test_written_month_fails(self):
        d = self.draft(); d["observation"]["text"] += "並且發生於九月。"
        self.assert_code(d, "MODEL_GENERATED_NUMBER")

    def test_written_percentage_fails(self):
        d = self.draft(); d["observation"]["text"] += "作者稱百分之五十。"
        self.assert_code(d, "MODEL_GENERATED_NUMBER")

    def test_fact_id_with_digits_allowed_as_metadata(self):
        d = self.draft(); d["observation"]["fact_ids"] = ["F001", "F002"]
        self.assertEqual(r8.validate_draft(d, self.catalog)["fact_refs"][:2], ["F001", "F002"])

    def test_publication_request_fails(self):
        d = self.draft(); d["publication_allowed"] = True
        self.assert_code(d, "PUBLICATION_DENIED")

    def test_claim_type_mismatch_fails(self):
        d = self.draft(); d["interpretation"]["claim_type"] = "fact"
        self.assert_code(d, "WRONG_CLAIM_TYPE")

    def test_interpretation_requires_assumption(self):
        d = self.draft(); d["interpretation"]["assumptions"] = []
        self.assert_code(d, "MISSING_ASSUMPTIONS")

    def test_impact_requires_assumption(self):
        d = self.draft(); d["impact"]["assumptions"] = []
        self.assert_code(d, "MISSING_ASSUMPTIONS")

    def test_follow_up_must_be_actionable(self):
        d = self.draft(); d["next_checks"][0]["decision_test"] = "查證"
        self.assert_code(d, "INVALID_TEXT")

    def test_no_follow_up_fails(self):
        d = self.draft(); d["next_checks"] = []
        self.assert_code(d, "MISSING_FOLLOW_UP")

    def test_no_limitations_fails(self):
        d = self.draft(); d["limitations"] = []
        self.assert_code(d, "MISSING_LIMITATIONS")

    def test_unapproved_extra_keys_fails(self):
        d = self.draft(); d["human_approved"] = True
        self.assert_code(d, "INVALID_SCHEMA")

    def test_unsupported_certainty_fails(self):
        d = self.draft(); d["impact"]["text"] = "官方資料已經證實某個產業必然發生巨大變化。"
        self.assert_code(d, "UNSUPPORTED_CERTAINTY")

    def test_arxiv_fake_success_rate_fails(self):
        d = self.draft("arxiv"); d["observation"]["text"] += "這就是機器人的成功率。"
        self.assert_code(d, "CASE_SPECIFIC_PROHIBITED_CLAIM")

    def test_importance_tier_malformed(self):
        d = self.draft(); d["importance"]["tier"] = "全球第一"
        self.assert_code(d, "INVALID_IMPORTANCE")

    def test_missing_required_key_fails(self):
        d = self.draft(); del d["next_checks"]
        self.assert_code(d, "INVALID_SCHEMA")

    def test_full_set_needs_all_three_cases(self):
        with self.assertRaises(r8.DraftError) as caught:
            r8.make_result([self.draft("bea")], self.catalog)
        self.assertEqual(caught.exception.code, "INCOMPLETE_CASE_SET")

    def test_duplicate_cases_are_rejected(self):
        with self.assertRaises(r8.DraftError) as caught:
            r8.make_result([self.draft("bea"), self.draft("bea"), self.draft("eia")], self.catalog)
        self.assertEqual(caught.exception.code, "INCOMPLETE_CASE_SET")

    def test_html_escapes_model_text(self):
        out = r8.make_result(copy.deepcopy(self.inputs), self.catalog)
        out["cases"][0]["analysis"]["observation"]["text"] = "<script>alert('x')</script>"
        markup = r8.render_report(out)
        self.assertIn("&lt;script&gt;", markup)
        self.assertNotIn("<script>alert('x')</script>", markup)

    def test_render_display_number_from_catalog_only(self):
        out = r8.make_result(copy.deepcopy(self.inputs), self.catalog)
        page = r8.render_report(out)
        self.assertIn("21.9 billion USD", page)
        self.assertIn("52%", page)
        self.assertIn("不是當月實測值", page)

    def test_always_manual_unverified(self):
        out = r8.make_result(copy.deepcopy(self.inputs), self.catalog)
        self.assertTrue(all(not x["publication_allowed"] and not x["independently_verified"] for x in out["cases"]))
        self.assertIn("NOT VERIFIED", r8.render_report(out))

    def test_provenance_ids_and_urls(self):
        out = r8.make_result(copy.deepcopy(self.inputs), self.catalog)
        for case in out["cases"]:
            for fact in case["facts"].values():
                self.assertTrue(fact["source_evidence_id"])
                self.assertTrue(fact["source_url"].startswith("https://"))
                self.assertFalse(fact["independently_verified"])

    def test_mutated_catalog_in_memory_rejected_when_fact_invalid(self):
        broken = copy.deepcopy(self.catalog)
        broken["sources"]["bea"].pop("F001")
        with self.assertRaises(r8.DraftError):
            r8.validate_draft(self.draft(), broken)


if __name__ == "__main__":
    unittest.main(verbosity=2)

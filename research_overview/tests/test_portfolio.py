"""SIGNAL research portfolio: source-snapshot, no-lookahead and no-trading tests."""
from __future__ import annotations

from copy import deepcopy
import json
import tempfile
from pathlib import Path
import unittest

from research_overview.validate import (
    HERE, load_portfolio, validate_manifest, validate_card,
)
from research_overview.build_review import build_html, render_card

class ResearchPortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.cards = load_portfolio()
        cls.prs = {p["number"]: p for p in cls.manifest["prs"]}
        cls.by_id = {c["hypothesis_id"]: c for c in cls.cards}

    def test_two_frozen_research_cards_reproduce_verified_sources(self):
        self.assertEqual(len(self.cards),2)
        a=self.by_id["H-CORN-001"]
        b=self.by_id["H-NG-001"]
        self.assertEqual((a["forecast"]["value"],a["unit"]),(1758,"million_bushels"))
        self.assertEqual((b["forecast"]["value"],b["unit"]),(61,"Bcf"))
        self.assertEqual(a["forecast"]["frozen_proof"]["value"],
                         "54d4d7597d457c64307e9a2e1e5670cd5f1ecd52676180eded2a19a8ebcaca48")
        self.assertEqual(b["forecast"]["frozen_proof"]["value"],
                         "bacc82f549fb3bba74142139d89bec94e386d88e")
        self.assertFalse(a["decision"]["trade_eligible"])
        self.assertFalse(b["decision"]["trade_eligible"])

    def test_each_event_keeps_score_empty_until_official_result_arrives(self):
        for card in self.cards:
            official=card["official_outcome"]
            score=card["score"]
            if official["status"]=="NOT_RELEASED":
                self.assertIsNone(official["value"])
                self.assertIsNone(score["v0_absolute_error"])
                self.assertIsNone(score["consensus_absolute_error"])
                self.assertIsNone(score["v1_absolute_error"])
            else:
                self.assertEqual(official["status"],"RESEARCH_BRANCH_RAW_CAPTURED")
                self.assertEqual(score["v0_absolute_error"],
                                 abs(official["value"]-card["forecast"]["value"]))
                self.assertFalse(card["decision"]["trade_eligible"])

    def test_k5_indicative_calendar_is_not_consensus(self):
        card=self.by_id["H-NG-001"]
        self.assertEqual(card["indicative_external_forecasts"][0]["value"],69)
        self.assertEqual(card["market_consensus"]["status"],"NOT_VERIFIED")
        self.assertIsNone(card["market_consensus"]["value"])

    def test_main_is_registration_only_not_merged_research(self):
        m=self.manifest
        self.assertFalse(m["k38_main_registration"]["actual_capture_implementation_in_main"])
        self.assertEqual(m["k38_main_registration"]["default_branch_execution"],"INTENTIONAL_FAIL_CLOSED")
        self.assertFalse(m["publication"]["research_branch_results_in_main"])
        for number in (19,22,23):
            self.assertTrue(self.prs[number]["draft"])
            self.assertFalse(self.prs[number]["merged"])

    def test_version_mismatch_shown_not_hidden(self):
        self.assertEqual(self.manifest["publication"]["main_readme_label"],"SIGNAL V0.3.3")
        self.assertIn("V0.5.2a",self.manifest["publication"]["main_index_html_title"])
        self.assertFalse(self.manifest["publication"]["current_public_site_revision_verified"])

    def test_false_pr_merge_is_rejected(self):
        fake=deepcopy(self.manifest)
        fake["prs"][2]["merged"]=True
        with self.assertRaisesRegex(ValueError,"RESEARCH_PR_NOT_DRAFT"):
            validate_manifest(fake)

    def test_unverified_calendar_cannot_be_promoted_to_consensus(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["market_consensus"]["value"]=69
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_CONSENSUS_MUST_BE_NULL"):
            validate_card(fake,self.prs)

    def test_consensus_published_after_release_rejected(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        c=fake["market_consensus"]
        c.update({"status":"VERIFIED_PRE_RELEASE","value":69,
                  "raw_sha256":"a"*64,
                  "pre_event_capture_utc":"2026-11-19T15:30:00Z",
                  "source_url":"https://example.org/survey",
                  "methodology":"synthetic survey example"})
        with self.assertRaisesRegex(ValueError,"INVALID_PRE_RELEASE_CONSENSUS"):
            validate_card(fake,self.prs)

    def test_unbacked_future_result_rejected(self):
        fake=deepcopy(self.by_id["H-CORN-001"])
        fake["official_outcome"]["value"]=1600
        with self.assertRaisesRegex(ValueError,"FUTURE_OUTCOME_INVENTED"):
            validate_card(fake,self.prs)

    def test_numeric_score_requires_official_outcome(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["score"]["v0_absolute_error"]=0
        with self.assertRaisesRegex(ValueError,"FUTURE_SCORE_INVENTED"):
            validate_card(fake,self.prs)

    def test_trade_promotion_rejected(self):
        fake=deepcopy(self.by_id["H-CORN-001"])
        fake["decision"]["trade_eligible"]=True
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_INVESTMENT_PROMOTION"):
            validate_card(fake,self.prs)

    def test_source_hash_cannot_be_unknown(self):
        fake=deepcopy(self.by_id["H-CORN-001"])
        fake["evidence"]["prospective_raw_source_sha256"]=None
        with self.assertRaisesRegex(ValueError,"PRIOR_ORIGINAL_HASH_MISSING"):
            validate_card(fake,self.prs)

    def test_wrong_units_rejected(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["unit"]="MBtu"
        with self.assertRaisesRegex(ValueError,"INVALID_UNIT"):
            validate_card(fake,self.prs)

    def test_invalid_evidence_path_rejected(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["forecast"]["source_path"]="../../private/key.env"
        with self.assertRaisesRegex(ValueError,"FORECAST_SOURCE_PATH_MISMATCH"):
            validate_card(fake,self.prs)

    def test_research_pr_cannot_point_to_main(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["research_branch"]="main"
        with self.assertRaisesRegex(ValueError,"RESEARCH_BRANCH_MISMATCH"):
            validate_card(fake,self.prs)

    def test_k4_must_link_actual_frozen_forecast_not_scoring_contract(self):
        original=self.by_id["H-CORN-001"]
        self.assertEqual(original["forecast"]["source_path"],
            "research_core/k4/cases/2026-12-10-forward-baseline-forecast.json")
        fake=deepcopy(original)
        fake["forecast"]["source_path"]="research_core/k4/cases/2026-12-10-v0-scoring-contract.json"
        with self.assertRaisesRegex(ValueError,"FORECAST_ORIGINAL_PATH_MISMATCH"):
            validate_card(fake,self.prs)

    def test_k4_commit_anchor_cannot_drift(self):
        fake=deepcopy(self.by_id["H-CORN-001"])
        fake["forecast"]["source_commit_ref"]="a"*40
        with self.assertRaisesRegex(ValueError,"FORECAST_COMMIT_ANCHOR_MISMATCH"):
            validate_card(fake,self.prs)

    def test_k5_eia_original_commit_anchor_cannot_drift(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["evidence"]["source_commit_ref"]="b"*40
        with self.assertRaisesRegex(ValueError,"PRIOR_EVIDENCE_COMMIT_ANCHOR_MISMATCH"):
            validate_card(fake,self.prs)

    def test_manifest_rejects_missing_head_sha(self):
        fake=deepcopy(self.manifest)
        fake["prs"][2].pop("head_commit_sha")
        with self.assertRaisesRegex(ValueError,"RESEARCH_COMMIT_ANCHOR_MISSING"):
            validate_manifest(fake)

    def test_html_links_are_commit_pinned_not_mutable_head(self):
        a=self.by_id["H-CORN-001"]
        b=self.by_id["H-NG-001"]
        rendered=render_card(a,self.manifest["repository"])+render_card(b,self.manifest["repository"])
        for card in (a,b):
            self.assertIn("/blob/"+card["forecast"]["source_commit_ref"]+"/",rendered)
            self.assertIn(card["forecast"]["source_path"],rendered)
            self.assertIn(card["evidence"]["prospective_raw_source_path"],rendered)
        self.assertNotIn("/blob/codex/k4-corn-hypothesis-mvp/",rendered)
        self.assertNotIn("/blob/codex/k5-natural-gas-scout/",rendered)

    def test_html_is_readonly_static_and_renders_all_gates(self):
        html=build_html(self.manifest,self.cards)
        self.assertIn("H-CORN-001",html)
        self.assertIn("H-NG-001",html)
        self.assertIn("1,758",html.replace("1758","1,758"))  # numeric label present
        self.assertIn("2026-11-19T15:30:00Z",html)
        self.assertIn("No-Go",html)
        self.assertIn("非即時資料",html)
        self.assertNotIn("<script",html)
        self.assertNotIn("data:text/html",html)

    def test_html_escapes_untrusted_card_text(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["title"]="<script>alert(1)</script>"
        html=render_card(fake,self.manifest["repository"])
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)

    def test_review_can_be_written_offline(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"review.html"
            path.write_text(build_html(self.manifest,self.cards),encoding="utf-8")
            self.assertGreater(path.stat().st_size,5000)
            self.assertTrue(path.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_synthetic_post_release_K5_result_can_be_reviewed_without_rewriting_v0(self):
        # This is a DESIGN TEST ONLY. No Nov19 EIA outcome is supplied or asserted.
        future_head="c"*40
        manifest=deepcopy(self.manifest)
        manifest["prs"][3]["head_commit_sha"]=future_head
        self.assertIsNotNone(validate_manifest(manifest))
        indices={p["number"]:p for p in manifest["prs"]}
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["official_outcome"].update({
            "status":"RESEARCH_BRANCH_RAW_CAPTURED",
            "value":40,
            "raw_sha256":"b"*64,
            "capture_utc":"2026-11-19T15:40:00Z",
            "evidence_link":"https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/blob/"+
                future_head+"/research_core/k5/evidence/eia/SYNTHETIC_TEST_ONLY.json"
        })
        fake["score"]["v0_absolute_error"]=21
        self.assertEqual(validate_card(fake,indices),fake)
        self.assertEqual(fake["forecast"]["source_commit_ref"],
                         "f613719479c9ede0add2e6ff0893c0fa1831c765")
        self.assertIn("40 Bcf",render_card(fake,manifest["repository"]))
        self.assertFalse(fake["score"]["out_of_sample_edge_verified"])
        self.assertFalse(fake["decision"]["trade_eligible"])

    def test_synthetic_future_value_with_wrong_error_still_blocked(self):
        fake=deepcopy(self.by_id["H-NG-001"])
        fake["official_outcome"].update({
            "status":"RESEARCH_BRANCH_RAW_CAPTURED",
            "value":40,
            "raw_sha256":"b"*64,
            "capture_utc":"2026-11-19T15:40:00Z",
            "evidence_link":"https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/blob/"+
                "c"*40+"/research_core/k5/evidence/eia/SYNTHETIC_TEST_ONLY.json"
        })
        fake["score"]["v0_absolute_error"]=0
        with self.assertRaisesRegex(ValueError,"OUTCOME_SCORE_WRONG"):
            validate_card(fake,self.prs)

    def test_no_investment_promotion_in_portfolio_gate(self):
        m=deepcopy(self.manifest)
        m["programme_gates"]["alpha"]="VERIFIED"
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_READY_CLAIM"):
            validate_manifest(m)

if __name__ == "__main__":
    unittest.main()

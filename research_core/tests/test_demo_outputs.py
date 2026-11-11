import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_core import demo


class DemoOutputTests(unittest.TestCase):
    def test_all_required_outputs_and_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(demo, "OUT", Path(tmp)):
                report = demo.build_demo()
                self.assertTrue(report["all_passed"])
                self.assertEqual(report["case_count"], 7)
                for filename in ("observation_catalog.json", "asof_replay.json", "model_inputs.json", "qa_report.json", "review.html"):
                    self.assertTrue((Path(tmp) / filename).exists(), filename)
                inputs = json.loads((Path(tmp) / "model_inputs.json").read_text(encoding="utf-8"))
                self.assertTrue(inputs["not_a_forecast"])
                self.assertTrue(inputs["balance"]["balanced"])
                self.assertEqual(inputs["balance"]["reported_ending"], "1625")

    def test_replay_uses_original_then_revised_vintage(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(demo, "OUT", Path(tmp)):
                demo.build_demo()
                result = json.loads((Path(tmp) / "asof_replay.json").read_text(encoding="utf-8"))
                self.assertEqual({x["vintage_id"] for x in result["early"]["selected"]}, {"v1"})
                self.assertEqual({x["vintage_id"] for x in result["after_revision"]["selected"]}, {"v2"})

    def test_html_prominent_synthetic_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(demo, "OUT", Path(tmp)):
                demo.build_demo()
                html = (Path(tmp) / "review.html").read_text(encoding="utf-8")
                self.assertIn("完全合成", html)
                self.assertIn("不是 USDA 官方", html)
                self.assertIn("K1 驗收狀態", html)

    def test_fixture_never_claims_official_values(self):
        payload = demo.load_fixture()
        self.assertEqual(payload["fixture_type"], "SYNTHETIC_ONLY_NOT_USDA")
        for observation in payload["observations"]:
            self.assertEqual(observation["data_status"], "synthetic_fixture")


if __name__ == "__main__":
    unittest.main()

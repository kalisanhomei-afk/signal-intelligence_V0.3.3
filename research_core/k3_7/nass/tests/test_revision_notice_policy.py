"""Regression: generic USDA Revision Policy is not a specific revised edition.

Only synthetic fixtures are used in the offline suite. Real archived reports
are independently checked by the source QA workflow.
"""
import unittest
from pathlib import Path
from research_core.k3_7.nass import pipeline

SYNTH = Path(__file__).resolve().parents[1] / "fixtures/report_synthetic.txt"


class RevisionNoticeClassification(unittest.TestCase):
    def test_generic_revision_policy_is_not_an_actual_revision_notice(self):
        original = SYNTH.read_bytes()
        raw = original + (b"\nRevision Policy: Progress and condition estimates in the Crop "
                          b"Progress report are released after 4:00pm.\n"
                          b"These estimates are subject to revision the following week.\n")
        result = pipeline.parse_report(raw)
        self.assertFalse(result["revision_marker"])

    def test_explicit_revised_edition_is_identified(self):
        raw = SYNTH.read_bytes() + b"\nRevised edition\n"
        self.assertTrue(pipeline.parse_report(raw)["revision_marker"])

    def test_explicit_correction_notice_is_identified(self):
        raw = SYNTH.read_bytes() + b"\nCorrection Notice: changed condition values\n"
        self.assertTrue(pipeline.parse_report(raw)["revision_marker"])

    def test_plain_originality_still_not_certified(self):
        result = pipeline.parse_report(SYNTH.read_bytes())
        self.assertFalse(result["revision_marker"])
        # This flag does not prove the copy is the first edition.
        self.assertEqual(result["status"], "PARSED")


if __name__ == "__main__":
    unittest.main()

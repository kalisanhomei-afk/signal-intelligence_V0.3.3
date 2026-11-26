"""R1g contract tests: synthetic-only, fully offline, not market-model tests."""
import importlib.util
from pathlib import Path
import unittest

src = Path(__file__).resolve().parents[1] / "scripts" / "validate_capital_flow_receipts.py"
spec = importlib.util.spec_from_file_location("validate_capital_flow_receipts", src)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def fixture(**kwargs):
    r = {
        "schema": validator.SCHEMA,
        "source_id": "SYNTH_ALPHA", "dataset_id": "fictional_macro_01",
        "observation_month": "2020-01", "role": "feature",
        "value": 11.5, "unit": "synthetic_units",
        "source_release_utc": "2020-02-20T12:00:00Z",
        "retrieved_utc": None, "decision_cutoff_utc": "2020-02-28T21:00:00Z",
        "vintage_id": "synthetic-v1", "raw_sha256": None,
        "evidence_type": "SYNTHETIC", "rights_status": "NOT_APPLICABLE",
        "pit_status": "NOT_VERIFIED", "accepted_for_model": False,
    }
    r.update(kwargs)
    return r


class ReceiptGuardTests(unittest.TestCase):
    def test_valid_fixture_is_never_model_admitted(self):
        result = validator.inspect(fixture())
        self.assertTrue(result["structure_valid"])
        self.assertEqual(result["source_gate"], "BLOCKED")
        self.assertFalse(result["model_admitted"])

    def test_post_cutoff_feature_is_warned_not_admitted(self):
        result = validator.inspect(fixture(source_release_utc="2020-02-29T01:00:00Z"))
        self.assertTrue(result["structure_valid"])
        self.assertTrue(any("NO LOOKAHEAD" in w for w in result["warnings"]))

    def test_cutoff_equals_release_blocks(self):
        result = validator.inspect(fixture(source_release_utc="2020-02-28T21:00:00Z"))
        self.assertTrue(any("NO LOOKAHEAD" in w for w in result["warnings"]))

    def test_unknown_release_warns(self):
        result = validator.inspect(fixture(source_release_utc=None))
        self.assertTrue(any("PIT unsafe" in w for w in result["warnings"]))

    def test_synthetic_cannot_claim_hash_or_pit(self):
        result = validator.inspect(fixture(raw_sha256="0" * 64, pit_status="VERIFIED"))
        self.assertFalse(result["structure_valid"])
        self.assertGreaterEqual(len(result["errors"]), 2)

    def test_unverified_real_source_is_not_admitted(self):
        r = fixture(evidence_type="PUBLIC_METADATA_ONLY", source_id="SOURCE_X",
                    rights_status="UNVERIFIED", pit_status="PENDING")
        result = validator.inspect(r)
        self.assertTrue(result["structure_valid"])
        self.assertFalse(result["model_admitted"])
        self.assertTrue(any("rights" in w for w in result["warnings"]))

    def test_raw_hash_required_for_external_evidence(self):
        r = fixture(evidence_type="EXTERNAL_RAW_REPORTED", rights_status="UNVERIFIED",
                    retrieved_utc="2026-11-22T10:00:00Z")
        self.assertFalse(validator.inspect(r)["structure_valid"])

    def test_synthetically_perfect_rights_cannot_admit(self):
        r = fixture(evidence_type="LOCAL_RAW_VERIFIED", source_id="SOURCE_X",
                    rights_status="CLEARED", pit_status="VERIFIED", raw_sha256="b" * 64,
                    retrieved_utc="2026-11-22T10:00:00Z")
        result = validator.inspect(r)
        self.assertTrue(result["structure_valid"])
        self.assertFalse(result["model_admitted"])

    def test_outcome_cannot_be_used_as_feature(self):
        result = validator.inspect(fixture(role="outcome", source_release_utc="2020-03-05T10:00:00Z"))
        self.assertTrue(result["structure_valid"])
        self.assertTrue(any("outcome cannot" in w for w in result["warnings"]))

    def test_bad_numeric_or_timestamp_rejected(self):
        self.assertFalse(validator.inspect(fixture(value=float('nan')))["structure_valid"])
        self.assertFalse(validator.inspect(fixture(value=True))["structure_valid"])
        self.assertFalse(validator.inspect(fixture(decision_cutoff_utc="2020-02-28T21:00:00+00:00"))["structure_valid"])

    def test_malformed_types_rejected_cleanly(self):
        result = validator.inspect(fixture(role=[], evidence_type=[], rights_status=[]))
        self.assertFalse(result["structure_valid"])

    def test_missing_keys_rejected_cleanly(self):
        r = fixture()
        del r["source_id"]
        self.assertFalse(validator.inspect(r)["structure_valid"])
        self.assertFalse(validator.inspect(None)["structure_valid"])


if __name__ == "__main__":
    unittest.main()

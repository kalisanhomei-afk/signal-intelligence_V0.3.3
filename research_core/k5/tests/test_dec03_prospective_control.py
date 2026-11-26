"""Independent contract checks for the Dec 03 EIA persistence control.

No network, no new event outcome, no trading or inferred PIT certification.
The original forecast JSON is pinned to its first Git blob object ID.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parents[1] / "cases"
FORECAST = HERE / "2026-12-03-eia-frozen-v0-forecast.json"
NOV19 = HERE / "2026-11-19-eia-frozen-v0-forecast.json"
EXPECTED_NEW_BLOB = "7e78fe165b75dc13662d87b8f53b3172d712fe51"
EXPECTED_OLD_BLOB = "bacc82f549fb3bba74142139d89bec94e386d88e"


def blob_oid(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw).hexdigest()


def parsed(raw):
    return json.loads(raw.decode("utf-8"))


def utc(value):
    assert value.endswith("Z"), "UTC_ISO_8601_Z_REQUIRED"
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert d.tzinfo is not None and d.utcoffset().total_seconds() == 0
    return d


def validate(record):
    assert record["event_id"] == "EIA-WNGSR-2026-12-03", "WRONG_EVENT"
    assert record["target"] == "US_LOWER48_WORKING_GAS_WEEKLY_NET_CHANGE"
    assert record["unit"] == "Bcf"
    assert record["target_week_end"] == "2026-11-27"
    assert record["method_id"] == "PREVIOUS_RELEASE_WEEKLY_NET_CHANGE_UNCHANGED"
    assert record["baseline_observation_week_end"] == "2026-11-20"
    assert record["baseline_storage_asof_2026_11_20_bcf"] == 3858
    assert record["baseline_net_change_bcf"] == -24
    assert record["forecast_net_change_bcf"] == record["baseline_net_change_bcf"]
    assert utc(record["baseline_source_release_utc"]) <= utc(record["forecast_inputs_cutoff_utc"])
    assert utc(record["forecast_inputs_cutoff_utc"]) <= utc(record["forecast_created_utc"])
    assert utc(record["forecast_created_utc"]) < utc(record["release_scheduled_utc"])
    assert record["release_scheduled_utc"] == "2026-12-03T15:30:00Z"
    assert record["source_raw_sha256"] is None and record["source_raw_bytes_verified"] is False
    assert record["source_first_public_time_independently_verified"] is False
    assert record["market_consensus_bcf"] is None and record["consensus_pit_verified"] is False
    assert record["actual_next_release_net_change_bcf"] is None
    assert record["score_absolute_error_bcf"] is None
    assert record["independent_pit_certified"] is False and record["trade_eligible"] is False
    return True


class Dec03FrozenControlTests(unittest.TestCase):
    def setUp(self):
        self.raw = FORECAST.read_bytes()
        self.data = parsed(self.raw)

    def test_new_frozen_bytes_match_first_github_blob(self):
        self.assertEqual(blob_oid(self.raw), EXPECTED_NEW_BLOB)

    def test_previous_nov19_frozen_bytes_unchanged(self):
        self.assertEqual(blob_oid(NOV19.read_bytes()), EXPECTED_OLD_BLOB)

    def test_real_control_contract_and_no_future_outcome(self):
        self.assertTrue(validate(self.data))

    def test_tampered_target_week_rejected(self):
        x = dict(self.data, target_week_end="2026-11-20")
        with self.assertRaises(AssertionError):
            validate(x)

    def test_tampered_value_rejected(self):
        x = dict(self.data, forecast_net_change_bcf=-20)
        with self.assertRaises(AssertionError):
            validate(x)

    def test_pre_source_forecast_rejected(self):
        x = dict(self.data, forecast_created_utc="2026-11-25T16:59:00Z",
                 forecast_inputs_cutoff_utc="2026-11-25T16:59:00Z")
        with self.assertRaises(AssertionError):
            validate(x)

    def test_post_event_forecast_rejected(self):
        x = dict(self.data, forecast_created_utc="2026-12-03T15:31:00Z")
        with self.assertRaises(AssertionError):
            validate(x)

    def test_leaked_actual_outcome_rejected(self):
        x = dict(self.data, actual_next_release_net_change_bcf=-30)
        with self.assertRaises(AssertionError):
            validate(x)

    def test_fake_pit_and_consensus_rejected(self):
        x = dict(self.data, consensus_pit_verified=True)
        with self.assertRaises(AssertionError):
            validate(x)


if __name__ == "__main__":
    unittest.main()

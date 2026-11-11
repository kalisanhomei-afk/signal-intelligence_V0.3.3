import hashlib
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from research_core.asof_guard import check_asof, validate_forecast_inputs, select_asof, TimePolicy
from research_core.contracts import ContractError, ForecastRun, Observation, SourceSnapshot
from research_core.store import ImmutableStore
from research_core.tests.test_contracts import snapshots_and_observations


class AsOfAndStoreTests(unittest.TestCase):
    def setUp(self):
        self.fixture, snaps, self.obs = snapshots_and_observations()
        self.snaps = {s.snapshot_id: s for s in snaps}
        self.v1 = self.obs[:6]
        self.v2 = self.obs[6:]
        self.asof1 = self.fixture["as_of_before_revision"]
        self.asof2 = self.fixture["as_of_after_revision"]

    def test_asof_selects_initial_vintage(self):
        selected = select_asof(self.obs, self.snaps, self.asof1)
        self.assertEqual(len(selected), 6)
        self.assertEqual(selected["production"].vintage_id, "v1")
        self.assertEqual(selected["ending_stocks"].value, "1625")

    def test_asof_selects_revised_vintage(self):
        selected = select_asof(self.obs, self.snaps, self.asof2)
        self.assertEqual(len(selected), 6)
        self.assertEqual(selected["production"].vintage_id, "v2")
        self.assertEqual(selected["ending_stocks"].value, "1525")

    def test_earlier_asof_has_no_data(self):
        selected = select_asof(self.obs, self.snaps, "2026-01-09T10:00:00-05:00")
        self.assertEqual(selected, {})

    def test_future_data_rejected(self):
        with self.assertRaises(ContractError) as e:
            check_asof(self.v2[0], self.snaps[self.v2[0].snapshot_id], self.asof1)
        self.assertEqual(e.exception.code, "FUTURE_DATA")

    def test_retrieval_after_asof_rejected(self):
        mid = "2026-01-10T09:05:00-05:00"  # published 09:00, acquired only 09:10
        with self.assertRaises(ContractError) as e:
            check_asof(self.v1[0], self.snaps[self.v1[0].snapshot_id], mid)
        self.assertEqual(e.exception.code, "NOT_YET_RETRIEVED")

    def test_public_policy_labeled_and_permitted(self):
        mid = "2026-01-10T09:05:00-05:00"
        check_asof(self.v1[0], self.snaps[self.v1[0].snapshot_id], mid, policy=TimePolicy(require_local_retrieval=False))

    def test_observation_before_published_rejected(self):
        altered = replace(self.v1[0], available_at="2026-01-09T09:00:00-05:00")
        with self.assertRaises(ContractError) as e:
            check_asof(altered, self.snaps[altered.snapshot_id], self.asof1)
        self.assertEqual(e.exception.code, "AVAILABLE_BEFORE_PUBLICATION")

    def test_observation_after_retrieved_rejected(self):
        altered = replace(self.v1[0], available_at="2026-01-11T09:00:00-05:00")
        with self.assertRaises(ContractError) as e:
            check_asof(altered, self.snaps[altered.snapshot_id], self.asof2)
        self.assertEqual(e.exception.code, "UNAVAILABLE_AT_RETRIEVAL")

    def test_vintage_mismatch_rejected(self):
        altered = replace(self.v1[0], vintage_id="v2")
        with self.assertRaises(ContractError) as e:
            check_asof(altered, self.snaps[altered.snapshot_id], self.asof1)
        self.assertEqual(e.exception.code, "VINTAGE_MISMATCH")

    def test_snapshot_mismatch_rejected(self):
        with self.assertRaises(ContractError) as e:
            check_asof(self.v1[0], self.snaps[self.v2[0].snapshot_id], self.asof1)
        self.assertEqual(e.exception.code, "SNAPSHOT_MISMATCH")

    def test_missing_source_rejected(self):
        with self.assertRaises(ContractError) as e:
            select_asof(self.v1, {}, self.asof1)
        self.assertEqual(e.exception.code, "MISSING_SOURCE")

    def test_forecast_future_input_rejected(self):
        run = ForecastRun("F1", self.asof1, "ending_stocks", "MY2025/26", 30, "demo", [self.v2[0].observation_id], "1", "2", "3", "persistence")
        with self.assertRaises(ContractError) as e:
            validate_forecast_inputs(run, {o.observation_id: o for o in self.obs}, self.snaps)
        self.assertEqual(e.exception.code, "FUTURE_DATA")

    def test_forecast_valid_input(self):
        run = ForecastRun("F1", self.asof1, "ending_stocks", "MY2025/26", 30, "demo", [self.v1[0].observation_id], "1", "2", "3", "persistence")
        chosen = validate_forecast_inputs(run, {o.observation_id: o for o in self.obs}, self.snaps)
        self.assertEqual(chosen[0].observation_id, self.v1[0].observation_id)

    def test_different_period_same_series_rejected_for_ambiguous_replay(self):
        extra = replace(self.v1[0], observation_id="EXTRA", period="MY2024/25")
        with self.assertRaises(ContractError) as e:
            select_asof(self.v1 + [extra], self.snaps, self.asof1)
        self.assertEqual(e.exception.code, "AMBIGUOUS_SERIES_SCOPE")

    def test_store_rejects_bad_sha(self):
        with ImmutableStore(":memory:") as db:
            with self.assertRaises(ContractError) as e:
                db.add_snapshot(self.snaps[self.v1[0].snapshot_id], b"wrong data")
            self.assertEqual(e.exception.code, "HASH_MISMATCH")

    def populate(self, db):
        for source in self.fixture["snapshots"]:
            record = SourceSnapshot(**{k: v for k, v in source.items() if k != "raw_payload_utf8"})
            db.add_snapshot(record, source["raw_payload_utf8"].encode("utf-8"))
        for obs in self.obs:
            db.add_observation(obs)

    def test_store_roundtrip(self):
        with ImmutableStore(":memory:") as db:
            self.populate(db)
            self.assertEqual(len(db.all_observations()), 12)
            self.assertEqual(len(db.all_snapshots()), 2)

    def test_store_rejects_vintage_overwrite(self):
        with ImmutableStore(":memory:") as db:
            self.populate(db)
            source = self.fixture["snapshots"][0]
            record = SourceSnapshot(**{k: v for k, v in source.items() if k != "raw_payload_utf8"})
            with self.assertRaises(ContractError) as e:
                db.add_snapshot(record, source["raw_payload_utf8"].encode("utf-8"))
            self.assertEqual(e.exception.code, "IMMUTABLE_VINTAGE")

    def test_store_rejects_observation_overwrite(self):
        with ImmutableStore(":memory:") as db:
            self.populate(db)
            with self.assertRaises(ContractError) as e:
                db.add_observation(self.v1[0])
            self.assertEqual(e.exception.code, "IMMUTABLE_VINTAGE")

    def test_sqlite_update_rejected_by_trigger(self):
        with ImmutableStore(":memory:") as db:
            self.populate(db)
            with self.assertRaises(sqlite3.DatabaseError):
                db.conn.execute("UPDATE observations SET payload_json='{}' WHERE observation_id=?", (self.v1[0].observation_id,))

    def test_sqlite_delete_rejected_by_trigger(self):
        with ImmutableStore(":memory:") as db:
            self.populate(db)
            with self.assertRaises(sqlite3.DatabaseError):
                db.conn.execute("DELETE FROM snapshots WHERE snapshot_id=?", (self.v1[0].snapshot_id,))

    def test_store_missing_snapshot_rejected(self):
        with ImmutableStore(":memory:") as db:
            with self.assertRaises(ContractError) as e:
                db.add_observation(self.v1[0])
            self.assertEqual(e.exception.code, "MISSING_SOURCE")

    def test_store_observation_wrong_vintage_rejected(self):
        with ImmutableStore(":memory:") as db:
            src = self.fixture["snapshots"][0]
            db.add_snapshot(self.snaps[self.v1[0].snapshot_id], src["raw_payload_utf8"].encode("utf-8"))
            with self.assertRaises(ContractError) as e:
                db.add_observation(replace(self.v1[0], vintage_id="v999"))
            self.assertEqual(e.exception.code, "VINTAGE_MISMATCH")

    def test_file_persistence_and_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp) / "data.sqlite"
            with ImmutableStore(location) as db:
                self.populate(db)
            with ImmutableStore(location) as db:
                self.assertEqual(len(db.all_observations()), 12)
                self.assertEqual(db.get_snapshot(self.snaps[self.v2[0].snapshot_id].snapshot_id).vintage_id, "v2")


if __name__ == "__main__":
    unittest.main()

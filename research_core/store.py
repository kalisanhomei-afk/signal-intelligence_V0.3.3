"""Minimal append-only SQLite snapshot/observation store (for local K1 tests).

No credentials, API calls, cloud deployment, or real investment data.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path
from dataclasses import asdict
from .contracts import ContractError, SourceSnapshot, Observation
from .asof_guard import validate_observation_provenance

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    vintage_id TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_payload BLOB NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(source_id, vintage_id)
);
CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    series_id TEXT NOT NULL,
    period TEXT NOT NULL,
    frequency TEXT NOT NULL,
    vintage_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(snapshot_id, series_id, period, frequency)
);
CREATE TRIGGER IF NOT EXISTS snapshots_no_update BEFORE UPDATE ON snapshots
 BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END;
CREATE TRIGGER IF NOT EXISTS snapshots_no_delete BEFORE DELETE ON snapshots
 BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END;
CREATE TRIGGER IF NOT EXISTS observations_no_update BEFORE UPDATE ON observations
 BEGIN SELECT RAISE(ABORT, 'immutable observation'); END;
CREATE TRIGGER IF NOT EXISTS observations_no_delete BEFORE DELETE ON observations
 BEGIN SELECT RAISE(ABORT, 'immutable observation'); END;
"""


class ImmutableStore:
    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def add_snapshot(self, snapshot: SourceSnapshot, raw_payload: bytes) -> None:
        if not isinstance(raw_payload, bytes):
            raise ContractError("RAW_BYTES_REQUIRED", "raw snapshot must be bytes")
        actual = hashlib.sha256(raw_payload).hexdigest()
        if actual != snapshot.payload_sha256:
            raise ContractError("HASH_MISMATCH", f"{snapshot.snapshot_id}: raw bytes don't match declared digest")
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO snapshots(snapshot_id,source_id,vintage_id,payload_sha256,raw_payload,payload_json) VALUES(?,?,?,?,?,?)",
                    (snapshot.snapshot_id, snapshot.source_id, snapshot.vintage_id, actual, raw_payload, json.dumps(asdict(snapshot), ensure_ascii=False, sort_keys=True)),
                )
        except sqlite3.IntegrityError as exc:
            raise ContractError("IMMUTABLE_VINTAGE", f"snapshot already exists (or vintage reused): {snapshot.vintage_id}") from exc

    def get_snapshot(self, snapshot_id: str) -> SourceSnapshot | None:
        row = self.conn.execute("SELECT payload_json FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        return SourceSnapshot(**json.loads(row[0])) if row else None

    def add_observation(self, observation: Observation) -> None:
        snap = self.get_snapshot(observation.snapshot_id)
        if snap is None:
            raise ContractError("MISSING_SOURCE", observation.snapshot_id)
        validate_observation_provenance(observation, snap)
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO observations(observation_id,snapshot_id,series_id,period,frequency,vintage_id,payload_json) VALUES(?,?,?,?,?,?,?)",
                    (observation.observation_id, observation.snapshot_id, observation.series_id, observation.period, observation.frequency, observation.vintage_id, json.dumps(asdict(observation), ensure_ascii=False, sort_keys=True)),
                )
        except sqlite3.IntegrityError as exc:
            raise ContractError("IMMUTABLE_VINTAGE", f"observation already exists: {observation.observation_id}") from exc

    def all_snapshots(self) -> dict[str, SourceSnapshot]:
        rows = self.conn.execute("SELECT payload_json FROM snapshots ORDER BY snapshot_id").fetchall()
        instances = [SourceSnapshot(**json.loads(row[0])) for row in rows]
        return {record.snapshot_id: record for record in instances}

    def all_observations(self) -> list[Observation]:
        rows = self.conn.execute("SELECT payload_json FROM observations ORDER BY observation_id").fetchall()
        return [Observation(**json.loads(row[0])) for row in rows]

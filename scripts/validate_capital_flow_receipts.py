#!/usr/bin/env python3
"""Offline-only R1g provenance contract guard. NOT a PIT certification or model gate.

Validate a *small* source-agnostic research observation/receipt envelope. No
network, source downloads, database imports, signals, or financial calculations.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
from pathlib import Path

SCHEMA = "signal.global_capital_flow.observation.v0.1"
REQUIRED = frozenset({
    "schema", "source_id", "dataset_id", "observation_month", "role",
    "value", "unit", "source_release_utc", "retrieved_utc", "decision_cutoff_utc",
    "vintage_id", "raw_sha256", "evidence_type", "rights_status",
    "pit_status", "accepted_for_model",
})
ROLE = {"feature", "outcome"}
EVIDENCE = {"SYNTHETIC", "PUBLIC_METADATA_ONLY", "EXTERNAL_RAW_REPORTED", "LOCAL_RAW_VERIFIED"}
RIGHTS = {"NOT_APPLICABLE", "UNVERIFIED", "RESTRICTED", "CLEARED"}
PIT = {"NOT_VERIFIED", "PENDING", "VERIFIED"}
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
SHA = re.compile(r"^[a-f0-9]{64}$")
MONTH = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")


def utc(s: str | None, field: str, errors: list[str]) -> dt.datetime | None:
    if s is None:
        return None
    if not isinstance(s, str) or not ISO_UTC.fullmatch(s):
        errors.append(f"{field}: requires UTC ISO8601 with Z")
        return None
    try:
        return dt.datetime.fromisoformat(s[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{field}: invalid timestamp")
        return None


def inspect(record: object) -> dict:
    """Check structure and emit warnings, never grant Gate 0 or model admission."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(record, dict):
        return {"structure_valid": False, "errors": ["record: object required"],
                "warnings": [], "source_gate": "BLOCKED", "model_admitted": False}
    missing = sorted(REQUIRED - set(record))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if record.get("schema") != SCHEMA:
        errors.append("schema: unknown version")
    for key in ("source_id", "dataset_id", "unit", "vintage_id"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f"{key}: nonempty string required")
    if not isinstance(record.get("observation_month"), str) or not MONTH.fullmatch(record["observation_month"]):
        errors.append("observation_month: YYYY-MM required")
    if not isinstance(record.get("role"), str) or record["role"] not in ROLE:
        errors.append("role: feature or outcome required")
    v = record.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        errors.append("value: finite numeric value required (not bool)")
    for key, allowed in (("evidence_type", EVIDENCE), ("rights_status", RIGHTS), ("pit_status", PIT)):
        if not isinstance(record.get(key), str) or record[key] not in allowed:
            errors.append(f"{key}: invalid state")
    if record.get("accepted_for_model") is not False:
        errors.append("accepted_for_model: this preflight contract requires false")
    release = utc(record.get("source_release_utc"), "source_release_utc", errors)
    retrieved = utc(record.get("retrieved_utc"), "retrieved_utc", errors)
    cutoff = utc(record.get("decision_cutoff_utc"), "decision_cutoff_utc", errors)
    if cutoff is None:
        errors.append("decision_cutoff_utc: required; do not infer from observation month")
    if record.get("evidence_type") == "SYNTHETIC":
        if any(record.get(x) is not None for x in ("raw_sha256", "retrieved_utc")):
            errors.append("synthetic: raw hash and retrieval must be null")
        if record.get("rights_status") != "NOT_APPLICABLE":
            errors.append("synthetic: rights_status must be NOT_APPLICABLE")
        if record.get("pit_status") != "NOT_VERIFIED":
            errors.append("synthetic: cannot claim PIT verification")
    else:
        if record.get("rights_status") == "NOT_APPLICABLE":
            errors.append("real source: cannot set rights_status NOT_APPLICABLE")
        if isinstance(record.get("evidence_type"), str) and record["evidence_type"] in {"LOCAL_RAW_VERIFIED", "EXTERNAL_RAW_REPORTED"}:
            if not isinstance(record.get("raw_sha256"), str) or not SHA.fullmatch(record["raw_sha256"]):
                errors.append("raw evidence: 64-character sha256 required")
            if retrieved is None:
                errors.append("raw evidence: retrieved_utc required")
        elif record.get("raw_sha256") is not None:
            errors.append("metadata-only evidence: raw_sha256 must be null")
    if retrieved and release and retrieved < release:
        warnings.append("retrieval predates claimed release: verify source chronology")
    if record.get("role") == "feature":
        if release is None:
            warnings.append("feature release timestamp unknown; PIT unsafe")
        elif cutoff is not None and release >= cutoff:
            warnings.append("feature not released strictly before cutoff; NO LOOKAHEAD")
    if record.get("role") == "outcome":
        warnings.append("outcome cannot be used as an as-of forecasting feature")
    if not isinstance(record.get("rights_status"), str) or record["rights_status"] not in {"CLEARED", "NOT_APPLICABLE"}:
        warnings.append("rights not cleared for commercial/model use")
    if record.get("pit_status") != "VERIFIED":
        warnings.append("historical PIT not independently verified")
    return {"structure_valid": not errors, "errors": errors, "warnings": warnings,
            "source_gate": "BLOCKED", "model_admitted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path, help="Local fixture/metadata file only")
    args = parser.parse_args()
    result = inspect(json.loads(args.json_path.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["structure_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

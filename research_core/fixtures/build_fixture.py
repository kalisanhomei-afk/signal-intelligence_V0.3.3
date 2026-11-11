"""Build deterministic synthetic corn balance vintages; never present as USDA data."""
from __future__ import annotations
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

CORN_COMPONENTS = ("beginning_stocks", "production", "imports", "domestic_use", "exports", "ending_stocks")
BASE_VALUE = ("1700", "15000", "25", "12300", "2800", "1625")
REVISED_VALUE = ("1700", "14900", "25", "12300", "2800", "1525")


def create_fixture() -> dict:
    snapshots, observations = [], []
    for vintage, pub, retrieval, values in (
        ("v1", "2026-01-10T09:00:00-05:00", "2026-01-10T09:10:00-05:00", BASE_VALUE),
        ("v2", "2026-01-15T09:00:00-05:00", "2026-01-15T09:10:00-05:00", REVISED_VALUE),
    ):
        snapshot_id = f"SYN-CORN-{vintage}"
        raw = f"SYNTHETIC US CORN MY2025/26 VINTAGE {vintage}\n" + "\n".join(f"{k}={v} million_bushels" for k, v in zip(CORN_COMPONENTS, values)) + "\nNOT USDA DATA\n"
        snapshots.append({
            "snapshot_id": snapshot_id,
            "source_id": "synthetic_corn_supply_demand",
            "source_uri": "synthetic://signal/k1/us-corn-stockflow",
            "published_at": pub,
            "retrieved_at": retrieval,
            "vintage_id": vintage,
            "payload_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "rights_scope": "synthetic_internal_testing_only",
            "source_type": "synthetic_fixture",
            "schema_version": "1.0",
            "raw_payload_utf8": raw,
        })
        for key, value in zip(CORN_COMPONENTS, values):
            observations.append({
                "observation_id": f"SYN-{vintage}-{key}",
                "series_id": key,
                "value": value,
                "unit": "million_bushels",
                "period": "MY2025/26",
                "frequency": "marketing_year",
                "available_at": pub,
                "data_status": "synthetic_fixture",
                "snapshot_id": snapshot_id,
                "vintage_id": vintage,
                "commodity": "corn",
                "geography": "US",
                "measurement_basis": "synthetic_US_corn_marketing_year_stockflow",
                "schema_version": "1.0",
            })
    return {
        "fixture_type": "SYNTHETIC_ONLY_NOT_USDA",
        "description": "Purely illustrative, invented US corn stocks and flows in million bushels; do not use to trade.",
        "snapshots": snapshots,
        "observations": observations,
        "as_of_before_revision": "2026-01-12T10:00:00-05:00",
        "as_of_after_revision": "2026-01-16T10:00:00-05:00",
    }


if __name__ == "__main__":
    target = Path(__file__).with_name("synthetic_corn_vintages.json")
    target.write_text(json.dumps(create_fixture(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)

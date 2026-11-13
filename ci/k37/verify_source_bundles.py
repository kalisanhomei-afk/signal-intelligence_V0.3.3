"""Fail-closed integrity check for K3.7 official-source bundles (never PIT certification)."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

RUN = 43448555468
ARTIFACT_IDS = {
    "wasde": 14049815789, "nass": 14049291864, "pit": 14049231951
}
PILOT = {"2016", "2020", "2022"}


def require(test, message):
    if not test:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def verify_raw(root, folder):
    directory = root / folder
    require(directory.is_dir(), f"Missing raw directory {folder}")
    objects = list(directory.glob("*.bin"))
    require(len(objects) > 0, f"No raw source bytes in {folder}")
    for file in objects:
        require(re.fullmatch(r"[0-9a-f]{64}\.bin", file.name) is not None, "Unexpected raw filename")
        require(sha256(file) == file.stem, f"Corrupt source: {file.name}")
    return {file.stem for file in objects}


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def audit(root):
    result = {"source_run_id": RUN, "artifact_ids": ARTIFACT_IDS,
              "status": "SOURCE_RAW_BYTES_VERIFIED_PIT_UNVERIFIED",
              "pit_certified": False, "verified_historical_public_timestamps": 0}
    w = root / "wasde"
    wm = read_json(w / "wasde/manifest.json")
    wh = verify_raw(w, "wasde_raw")
    require(wm["status"] == "COLLECTED_PIT_UNVERIFIED", "Unexpected WASDE collection status")
    require(wm["verified_pit_records"] == 0, "WASDE PIT certification unexpectedly nonzero")
    for src in [wm["archive"], *wm["sources"]]:
        if "source_sha256" in src:
            require(src["source_sha256"] in wh, "WASDE manifest references absent raw content")
            require(src["raw_file"] == src["source_sha256"] + ".bin", "WASDE raw path mismatch")
    wr = read_csv(w / "wasde/wasde_vintages.csv")
    wy = Counter(r["release_date"][:4] for r in wr)
    require(set(wy) == PILOT, "WASDE missing pilot year")
    require(len(wr) == wm["records"] and len(wr) > 0, "WASDE row mismatch")
    require(wm["coverage_counts"].get("OBSERVED") == 36, "WASDE months not 36")
    require(all(r.get("source_sha256") in wh for r in wr), "WASDE CSV references absent raw bytes")

    n = root / "nass"
    nq = read_json(n / "nass-out/quality_report.json")
    nh = verify_raw(n, "nass-bundle/raw")
    ledger = [json.loads(line) for line in
              (n / "nass-bundle/source_manifest.jsonl").read_text(encoding="utf-8").splitlines()
              if line.strip()]
    for rec in ledger:
        if rec.get("status") == "DOWNLOADED":
            require(rec["source_sha256"] in nh, "NASS manifest references absent raw content")
            require(rec["raw_path"] == "raw/" + rec["source_sha256"] + ".bin", "NASS raw path mismatch")
    nr = read_csv(n / "nass-out/nass_state_weekly.csv")
    ny = Counter(r["calendar_year"] for r in nr)
    require(set(ny) == PILOT, "NASS missing pilot year")
    require(len(nr) == nq["observation_rows"] and len(nr) > 0, "NASS row mismatch")
    require(nq["verified_public_timestamp_rows"] == 0, "Unexpected NASS PIT timestamp")
    require(all(r.get("source_sha256") in nh for r in nr), "NASS CSV references absent raw bytes")

    p = root / "pit"
    access = read_json(p / "pit-locators/source_access.json")
    mirror = read_json(p / "pit-locators/official_mirror_probe.json")
    require(len(access) == 3, "PIT locator count mismatch")
    require(mirror["status"] == "FETCHED_LOCATOR_NOT_TIME_EVIDENCE",
            "Official mirror not accessible")
    for src in [*access, mirror]:
        if src["status"] == "FETCHED_LOCATOR_NOT_TIME_EVIDENCE":
            require(sha256(p / "pit-locators" / src["source_path"]) == src["source_sha256"],
                    "PIT locator raw checksum mismatch")
    result["datasets"] = {
        "wasde": {"rows": len(wr), "by_year": dict(wy), "raw_objects_sha256_verified": len(wh),
                  "status": wm["status"]},
        "nass": {"rows": len(nr), "by_year": dict(ny), "raw_objects_sha256_verified": len(nh),
                 "reports_downloaded": sum(r.get("status") == "DOWNLOADED" and
                                           r.get("role") == "report" for r in ledger),
                 "status": nq["status"]},
        "pit": {"primary_locators_attempted": len(access), "official_mirror_reachable": True,
                "historical_timestamps_certified": 0}
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    opts = parser.parse_args()
    opts.output.mkdir(parents=True, exist_ok=True)
    result = audit(opts.input)
    (opts.output / "source_artifact_audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

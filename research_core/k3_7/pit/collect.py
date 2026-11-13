"""Optional online locator probe; never manufactures historical release records.

Download receipts use this process's wall clock, never Date/Last-Modified or a
date in the URL/document. Source feasibility probes and offline audit are separate.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .audit import AuditError, official, sha, url_host

LOCATORS = (
    "https://www.usda.gov/historical-wasde-report-data-3",
    "https://esmis.nal.usda.gov/publication/crop-progress",
    "https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Crop_Progress_and_Condition/",
)
MAX_BYTES = 4_000_000


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official(url_host(newurl)):
            raise AuditError("NON_OFFICIAL_REDIRECT", newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def capture(url: str, output: Path, name: str, *, opener=None, clock=now) -> dict:
    if not official(url_host(url)):
        raise AuditError("NON_OFFICIAL_SOURCE", url)
    if Path(name).name != name or name in {"", ".", ".."}:
        raise AuditError("INVALID_ARTIFACT_NAME")
    output.mkdir(parents=True, exist_ok=True)
    # Append-only capture names avoid overwriting a prior vintage or receipt.
    raw_path = output / (name + ".raw")
    receipt_path = output / (name + ".receipt.json")
    if raw_path.exists() or receipt_path.exists():
        raise AuditError("CAPTURE_ALREADY_EXISTS", name)
    attempted = clock()
    result = {"url": url, "attempted_at_utc": attempted, "completed_at_utc": "",
              "status": "SOURCE_UNAVAILABLE", "retrieved_at_utc": "",
              "source_sha256": "", "error": ""}
    opener = opener or build_opener(OfficialRedirects())
    try:
        request = Request(url, headers={"User-Agent": "SIGNAL-K37-PIT-research/1.0"})
        with opener.open(request, timeout=20) as response:
            if not official(url_host(response.geturl())):
                raise AuditError("NON_OFFICIAL_REDIRECT", response.geturl())
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise AuditError("OVERSIZED_SOURCE")
            finished = clock()
            receipt = {"kind": "SIGNAL_HTTP_DOWNLOAD_V1", "source_url": url,
                       "resolved_url": response.geturl(), "source_sha256": sha(raw),
                       "started_at_utc": attempted, "finished_at_utc": finished}
        with raw_path.open("xb") as stream:
            stream.write(raw)
        with receipt_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
        result.update(status="FETCHED_LOCATOR_NOT_TIME_EVIDENCE", completed_at_utc=finished,
                      retrieved_at_utc=finished, source_sha256=sha(raw),
                      source_path=raw_path.name, retrieval_receipt_path=receipt_path.name,
                      retrieval_receipt_sha256=sha(receipt_path.read_bytes()))
    except (HTTPError, URLError, OSError, AuditError) as exc:
        result.update(completed_at_utc=clock(), error=f"{type(exc).__name__}: {exc}")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New append-only capture bundle")
    args = parser.parse_args(argv)
    if (args.output / "source_access.json").exists():
        parser.error("source_access.json already exists; use a new capture directory")
    results = [capture(url, args.output, f"locator-{i}") for i, url in enumerate(LOCATORS, 1)]
    (args.output / "source_access.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"attempts": len(results), "fetched": sum(bool(r["source_sha256"]) for r in results)}))
    return 0 if all(r["source_sha256"] for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())

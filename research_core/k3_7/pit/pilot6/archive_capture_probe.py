"""PIT6 independent historical-capture INDEX probe (not PIT certification).

Bounded source-specific queries to independent Internet Archive and Common Crawl
indices. A historical capture *index entry* does not prove the particular value
was present in captured bytes. All resulting records stay PIT_UNVERIFIED.
Internet access failures remain UNAVAILABLE, never NO_CAPTURE.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

SOURCES = {
    2016: ("CC-MAIN-2016-26", "CC-MAIN-2016-30"),
    2020: ("CC-MAIN-2020-29", "CC-MAIN-2020-34"),
    2022: ("CC-MAIN-2022-27", "CC-MAIN-2022-33"),
}
ALLOW_HOSTS = {"archive.org", "web.archive.org", "index.commoncrawl.org"}
LIMIT = 750_000
TIMEOUT = 10


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def iso_ts(v):
    if not isinstance(v, str) or not re.fullmatch(r"\d{14}", v):
        raise ValueError("Invalid archival UTC timestamp")
    return datetime.strptime(v, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def query(url, opener=None):
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in ALLOW_HOSTS or p.username or p.password or p.fragment:
        raise ValueError("Archive query host not approved")
    opener = opener or urlopen
    req = Request(url, headers={"User-Agent": "SIGNAL-K37-independent-archive-evidence/1.0"})
    try:
        with opener(req, timeout=TIMEOUT) as response:
            redirect = urlparse(response.geturl())
            if redirect.scheme != "https" or redirect.hostname not in ALLOW_HOSTS:
                raise ValueError("Archive redirect host not approved")
            raw = response.read(LIMIT + 1)
            if len(raw) > LIMIT:
                return {"status": "RESPONSE_OVERSIZED", "request_url": url}
            return {"status": "HTTP_OK", "request_url": url, "bytes_sha256": hashlib.sha256(raw).hexdigest(),
                    "body": raw.decode("utf-8-sig", errors="replace")}
    except HTTPError as e:
        return {"status": "HTTP_ERROR", "request_url": url, "http_status": e.code}
    except (URLError, TimeoutError, OSError, ValueError) as e:
        return {"status": "SOURCE_UNAVAILABLE", "request_url": url,
                "error": f"{type(e).__name__}: {str(e)[:180]}"}


def date_window(record):
    first = date.fromisoformat(record["release_date"])
    last = first + timedelta(days=180)
    return first, last


def in_window(timestamp, first, last):
    try:
        day = datetime.fromisoformat(iso_ts(timestamp).replace("Z", "+00:00")).date()
        return first <= day <= last
    except (TypeError, ValueError):
        return False


def parse_wayback_cdx(response, first, last):
    if response["status"] != "HTTP_OK":
        return {"state": "INDEX_UNAVAILABLE", "status": response["status"], "index_http_status": response.get("http_status")}
    try:
        data = json.loads(response["body"])
        if not isinstance(data, list) or not data:
            raise ValueError("Index result missing header")
        fields = data[0]
        records = [dict(zip(fields, v)) for v in data[1:] if len(v) == len(fields)]
        hits = [{"capture_at_utc": iso_ts(r["timestamp"]), "archived_url": r["original"],
                 "capture_digest": r.get("digest", "")} for r in records
                if r.get("statuscode") == "200" and in_window(r.get("timestamp"), first, last)]
        return {"state": "CANDIDATE_INDEX_HITS" if hits else "INDEX_QUERY_NO_WINDOW_HITS",
                "capture_entries_in_180day_window": hits[:8], "total_hits_in_window": len(hits)}
    except (KeyError, ValueError, TypeError) as e:
        return {"state": "INDEX_RESPONSE_UNPARSABLE", "error": str(e)[:150]}


def parse_commoncrawl(response, first, last):
    if response["status"] == "HTTP_ERROR" and response.get("http_status") == 404:
        return {"state": "INDEX_QUERY_NO_MATCH", "total_hits_in_window": 0, "capture_entries_in_180day_window": []}
    if response["status"] != "HTTP_OK":
        return {"state": "INDEX_UNAVAILABLE", "status": response["status"], "index_http_status": response.get("http_status")}
    try:
        recs = [json.loads(line) for line in response["body"].splitlines() if line.strip()]
        hits = [{"capture_at_utc": iso_ts(r["timestamp"]), "archived_url": r["url"],
                 "capture_digest": r.get("digest", ""), "warc_file": r.get("filename", ""),
                 "warc_offset": r.get("offset", ""), "warc_length": r.get("length", "")}
                for r in recs if str(r.get("status")) == "200"
                and in_window(r.get("timestamp"), first, last)]
        return {"state": "CANDIDATE_INDEX_HITS" if hits else "INDEX_QUERY_NO_WINDOW_HITS",
                "capture_entries_in_180day_window": hits[:8], "total_hits_in_window": len(hits)}
    except (KeyError, ValueError, TypeError) as e:
        return {"state": "INDEX_RESPONSE_UNPARSABLE", "error": str(e)[:150]}


def parse_availability(response, first, last):
    if response["status"] != "HTTP_OK":
        return {"state": "INDEX_UNAVAILABLE", "status": response["status"], "index_http_status": response.get("http_status")}
    try:
        obj = json.loads(response["body"])
        capture = obj.get("archived_snapshots", {}).get("closest")
        if not capture:
            return {"state": "NO_CLOSEST_CAPTURE_REPORTED", "total_hits_in_window": 0}
        ts = capture.get("timestamp", "")
        # Closest may be years later. Do not accept it without explicit UTC range.
        if not in_window(ts, first, last):
            return {"state": "CLOSEST_CAPTURE_OUTSIDE_WINDOW", "nearest_capture_at_utc": iso_ts(ts),
                    "total_hits_in_window": 0}
        return {"state": "CANDIDATE_INDEX_HITS",
                "total_hits_in_window": 1, "capture_entries_in_180day_window": [
                    {"capture_at_utc": iso_ts(ts), "archived_url": capture.get("url", ""),
                     "index_status": capture.get("status", "")}]}
    except (KeyError, ValueError, TypeError) as e:
        return {"state": "INDEX_RESPONSE_UNPARSABLE", "error": str(e)[:150]}


def scrub(resp):
    return {k: v for k, v in resp.items() if k != "body"}


def run(catalog, output, requester=query):
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    cases = payload["records"]
    if len(cases) != 6:
        raise ValueError("Require exact six fixed source cases")
    report = {"schema": "signal-k37-independent-capture-index-pilot-v1",
              "generated_at_utc": now(), "source_catalog_schema": payload["schema"],
              "window_days_after_nominal_report": 180, "cases": [],
              "verified_contemporaneous_page_values": 0, "pit_certified_rows": 0,
              "historical_public_timestamp_certified": 0, "formal_backtest_eligible": False}
    for r in cases:
        if r.get("pit_certified") or r.get("available_at_utc") or r.get("timestamp_quality") != "UNKNOWN":
            raise ValueError("Refuse upstream PIT status promotion")
        first, last = date_window(r)
        # The submitted article URL is candidate identity only; the media site could edit it.
        url = r["content_evidence_url"]
        endpoints = [
            ("IA_AVAILABILITY", "https://archive.org/wayback/available?" +
             urlencode({"url": url, "timestamp": last.strftime("%Y%m%d")}), parse_availability),
            ("IA_CDX", "https://web.archive.org/cdx/search/cdx?" +
             urlencode({"url": url, "from": first.year, "to": last.year,
                        "output": "json", "filter": "statuscode:200",
                        "fl": "timestamp,original,digest,statuscode", "limit": 8}), parse_wayback_cdx)
        ]
        for cid in SOURCES[r["year"]]:
            endpoints.append(("CC_" + cid, f"https://index.commoncrawl.org/{cid}-index?" +
                              urlencode({"url": url, "output": "json"}), parse_commoncrawl))
        checks = []
        for name, endpoint, processor in endpoints:
            res = requester(endpoint)
            parsed = processor(res, first, last)
            checks.append({"provider": name, "query": endpoint, "retrieved_now_utc": now(),
                           "response": scrub(res), **parsed})
        hits = sum(z.get("total_hits_in_window", 0) for z in checks)
        report["cases"].append({
            "kind": r["kind"], "year": r["year"], "nominal_release_date": r["release_date"],
            "expected_value": r["official_numeric_value"], "target_media_url": url,
            "queries": checks, "candidate_archive_index_hits": hits,
            "capture_body_verified": False, "publisher_publication_time_verified": False,
            "metric_historical_public_time_verified": False, "timestamp_quality": "UNKNOWN",
            "pit_certified": False, "disposition":
            "INDEX_CANDIDATES_REQUIRE_WARC_OR_REPLAY_CONTENT_VERIFICATION" if hits
            else "NO_VERIFIABLE_HISTORICAL_SNAPSHOT_YET",
        })
    report["total_candidate_index_hits"] = sum(z["candidate_archive_index_hits"] for z in report["cases"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "historical_capture_index_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(report["cases"]), "candidate_index_hits": report["total_candidate_index_hits"],
                      "PIT_CERTIFIED": 0, "source_index_states":
                      {f"{x['year']}-{x['kind']}": [z["state"] for z in x["queries"]] for x in report["cases"]}},
                     ensure_ascii=False, sort_keys=True))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run(args.catalog, args.output)


if __name__ == "__main__":
    main()

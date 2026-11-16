"""Read historical Wayback/CC capture payload, verify only target numerical value.

Public web archive indexes alone are insufficient. This module saves only
capture metadata, hashes, and a content-match boolean; never republishes copyrighted
article HTML. A successful content match bounds observed public *value* by the
archive capture instant, not original USDA file availability or media posting time.
The downstream PIT certification decision remains explicitly CLOSED.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import gzip
from email.utils import parsedate_to_datetime
import hashlib
from html import unescape
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_DOWNLOAD = 1_500_000
MAX_DECOMPRESSED = 3_000_000
ARCHIVE_HOSTS = {"web.archive.org", "data.commoncrawl.org"}
TIMEOUT = 14


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_open(url, *, request_headers=None, max_bytes=MAX_DOWNLOAD):
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in ARCHIVE_HOSTS or p.username or p.password or p.fragment:
        return {"status": "REJECTED_UNTRUSTED_ARCHIVE_HOST"}
    headers = {"User-Agent": "SIGNAL-K37-independent-historical-source/1.0", "Accept-Encoding": "identity"}
    headers.update(request_headers or {})
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=TIMEOUT) as r:
            redirect = urlparse(r.geturl())
            if redirect.scheme != "https" or redirect.hostname not in ARCHIVE_HOSTS:
                return {"status": "UNAPPROVED_ARCHIVE_REDIRECT"}
            code = r.status
            if request_headers and "Range" in request_headers and code != 206:
                return {"status": "RANGE_REQUEST_NOT_HONORED", "http_status": code}
            raw = r.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return {"status": "ARCHIVE_PAYLOAD_OVERSIZED"}
            return {"status": "FETCHED", "http_status": code, "raw": raw,
                    "resolved_url": r.geturl(),
                    "memento_datetime_header": r.headers.get("Memento-Datetime", ""),
                    "capture_sha256": hashlib.sha256(raw).hexdigest()}
    except HTTPError as e:
        return {"status": "ARCHIVE_HTTP_ERROR", "http_status": e.code}
    except (URLError, TimeoutError, OSError) as e:
        return {"status": "ARCHIVE_ACCESS_UNAVAILABLE", "error": str(e)[:180]}


def normalize_html(raw):
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]*>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).lower()


def match_target_text(text, kind, year):
    # Require crop context. A bare 75% or 2.008 somewhere on a page is not proof.
    if kind == "WASDE":
        value = {2016: r"(?:2[.]008\s+billion|2[,]008\s+million)",
                 2020: r"(?:3[.]323\s+billion|3[,]323\s+million)",
                 2022: r"(?:1[.]485\s+billion|1[,]485\s+million)"}[year]
        for m in re.finditer(value, text, re.I):
            context = text[max(0, m.start()-200):m.end()+100]
            if "corn" in context and ("stock" in context or "usda" in context):
                return True
    else:
        patt = {2016: r"75\s*%", 2020: r"75\s*%", 2022: r"73\s*%"}[year]
        for m in re.finditer(patt, text, re.I):
            context = text[max(0, m.start()-220):m.end()+220]
            if "corn" in context and ("good" in context or "excellent" in context):
                return True
    return False


def warc_content(raw):
    # Official CC index provides a precise compressed member; no full WARC download.
    try:
        decompressed = gzip.decompress(raw)
    except (gzip.BadGzipFile, EOFError, OSError) as e:
        raise ValueError("Common Crawl member not valid gzip") from e
    if len(decompressed) > MAX_DECOMPRESSED:
        raise ValueError("WARC member too large")
    if not decompressed.startswith(b"WARC/"):
        raise ValueError("Not a WARC response member")
    return decompressed


def verify_warc_identity(body, expected_url, expected_utc):
    text = body.split(b"\r\n\r\n", 1)[0].decode("utf-8", errors="replace")
    headers = {}
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.lower().strip()] = val.strip()
    if headers.get("warc-type", "").lower() != "response":
        return False
    target = urlparse(headers.get("warc-target-uri", ""))
    expected = urlparse(expected_url)
    if (target.hostname or "").removeprefix("www.") != (expected.hostname or "").removeprefix("www."):
        return False
    if target.path.rstrip("/") != expected.path.rstrip("/"):
        return False
    try:
        observed = datetime.fromisoformat(headers["warc-date"].replace("Z", "+00:00")).astimezone(timezone.utc)
        wanted = datetime.fromisoformat(expected_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        return abs((observed - wanted).total_seconds()) <= 2
    except (KeyError, ValueError):
        return False


def case_entries(case):
    found = set()
    for q in case["queries"]:
        for c in q.get("capture_entries_in_180day_window", []):
            provider = q["provider"]
            typ = "COMMON_CRAWL" if provider.startswith("CC_") else "WAYBACK"
            key = (typ, c["capture_at_utc"])
            if key in found:
                continue
            found.add(key)
            yield typ, c


def inspect(case, typ, capture):
    observed = capture["capture_at_utc"]
    if typ == "WAYBACK":
        stamp = re.sub(r"[^0-9]", "", observed)
        url = f"https://web.archive.org/web/{stamp}id_/{case['target_media_url']}"
        result = safe_open(url)
    else:
        offset = int(capture["warc_offset"])
        length = int(capture["warc_length"])
        if offset < 0 or not 0 < length <= 500_000:
            return {"type": typ, "capture_at_utc": observed, "status": "INVALID_WARC_RANGE",
                    "value_matched": False}
        url = "https://data.commoncrawl.org/" + capture["warc_file"]
        result = safe_open(url, request_headers={"Range": f"bytes={offset}-{offset+length-1}"},
                           max_bytes=length + 50)
    item = {"type": typ, "capture_at_utc": observed, "capture_source_url": url,
            "archive_index_digest": capture.get("capture_digest", ""),
            "status": result["status"], "http_status": result.get("http_status"),
            "archive_payload_sha256": result.get("capture_sha256", ""),
            "resolved_capture_url": result.get("resolved_url", ""),
            "memento_datetime_header": result.get("memento_datetime_header", ""),
            "value_matched": False, "pit_certified": False}
    if result["status"] != "FETCHED":
        item["error"] = result.get("error", "")
        return item
    if typ == "WAYBACK":
        # Wayback may silently redirect a request to another capture time.
        # Never label content with the requested instant unless the actual
        # replay URL resolves to the same 14-digit historical capture.
        replay_path = urlparse(result.get("resolved_url", "")).path
        match = re.match(r"^/web/(\d{14})(?:id_)?/", replay_path)
        required = re.sub(r"[^0-9]", "", observed)
        if not match or match.group(1) != required:
            item["status"] = "ARCHIVED_CAPTURE_REDIRECT_TIME_MISMATCH"
            return item
        # Require archive server's Memento record to agree with the replay instant.
        header = result.get("memento_datetime_header", "")
        try:
            recorded = parsedate_to_datetime(header).astimezone(timezone.utc)
            demanded = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            if abs((recorded - demanded).total_seconds()) > 1:
                item["status"] = "MEMENTO_HEADER_TIMESTAMP_MISMATCH"
                return item
        except (TypeError, ValueError):
            item["status"] = "MEMENTO_HEADER_MISSING_OR_INVALID"
            return item
    try:
        body = warc_content(result["raw"]) if typ == "COMMON_CRAWL" else result["raw"]
        if typ == "COMMON_CRAWL" and not verify_warc_identity(body, case["target_media_url"], observed):
            item["status"] = "COMMON_CRAWL_WARC_IDENTITY_MISMATCH"
            return item
        val = match_target_text(normalize_html(body), case["kind"], case["year"])
        item["value_matched"] = bool(val)
        item["status"] = "ARCHIVED_CAPTURE_VALUE_MATCH" if val else "ARCHIVED_CAPTURE_CONTENT_NOT_MATCHED"
    except (ValueError, TypeError) as e:
        item["status"] = "ARCHIVED_CAPTURE_PARSE_FAILED"
        item["error"] = str(e)[:150]
    return item


def run(source, target):
    inputs = json.loads(source.read_text(encoding="utf-8"))
    out = {"schema": "signal-k37-archive-captured-body-v1",
           "source_index_run_id": 43783910029, "generated_at_utc": now(),
           "cases": [], "metric_level_historical_public_by_candidates": 0,
           "original_usda_file_byte_level_verified": 0, "pit_certified": 0,
           "ready_for_certified_backtest": False}
    for case in inputs["cases"]:
        capture_results = [inspect(case, typ, c) for typ, c in case_entries(case)]
        matches = [x for x in capture_results if x["value_matched"]]
        out["cases"].append({
            "kind": case["kind"], "year": case["year"],
            "official_release_date": case["nominal_release_date"],
            "expected_numeric_value": case["expected_value"],
            "candidates": capture_results, "matched_capture_count": len(matches),
            "earliest_independent_capture_value_observed_at_utc":
                min((x["capture_at_utc"] for x in matches), default=None),
            "source_version_authenticated_original": False,
            "pit_certified": False,
            "status": "VALUE_PUBLIC_BY_ARCHIVE_CAPTURE_CANDIDATE" if matches
                      else "NO_CONFIRMED_CAPTURE_BODY_OR_VALUE",
        })
    out["metric_level_historical_public_by_candidates"] = sum(
        1 for item in out["cases"] if item["matched_capture_count"] > 0)
    target.mkdir(parents=True, exist_ok=True)
    (target / "archived_capture_value_evidence.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(out["cases"]),
                      "metric_public_by_candidates": out["metric_level_historical_public_by_candidates"],
                      "status_by_case": {str(x["year"])+"-"+x["kind"]: [
                         z["status"] for z in x["candidates"]] for x in out["cases"]},
                      "pit_certified": 0}, ensure_ascii=False, sort_keys=True))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run(args.index, args.output)


if __name__ == "__main__":
    main()

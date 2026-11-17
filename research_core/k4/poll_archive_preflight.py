"""Bounded, read-only Wayback pre-release source-vintage feasibility pilot.

Exactly three article URLs; independently captured HTML must contain the
claimed figure and the historical capture timestamp must PRECEDE the scheduled
USDA publication. Index discovery alone does NOT certify source-content PIT.
Time-outs/403/5xx are UNAVAILABLE, never proof that no archive exists.
Do not use this as a trading or historical dataset eligibility gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html import unescape
import argparse
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

EVENT = datetime(2026, 11, 10, 17, tzinfo=timezone.utc)
MIN_CAPTURE = datetime(2026, 11, 5, 0, tzinfo=timezone.utc)
LIMIT = 500_000
TIMEOUT = 9
SOURCES = (
    {"survey_id": "STONEX_NOV_05_AVERAGE",
     "url": "https://www.stonex.com/en-us/insights/nov-wasde-estimates/",
     "value": "1840", "context": (r"1[.]840\s+billion", r"\bcorn\b")},
    {"survey_id": "DTN_DOW_JONES_NOV_06",
     "url": "https://www.dtnpf.com/agriculture/web/ag/news/article/2026/11/06/grain-prices-melt-can-usda-provide",
     "value": "1826", "context": (r"1[.]826\s+bb", r"\bcorn\b")},
    {"survey_id": "CME_EVENT_CALENDAR_ESTIMATES",
     "url": "https://www.cmegroup.com/education/events/econoday/675955",
     "value": "1846", "context": (r"(?:1[,.]846|1[.]846)", r"\bcorn\b")},
)
ARCHIVE_HOSTS = {"web.archive.org", "archive.org"}


def canonical_time(timestamp):
    if not re.fullmatch(r"\d{14}", timestamp or ""):
        raise ValueError("INVALID_WAYBACK_UTC_TIMESTAMP")
    return datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _get(url, *, getter=urlopen):
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in ARCHIVE_HOSTS or p.username or p.password or p.fragment:
        return {"status": "INVALID_ARCHIVE_URL"}
    try:
        r = getter(Request(url, headers={"User-Agent": "SIGNAL-K4-Archival-Poll-Probe/1.0",
                                         "Accept-Encoding": "identity"}), timeout=TIMEOUT)
        with r:
            dest = urlparse(r.geturl())
            if dest.scheme != "https" or dest.hostname not in ARCHIVE_HOSTS:
                return {"status": "UNAPPROVED_ARCHIVE_REDIRECT"}
            data = r.read(LIMIT + 1)
            if len(data) > LIMIT:
                return {"status": "RESPONSE_OVERSIZED"}
            return {"status": "OK", "bytes": data, "sha256": sha256(data).hexdigest(),
                    "http_status": getattr(r, "status", None),
                    "resolved_url": r.geturl(),
                    "memento_datetime": r.headers.get("Memento-Datetime", "")}
    except HTTPError as exc:
        return {"status": "ARCHIVE_HTTP_ERROR", "http_status": exc.code}
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": "ARCHIVE_UNAVAILABLE", "reason": type(exc).__name__}


def index_candidates(payload):
    if payload.get("status") != "OK":
        return [], "INDEX_UNAVAILABLE"
    try:
        records = json.loads(payload["bytes"].decode("utf-8-sig"))
        if not isinstance(records, list) or not records:
            return [], "INDEX_RESPONSE_UNPARSABLE"
        head = records[0]
        hits = []
        for row in records[1:]:
            d = dict(zip(head, row))
            if d.get("statuscode") != "200":
                continue
            t = canonical_time(d["timestamp"])
            if MIN_CAPTURE <= t < EVENT:
                hits.append({"timestamp": d["timestamp"], "at_utc": iso(t),
                             "original_url": d["original"], "index_digest": d.get("digest", "")})
        return hits[:4], "PRE_RELEASE_INDEX_HITS" if hits else "INDEX_NO_MATCH_IN_REQUESTED_WINDOW"
    except (ValueError, KeyError, TypeError):
        return [], "INDEX_RESPONSE_UNPARSABLE"


def content_matches(body, source):
    raw = body.decode("utf-8", "replace")
    raw = re.sub(r"(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>", " ", raw)
    text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", raw))).lower()
    a, b = source["context"]
    for match in re.finditer(a, text, flags=re.I):
        close = text[max(0, match.start() - 300):match.end() + 240]
        if re.search(b, close, flags=re.I):
            return True
    return False


def inspect_capture(hit, source, *, getter=urlopen):
    u = f"https://web.archive.org/web/{hit['timestamp']}id_/{source['url']}"
    resp = _get(u, getter=getter)
    result = {"archive_request": u, "capture_time_utc": hit["at_utc"],
              "archive_index_digest": hit["index_digest"], "status": resp["status"],
              "captured_body_sha256": resp.get("sha256"), "value_present": False,
              "pre_release_value_capture_verified": False}
    if resp["status"] != "OK":
        return result
    path = urlparse(resp["resolved_url"]).path
    m = re.match(r"^/web/(\d{14})(?:id_)?/", path)
    if not m or m.group(1) != hit["timestamp"]:
        result["status"] = "WAYBACK_REPLAY_TIME_MISMATCH"
        return result
    try:
        header = parsedate_to_datetime(resp.get("memento_datetime", "")).astimezone(timezone.utc)
        if abs((header - canonical_time(hit["timestamp"])).total_seconds()) > 1:
            result["status"] = "WAYBACK_MEMENTO_TIME_MISMATCH"
            return result
    except (TypeError, ValueError):
        result["status"] = "WAYBACK_MEMENTO_TIMESTAMP_NOT_CONFIRMED"
        return result
    result["value_present"] = content_matches(resp["bytes"], source)
    result["status"] = "VALUE_FOUND_PRE_RELEASE_IN_WAYBACK" if result["value_present"] else "CAPTURE_EXISTS_VALUE_NOT_CONFIRMED"
    result["pre_release_value_capture_verified"] = bool(result["value_present"])
    return result


def inspect_source(source, *, getter=urlopen):
    params = {
        "url": source["url"], "output": "json",
        "from": "20261105", "to": "20261110165959",
        "filter": "statuscode:200", "fl": "timestamp,original,digest,statuscode",
        "limit": "25",
    }
    cdx_url = "https://web.archive.org/cdx/search/cdx?" + urlencode(params)
    index = _get(cdx_url, getter=getter)
    hits, status = index_candidates(index)
    contents = [inspect_capture(hit, source, getter=getter) for hit in hits]
    return {
        "survey_id": source["survey_id"], "publisher_url": source["url"],
        "expected_figure_million_bushels": source["value"],
        "window_utc": ["2026-11-05T00:00:00Z", "2026-11-10T17:00:00Z (exclusive)"],
        "cdx_query_url": cdx_url, "cdx_status": status,
        "cdx_error": index.get("http_status", index.get("reason")),
        "cdx_response_sha256": index.get("sha256"),
        "index_hit_count_inspected": len(hits),
        "capture_body_checks": contents,
        "verified_independent_pre_release_value_captures": sum(
            int(x["pre_release_value_capture_verified"]) for x in contents),
        "survey_data_asof_status": ("INDEPENDENT_PRE_RELEASE_BODY_CANDIDATE_NEEDS_EDITOR_REVIEW"
            if any(x["pre_release_value_capture_verified"] for x in contents)
            else "INDEPENDENT_PRE_RELEASE_CONTENT_NOT_VERIFIED"),
        "trade_eligible": False,
    }


def scan(*, getter=urlopen):
    sources = [inspect_source(x, getter=getter) for x in SOURCES]
    return {
        "schema": "signal-k4-three-poll-independent-archive-preflight-v1",
        "scope": "THREE_EXACT_URLS_2026-11-05_TO_BEFORE_2026-11-10T17Z",
        "generated_at_utc": iso(datetime.now(timezone.utc)),
        "sources": sources,
        "independently_value_verified_source_count": sum(
            int(x["verified_independent_pre_release_value_captures"] > 0) for x in sources),
        "source_pit_certified": False,
        "formal_event_study_eligible": False,
        "trading_allowed": False,
        "disclaimer": "Wayback indexing is incomplete; one index returning 0 or 403 is not proof no capture exists.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = scan()
    (args.output / "independent_survey_archive_preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"source_results": {x["survey_id"]: {
        "index": x["cdx_status"], "candidates": x["index_hit_count_inspected"],
        "value_verified": x["verified_independent_pre_release_value_captures"]}
        for x in result["sources"]},
        "publisher_date_is_not_independent_capture": True,
        "historical_source_PIT_certified": False}, sort_keys=True))
    return result


if __name__ == "__main__":
    main()

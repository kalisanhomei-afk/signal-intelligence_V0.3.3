"""SIGNAL K3.8 manual forward-only USDA observation (research; no trading).

Captures one exact official plain-text release, with raw bytes, UTC request
receipt, SHA-256 and conservative system-observation feature cutoff. This does
NOT certify the official publication instant or any retrospective PIT record.

NOT a background service; network happens only via explicit CLI invocation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

US_EAST = ZoneInfo("America/New_York")
UTC = timezone.utc
MIN_RELEASE_DATE = date(2026, 11, 16)
MAX_BYTES = 6_000_000
HOSTS = {
    "WASDE": frozenset(("www.usda.gov", "usda.gov", "usda.azureedge.us",
                       "esmis.nal.usda.gov")),
    "NASS": frozenset(("esmis.nal.usda.gov", "www.nass.usda.gov")),
}
DATE_FORMAT = "%B %d, %Y"
WASDE_NAME = re.compile(r"\bWASDE\s*[-–]\s*(\d{3,4})\b", re.I)
MONTH_DATE = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+20\d{2}", re.I,
)
NASS_RELEASE = re.compile(
    r"\bReleased\s+((?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},?\s+20\d{2})", re.I,
)


class CaptureError(ValueError):
    """Fail closed: never write an apparently valid observation on failure."""


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso(t: datetime) -> str:
    if t.tzinfo is None or t.utcoffset() is None:
        raise CaptureError("UTC_OFFSET_REQUIRED")
    return t.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if t.tzinfo is None or t.utcoffset() != timedelta(0):
            raise ValueError("timestamp is not explicit UTC")
        return t.astimezone(UTC)
    except ValueError as exc:
        raise CaptureError("INVALID_EXPLICIT_UTC_TIMESTAMP") from exc


def checked_url(url: str, source: str) -> str:
    if source not in HOSTS:
        raise CaptureError("UNSUPPORTED_SOURCE")
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname not in HOSTS[source] or
            u.username or u.password or u.port not in (None, 443) or u.fragment or
            not u.path.lower().endswith(".txt")):
        raise CaptureError("NON_OFFICIAL_OR_NON_TEXT_RESOURCE")
    return url


class OfficialRedirects(HTTPRedirectHandler):
    def __init__(self, source: str):
        super().__init__()
        self.source = source
        self.chain: list[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl, self.source)
        self.chain.append(newurl)
        if len(self.chain) > 3:
            raise CaptureError("TOO_MANY_REDIRECTS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class Fetch:
    raw: bytes
    requested_url: str
    resolved_url: str
    status: int
    content_type: str
    content_length: int | None
    start: datetime
    finish: datetime
    redirects: tuple[str, ...] = ()


def fetch_official(source: str, url: str) -> Fetch:
    checked_url(url, source)
    redirector = OfficialRedirects(source)
    opener = build_opener(redirector)
    started = now_utc()
    try:
        req = Request(url, headers={
            "User-Agent": "SIGNAL-K38-Manual-PIT-observer/0.1",
            "Cache-Control": "no-cache", "Pragma": "no-cache",
            "Accept-Encoding": "identity",
        })
        with opener.open(req, timeout=20) as response:
            final = response.geturl()
            checked_url(final, source)
            status = response.status
            ctype = response.headers.get("Content-Type", "")
            cl = response.headers.get("Content-Length")
            try:
                n = int(cl) if cl is not None else None
            except ValueError as exc:
                raise CaptureError("INVALID_CONTENT_LENGTH") from exc
            raw = response.read(MAX_BYTES + 1)
            finished = now_utc()
        return Fetch(raw, url, final, status, ctype, n, started, finished,
                     tuple(redirector.chain))
    except HTTPError as exc:
        raise CaptureError(f"OFFICIAL_HTTP_{exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise CaptureError("OFFICIAL_SOURCE_UNAVAILABLE") from exc


def _norm_date(s: str) -> date:
    try:
        return datetime.strptime(re.sub(r"\s+", " ", s.replace(",", ", ")).strip(),
                                 "%B %d, %Y").date()
    except ValueError as exc:
        raise CaptureError("REPORT_DATE_UNPARSABLE") from exc


def report_identity(source: str, raw: bytes, expected: date) -> dict:
    text = raw.decode("utf-8-sig", errors="replace")
    leading = text[:9000]
    if source == "NASS":
        if not re.search(r"\bCrop\s+Progress\b", leading, re.I):
            raise CaptureError("NASS_WRONG_REPORT_TYPE")
        m = NASS_RELEASE.search(leading)
        if not m:
            raise CaptureError("NASS_RELEASE_HEADER_MISSING")
        observed_date = _norm_date(m.group(1))
        report_id = f"NASS-CROP-PROGRESS-{observed_date.isoformat()}"
        crop_note = "CORN_MENTIONED" if re.search(r"\bcorn\b", text, re.I) else "CORN_NOT_REPORTED"
    elif source == "WASDE":
        if not re.search(r"World\s+Agricultural\s+Supply\s+and\s+Demand\s+Estimates", leading, re.I):
            raise CaptureError("WASDE_WRONG_REPORT_TYPE")
        m = WASDE_NAME.search(leading)
        if not m:
            raise CaptureError("WASDE_REPORT_NUMBER_MISSING")
        candidates = set()
        for rawdate in MONTH_DATE.findall(leading[:3500]):
            try:
                candidates.add(_norm_date(rawdate))
            except CaptureError:
                continue
        if expected not in candidates:
            raise CaptureError("WASDE_HEADER_DATE_MISMATCH")
        observed_date = expected
        report_id = "WASDE-" + m.group(1)
        crop_note = "CORN_MENTIONED" if re.search(r"\bcorn\b", text, re.I) else "CORN_NOT_REPORTED"
    else:
        raise CaptureError("UNSUPPORTED_SOURCE")
    if observed_date != expected:
        raise CaptureError("WRONG_RELEASE_DATE_STALE_OR_OTHER_EDITION")
    return {
        "report_id": report_id,
        "report_date_confirmed_from_body": observed_date.isoformat(),
        "crop_status": crop_note,
        "report_format": "ORIGINAL_OFFICIAL_TEXT",
    }


def validate_fetch(source: str, url: str, result: Fetch, expected: date,
                   not_before: datetime, safety_seconds: int) -> dict:
    checked_url(url, source)
    checked_url(result.resolved_url, source)
    if result.requested_url != url:
        raise CaptureError("REQUESTED_URL_MISMATCH")
    if any(checked_url(x, source) is None for x in result.redirects):
        raise CaptureError("INVALID_REDIRECT")
    if result.status != 200:
        raise CaptureError(f"OFFICIAL_HTTP_{result.status}")
    if not (0 < len(result.raw) <= MAX_BYTES):
        raise CaptureError("EMPTY_OR_OVERSIZED_RESPONSE")
    if result.content_length is not None and len(result.raw) != result.content_length:
        raise CaptureError("TRUNCATED_OR_EXTRA_RESPONSE_BYTES")
    if "text/html" in result.content_type.lower():
        raise CaptureError("HTML_ERROR_PAGE_NOT_REPORT")
    if result.raw[:4] == b"%PDF" or result.raw[:2] == b"PK":
        raise CaptureError("EXPECTED_ORIGINAL_PLAIN_TEXT")
    if not (result.start.tzinfo and result.finish.tzinfo):
        raise CaptureError("MISSING_UTC_OBSERVER_CLOCK")
    if result.start > result.finish or result.start < not_before:
        raise CaptureError("CLOCK_OR_EARLY_CAPTURE_ERROR")
    us_day = result.finish.astimezone(US_EAST).date()
    if not 0 <= (us_day - expected).days <= 2:
        raise CaptureError("OUTSIDE_ACTUAL_RELEASE_PILOT_WINDOW")
    identity = report_identity(source, result.raw, expected)
    if identity["crop_status"] != "CORN_MENTIONED":
        raise CaptureError("CORN_SCOPE_NOT_FOUND_IN_REPORT")
    if not (0 <= safety_seconds <= 3600):
        raise CaptureError("INVALID_SAFETY_LATENCY")
    return identity


def validate_spec(source: str, url: str, release_date: str, not_before_utc: str,
                  safety_seconds: int, clock: datetime):
    checked_url(url, source)
    try:
        d = date.fromisoformat(release_date)
    except ValueError as exc:
        raise CaptureError("INVALID_RELEASE_DATE") from exc
    if d < MIN_RELEASE_DATE:
        raise CaptureError("HISTORICAL_BACKDATING_FORBIDDEN")
    t = parse_utc(not_before_utc)
    # Guard against a run that predates the intended release. Caller must choose
    # conservative official-schedule barrier, not a timestamp printed on a PDF.
    if clock < t:
        raise CaptureError("PRE_RELEASE_CAPTURE_NOT_ALLOWED")
    # A human-input future date must not be disguised as a valid report from today.
    if d > clock.astimezone(US_EAST).date():
        raise CaptureError("EXPECTED_RELEASE_IN_FUTURE")
    if not isinstance(safety_seconds, int) or not 0 <= safety_seconds <= 3600:
        raise CaptureError("INVALID_SAFETY_LATENCY")
    return d, t


def prior_comparison(source: str, release_id: str, digest: str, prior: dict | None):
    if prior is None:
        return {"status": "NO_AUTHENTICATED_PRIOR_LEDGER",
                "global_first_ever_observation_proven": False,
                "revision_authenticated": False}
    entries = prior.get("receipts")
    if not isinstance(entries, list):
        raise CaptureError("INVALID_PRIOR_LEDGER")
    same = [e for e in entries if e.get("source") == source and
            e.get("report_id") == release_id]
    for entry in same:
        if not re.fullmatch(r"[0-9a-f]{64}", entry.get("source_sha256", "")):
            raise CaptureError("INVALID_PRIOR_DIGEST")
    if any(x["source_sha256"] == digest for x in same):
        return {"status": "SAME_BYTES_REPORTED_IN_SUPPLIED_PRIOR_LEDGER",
                "global_first_ever_observation_proven": False,
                "revision_authenticated": False}
    if same:
        return {"status": "DIFFERENT_BYTES_POSSIBLE_REVISION_PRIOR_LEDGER_NOT_INDEPENDENTLY_PROVEN",
                "global_first_ever_observation_proven": False,
                "revision_authenticated": False}
    return {"status": "NO_SAME_RELEASE_IN_SUPPLIED_PRIOR_LEDGER",
            "global_first_ever_observation_proven": False,
            "revision_authenticated": False}


def verify_saved(root: Path) -> dict:
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    receipt_bytes = (root / man["receipt_path"]).read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != man["receipt_sha256"]:
        raise CaptureError("RECEIPT_SHA256_REPLAY_MISMATCH")
    receipt = json.loads(receipt_bytes)
    raw = (root / receipt["raw_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["source_sha256"]:
        raise CaptureError("RAW_SHA256_REPLAY_MISMATCH")
    if len(raw) != receipt["source_size_bytes"]:
        raise CaptureError("RAW_LENGTH_REPLAY_MISMATCH")
    report_identity(receipt["source"], raw, date.fromisoformat(receipt["release_date"]))
    if receipt["timestamp_quality"] != "UNKNOWN" or receipt["published_at_utc"]:
        raise CaptureError("RETROACTIVE_PIT_PROMOTION_FORBIDDEN")
    if parse_utc(receipt["safe_feature_not_before_utc"]) < parse_utc(receipt["response_finished_at_utc"]):
        raise CaptureError("LOOKAHEAD_TIME_TRAVEL")
    return {"verified": True, "source_sha256": receipt["source_sha256"],
            "report_id": receipt["report_id"], "pit_certified": False}


def capture(source: str, url: str, release_date: str, not_before_utc: str,
            output: Path, *, safety_seconds: int = 120, prior: dict | None = None,
            transport=fetch_official, preflight_now: datetime | None = None) -> dict:
    preflight_now = preflight_now or now_utc()
    expected, barrier = validate_spec(source, url, release_date, not_before_utc,
                                      safety_seconds, preflight_now)
    result = transport(source, url)
    ident = validate_fetch(source, url, result, expected, barrier, safety_seconds)
    raw_sha = hashlib.sha256(result.raw).hexdigest()
    release_id = ident["report_id"]
    compare = prior_comparison(source, release_id, raw_sha, prior)
    if compare["status"] == "SAME_BYTES_REPORTED_IN_SUPPLIED_PRIOR_LEDGER":
        raise CaptureError("EXACT_ALREADY_OBSERVED_SOURCE_BYTES_IN_SUPPLIED_LEDGER")
    # Finish time is a verified observation by this system, NOT original USDA
    # publication time. This conservative lower bound includes safety latency.
    available = result.finish + timedelta(seconds=safety_seconds)
    raw_key = f"objects/{source}/{expected.isoformat()}/{raw_sha}.bin"
    receipt = {
        "schema": "signal-k38-manual-official-response-receipt-v1",
        "source": source, "release_date": release_date, **ident,
        "source_url": url, "resolved_url": result.resolved_url,
        "redirect_chain": list(result.redirects), "http_status": result.status,
        "response_content_type": result.content_type,
        "source_size_bytes": len(result.raw), "source_sha256": raw_sha,
        "raw_path": raw_key,
        "request_started_at_utc": iso(result.start),
        "response_finished_at_utc": iso(result.finish),
        "first_observed_at_utc": iso(result.finish),
        "first_observed_definition": "EARLIEST_OBSERVATION_OF_THIS_EXACT_FETCH_BY_THIS_RUN_ONLY",
        "scheduled_not_before_utc": iso(barrier),
        "published_at_utc": "", "available_at_utc": "",
        "timestamp_quality": "UNKNOWN",
        "observation_time_class": "DIRECT_SYSTEM_SOURCE_OBSERVATION",
        "safe_feature_not_before_utc": iso(available),
        "safety_latency_seconds": safety_seconds,
        "prior_source_comparison": compare,
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "observer_commit_sha": os.environ.get("GITHUB_SHA", ""),
        "status": "ONE_SOURCE_OBSERVED_NO_BACKTEST_CERTIFICATION",
        "pit_certified_historical": False,
        "original_first_published_at_utc": None,
        "source_originality_certified": False,
        "cross_run_global_dedup_verified": False,
    }
    # Never write until both transport and source/clock/identity validation pass.
    # x mode and non-existing output root avoid accidental overwrite.
    output.mkdir(parents=True, exist_ok=False)
    saved = output / raw_key
    saved.parent.mkdir(parents=True, exist_ok=False)
    with saved.open("xb") as stream:
        stream.write(result.raw)
    raw_reloaded = saved.read_bytes()
    if hashlib.sha256(raw_reloaded).hexdigest() != raw_sha:
        raise CaptureError("DISK_RAW_WRITE_MISMATCH")
    rec_bytes = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with (output / "receipt.json").open("xb") as stream:
        stream.write(rec_bytes)
    manifest = {
        "schema": "signal-k38-capture-manifest-v1", "raw_path": raw_key,
        "receipt_path": "receipt.json", "receipt_sha256": hashlib.sha256(rec_bytes).hexdigest(),
        "report_id": release_id, "source_sha256": raw_sha,
        "historical_publication_timestamp_certified": False,
    }
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2)
        stream.write("\n")
    verify_saved(output)
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("WASDE", "NASS"))
    parser.add_argument("--url")
    parser.add_argument("--release-date")
    parser.add_argument("--not-before-utc")
    parser.add_argument("--latency-seconds", type=int, default=120)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prior-ledger", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            print(json.dumps(verify_saved(args.output), sort_keys=True))
            return 0
        if not all([args.source, args.url, args.release_date, args.not_before_utc]):
            parser.error("Capture requires source, URL, release-date and not-before-utc")
        prior = json.loads(args.prior_ledger.read_text(encoding="utf-8")) if args.prior_ledger else None
        receipt = capture(args.source, args.url, args.release_date, args.not_before_utc,
                          args.output, safety_seconds=args.latency_seconds, prior=prior)
        print(json.dumps({
            "status": receipt["status"], "source_sha256": receipt["source_sha256"],
            "report_id": receipt["report_id"],
            "response_finished_at_utc": receipt["response_finished_at_utc"],
            "safe_feature_not_before_utc": receipt["safe_feature_not_before_utc"],
            "pit_certified_historical": False, "global_dedup_verified": False,
        }, sort_keys=True))
        return 0
    except (CaptureError, FileExistsError, OSError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error_type": type(exc).__name__,
                          "reason": str(exc), "pit_certified_historical": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

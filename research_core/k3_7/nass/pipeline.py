"""USDA NASS pilot source acquisition and deterministic offline replay (stdlib).

Network access is explicit: only the ``fetch`` command downloads anything.
Archive editions are retrieved retrospectively; historical availability and
original-edition authenticity are never inferred from a URL, hash, or schedule.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, time, timedelta, timezone
import hashlib
from html.parser import HTMLParser
from http.client import HTTPException
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
YEARS = (2016, 2020, 2022)
ARCHIVE = "https://esmis.nal.usda.gov/publication/crop-progress"
POLICY = "https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Crop_Progress_and_Condition/"
HOSTS = {"esmis.nal.usda.gov", "www.nass.usda.gov"}
UTC = timezone.utc
SUM_TOLERANCE_PP = 1
RATINGS = ("very_poor_pct", "poor_pct", "fair_pct", "good_pct", "excellent_pct")
ALL_STATES = tuple(sorted((
    "Alabama,Alaska,Arizona,Arkansas,California,Colorado,Connecticut,Delaware,Florida,"
    "Georgia,Hawaii,Idaho,Illinois,Indiana,Iowa,Kansas,Kentucky,Louisiana,Maine,"
    "Maryland,Massachusetts,Michigan,Minnesota,Mississippi,Missouri,Montana,Nebraska,"
    "Nevada,New Hampshire,New Jersey,New Mexico,New York,North Carolina,North Dakota,"
    "Ohio,Oklahoma,Oregon,Pennsylvania,Rhode Island,South Carolina,South Dakota,"
    "Tennessee,Texas,Utah,Vermont,Virginia,Washington,West Virginia,Wisconsin,Wyoming"
).split(",")))
# Audit reference, not an assertion that all 50 states must be reported weekly.
REFERENCE_STATES = tuple(sorted((
    "Colorado,Illinois,Indiana,Iowa,Kansas,Kentucky,Michigan,Minnesota,Missouri,"
    "Nebraska,North Carolina,North Dakota,Ohio,Pennsylvania,South Dakota,"
    "Tennessee,Texas,Wisconsin"
).split(",")))
COLUMNS = [
    "report_date", "week_ending", "calendar_year", "iso_week", "marketing_year",
    "state", "crop", *RATINGS, "good_excellent_pct", "percentage_sum",
    "percentage_quality", "source_url", "source_sha256", "source_version_id",
    "source_version_status", "revision_marker", "retrieved_at_utc",
    "published_at_utc", "available_at_utc", "timestamp_quality", "evidence_url",
    "scheduled_release_at_utc", "schedule_evidence_url", "schedule_evidence_sha256",
    "quality_status",
]
MONTHS = {x.lower(): i for i, x in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
DATE_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},?\s+20\d{2}"
)
DATE_RE = re.compile(DATE_PATTERN, re.I)


class SourceError(ValueError):
    """An auditable source or format failure, never a missing-value substitute."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def checked_url(url: str) -> str:
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname not in HOSTS or p.username or p.password
            or p.port not in (None, 443) or p.fragment):
        raise SourceError(f"UNAPPROVED_URL: {url}")
    return url


def parse_instant(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise SourceError("Timestamp lacks timezone")
    return dt.astimezone(UTC)


def parse_date(value: str) -> date:
    match = DATE_RE.search(value)
    if not match:
        raise SourceError(f"Missing English report date: {value!r}")
    month, day, year = match.group().replace(",", "").split()
    return date(int(year), MONTHS[month[:3].lower()], int(day))


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.active = None
        self.labels = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.active = dict(attrs)
            self.labels = []

    def handle_data(self, data):
        if self.active is not None:
            self.labels.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            self.links.append((self.active, " ".join(self.labels)))
            self.active = None


def archive_links(raw: bytes, page_url: str) -> tuple[list[dict], str | None, list[dict]]:
    """Follow only observed official TXT and next-page links; retain all editions."""
    parser = Anchors()
    parser.feed(raw.decode("utf-8-sig"))
    releases, next_links, issues = [], set(), []
    seen = set()
    for attrs, label in parser.links:
        url = urljoin(page_url, attrs.get("href", ""))
        try:
            checked_url(url)
        except (SourceError, ValueError):
            continue
        if re.search(r"/(?:prog\d{4}|CropProg-\d{2}-\d{2}-20\d{2})\.txt$", urlsplit(url).path, re.I):
            try:
                day = parse_date(label + " " + attrs.get("title", ""))
            except (SourceError, ValueError):
                issues.append({"code": "UNDATED_TXT_LINK", "url": url, "label": label})
                continue
            key = (day.isoformat(), url)
            if key not in seen:
                seen.add(key)
                releases.append({"report_date": key[0], "url": url})
        is_next = ("next" in attrs.get("rel", "").lower().split()
                   or re.fullmatch(r"\s*(?:next(?:\s+page)?\s*[›»>]?|[›»])\s*", label, re.I)
                   or "next page" in attrs.get("title", "").lower())
        if (is_next and urlsplit(url).hostname == "esmis.nal.usda.gov"
                and urlsplit(url).path.rstrip("/") == urlsplit(ARCHIVE).path):
            next_links.add(url)
    if len(next_links) > 1:
        raise SourceError("AMBIGUOUS_ARCHIVE_PAGINATION")
    return releases, next(iter(next_links), None), issues


def percentages(tokens: list[str]) -> tuple[list[int] | None, str]:
    if len(tokens) != 5 or any(not re.fullmatch(r"\d{1,3}", t) for t in tokens):
        return None, "MISSING_OR_NONNUMERIC_RATING"
    values = [int(t) for t in tokens]
    if any(v > 100 for v in values):
        return None, "PERCENTAGE_OUT_OF_RANGE"
    if abs(sum(values) - 100) > SUM_TOLERANCE_PP:
        return None, "PERCENTAGE_SUM_OUT_OF_TOLERANCE"
    return values, "OK" if sum(values) == 100 else "ROUNDING_TOLERANCE"


def parse_report(raw: bytes, expected_date: str | None = None) -> dict:
    """Parse only the contemporary state corn-condition block, fail on ambiguity."""
    text = raw.decode("utf-8-sig")
    if not re.search(r"(?im)^\s*Crop Progress\s*$", text) or "National Agricultural Statistics Service" not in text:
        raise SourceError("NOT_NASS_CROP_PROGRESS_TEXT")
    release = re.search(r"\bReleased\s+(" + DATE_PATTERN + r")", text, re.I)
    if not release:
        raise SourceError("MISSING_RELEASE_HEADER")
    report_day = parse_date(release.group(1))
    if report_day.year not in YEARS:
        raise SourceError("OUTSIDE_PILOT_YEARS")
    if expected_date and report_day.isoformat() != expected_date:
        raise SourceError(f"RELEASE_DATE_MISMATCH: {report_day} vs {expected_date}")
    result = {"report_date": report_day.isoformat(), "week_ending": "", "rows": [],
              "issues": [], "listed_states": [], "declared_state_count": None,
              "revision_marker": bool(re.search(r"\b(?:Revised|Revision|Corrected|Correction)\b", text, re.I)),
              "status": "PARSED"}
    heads = list(re.finditer(
        r"(?im)^\s*Corn Condition\s*-\s*Selected States\s*:\s*Week Ending\s*([^\r\n]+)", text))
    if not heads:
        if re.search(r"Corn\s+Condition", text, re.I):
            raise SourceError("UNSUPPORTED_CORN_CONDITION_HEADING")
        result["status"] = "NOT_REPORTED_IN_RETRIEVED_REPORT"
        return result
    if len(heads) != 1:
        raise SourceError("MULTIPLE_CONTEMPORARY_CORN_CONDITION_BLOCKS")
    head = heads[0]
    week = parse_date(head.group(1))
    if week.weekday() != 6 or not 1 <= (report_day - week).days <= 3:
        raise SourceError("IMPLAUSIBLE_WEEK_ENDING_OR_RELEASE_LAG")
    result["week_ending"] = week.isoformat()
    block = text[head.end():]
    end = re.search(r"(?m)^\s*[A-Za-z][A-Za-z /]+\s*-\s*Selected States\b", block)
    if end:
        block = block[:end.start()]
    lines = block.splitlines()
    row_pattern = re.compile(r"^\s*([A-Za-z][A-Za-z .]*?)\s*:\s*(.*?)\s*$")
    state_lines = []
    for i, line in enumerate(lines):
        match = row_pattern.match(line)
        if match:
            label = re.sub(r"\s+", " ", match.group(1).replace(".", " ")).strip()
            if label in ALL_STATES:
                state_lines.append(i)
    if not state_lines:
        raise SourceError("NO_RECOGNIZED_STATE_ROWS")
    header = " ".join(lines[:state_lines[0]])
    header = re.sub(r"\bState\b", " ", header, flags=re.I)
    header = re.sub(r"[^A-Za-z]+", " ", header)
    if not re.search(r"\bVery\s+poor\s+Poor\s+Fair\s+Good\s+Excellent\b", header, re.I):
        raise SourceError("UNSUPPORTED_RATING_COLUMN_ORDER")
    header_end = max(i for i, line in enumerate(lines[:state_lines[0]])
                     if re.search(r"\bExcellent\b", line, re.I))
    states = defaultdict(list)
    aggregates = []
    for i, line in enumerate(lines):
        aggregate = re.match(r"^\s*(\d+)\s+States\s*\.*\s*:\s*(.*?)\s*$", line)
        if aggregate:
            values, status = percentages(aggregate.group(2).split())
            aggregates.append((int(aggregate.group(1)), values))
            if values is None:
                result["issues"].append({"code": "AGGREGATE_" + status, "source_row": line})
            continue
        match = row_pattern.match(line)
        if not match or i <= header_end:
            continue
        label = re.sub(r"\s+", " ", match.group(1).replace(".", " ")).strip()
        if re.match(r"(?:Previous\s+(?:week|year)|Last\s+(?:week|year))\b", label, re.I):
            continue
        if label not in ALL_STATES:
            result["issues"].append({"code": "UNRECOGNIZED_TABLE_ROW", "source_row": line})
            continue
        states[label].append((match.group(2).split(), line))
    result["listed_states"] = sorted(states)
    if len(aggregates) != 1:
        result["issues"].append({"code": "MISSING_OR_DUPLICATE_AGGREGATE_ROW"})
    else:
        result["declared_state_count"] = aggregates[0][0]
        if aggregates[0][0] != len(states):
            result["issues"].append({"code": "DECLARED_STATE_COUNT_MISMATCH",
                                     "declared": aggregates[0][0], "listed": len(states)})
    for state, items in sorted(states.items()):
        if len(items) != 1:
            result["issues"].append({"code": "DUPLICATE_STATE_ROW", "state": state,
                                     "source_rows": [line for _, line in items]})
            continue
        tokens, line = items[0]
        values, status = percentages(tokens)
        if values is None:
            result["issues"].append({"code": status, "state": state, "source_row": line})
            continue
        result["rows"].append({"state": state, **dict(zip(RATINGS, values)),
                               "good_excellent_pct": values[3] + values[4],
                               "percentage_sum": sum(values), "percentage_quality": status})
    result["missing_reference_states"] = sorted(set(REFERENCE_STATES) - set(states))
    accepted = {row["state"] for row in result["rows"]}
    result["state_rating_gaps"] = [
        {"state": state, "status": "RATING_REJECTED" if state in states else "NOT_LISTED_IN_RETRIEVED_TABLE"}
        for state in sorted(set(REFERENCE_STATES) - accepted)
    ]
    if result["issues"]:
        result["status"] = "PARTIAL_PARSE"
    return result


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Check BEFORE following the redirect; credentials/proxies stay inherited.
        checked_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str, max_bytes: int = 4_000_000, timeout: int = 20) -> dict:
    checked_url(url)
    req = Request(url, headers={"User-Agent": "SIGNAL-K37-NASS-source-research/1.0",
                                "Accept": "text/plain,text/html;q=0.9"})
    with build_opener(OfficialRedirects()).open(req, timeout=timeout) as response:
        final_url = checked_url(response.geturl())
        raw = response.read(max_bytes + 1)
        retrieved = utc_now()  # Recorded only after successful body read.
        if len(raw) > max_bytes:
            raise SourceError("RESPONSE_SIZE_LIMIT")
        if not raw:
            raise SourceError("EMPTY_RESPONSE")
        return {"raw": raw, "source_url": final_url, "retrieved_at_utc": retrieved,
                "http_status": response.status, "content_type": response.headers.get("Content-Type", ""),
                "last_modified": response.headers.get("Last-Modified", "")}


def append_json(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_ledger(bundle: Path) -> list[dict]:
    return read_jsonl(bundle / "source_manifest.jsonl")


def acquire(bundle: Path, url: str, role: str, fetcher=download, **metadata) -> dict:
    checked_url(url)
    record = {"role": role, "requested_url": url, "attempted_at_utc": utc_now(), **metadata}
    try:
        response = fetcher(url)
        raw = response.pop("raw")
        checked_url(response["source_url"])
        parse_instant(response["retrieved_at_utc"])
        digest = sha256(raw)
        local = bundle / "raw" / (digest + ".bin")
        local.parent.mkdir(parents=True, exist_ok=True)
        if local.exists():
            if local.read_bytes() != raw:
                raise SourceError("CONTENT_ADDRESS_COLLISION_OR_CORRUPTION")
        else:
            with local.open("xb") as stream:
                stream.write(raw)
        record.update(response, status="DOWNLOADED", source_sha256=digest,
                      byte_count=len(raw), raw_path=f"raw/{digest}.bin")
    except (OSError, ValueError, HTTPError, URLError, HTTPException) as exc:
        record.update(status="SOURCE_UNAVAILABLE", error=f"{type(exc).__name__}: {exc}",
                      completed_at_utc=utc_now())
    append_json(bundle / "source_manifest.jsonl", record)
    return record


def checked_raw(bundle: Path, entry: dict) -> bytes:
    digest = entry.get("source_sha256", "")
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise SourceError("INVALID_SOURCE_DIGEST")
    # Never trust a manifest-supplied path for filesystem traversal.
    if entry.get("raw_path") != f"raw/{digest}.bin":
        raise SourceError("INVALID_RAW_PATH")
    raw = (bundle / "raw" / f"{digest}.bin").read_bytes()
    if sha256(raw) != digest or len(raw) != entry["byte_count"]:
        raise SourceError("RAW_DIGEST_OR_SIZE_MISMATCH")
    checked_url(entry["source_url"])
    parse_instant(entry["retrieved_at_utc"])
    return raw


def fetch_sources(bundle: Path, max_pages: int, fetcher=download) -> dict:
    if max_pages < 1:
        raise SourceError("max-pages must be positive")
    acquire(bundle, POLICY, "schedule", fetcher)
    page_url, seen_pages, found = ARCHIVE, set(), {}
    status = "PAGE_LIMIT_REACHED"
    discovery_issue_count = 0
    for _ in range(max_pages):
        if page_url in seen_pages:
            status = "PAGINATION_CYCLE"
            break
        seen_pages.add(page_url)
        receipt = acquire(bundle, page_url, "archive", fetcher)
        if receipt["status"] != "DOWNLOADED":
            status = "SOURCE_UNAVAILABLE"
            break
        try:
            releases, next_url, issues = archive_links(checked_raw(bundle, receipt), receipt["source_url"])
        except (OSError, ValueError) as exc:
            status = "ARCHIVE_PARSE_ERROR"
            append_json(bundle / "discovery_log.jsonl", {"status": status, "url": page_url, "error": str(exc)})
            break
        for item in releases:
            if int(item["report_date"][:4]) in YEARS:
                found[(item["report_date"], item["url"])] = {
                    **item, "discovery_source_url": receipt["source_url"],
                    "discovery_source_sha256": receipt["source_sha256"]}
        discovery_issue_count += len(issues)
        append_json(bundle / "discovery_log.jsonl", {"status": "PAGE_PARSED", "url": page_url,
                    "source_sha256": receipt["source_sha256"], "txt_links": len(releases), "issues": issues})
        if not next_url:
            # No links does not establish completeness (HTML layout may have changed).
            status = "OBSERVED_PAGINATION_END" if releases else "NO_RECOGNIZED_LINKS"
            break
        page_url = next_url
    report_counts = Counter()
    for item in sorted(found.values(), key=lambda x: (x["report_date"], x["url"])):
        append_json(bundle / "discovered_reports.jsonl", item)
        receipt = acquire(bundle, item["url"], "report", fetcher, expected_report_date=item["report_date"],
                          discovery_source_sha256=item["discovery_source_sha256"])
        report_counts[receipt["status"]] += 1
    summary = {"status": status, "pages_attempted": len(seen_pages), "reports_discovered": len(found),
               "report_downloads_succeeded": report_counts["DOWNLOADED"],
               "report_downloads_failed": report_counts["SOURCE_UNAVAILABLE"],
               "discovery_issue_count": discovery_issue_count,
               "completed_at_utc": utc_now(), "scope_years": list(YEARS)}
    append_json(bundle / "discovery_log.jsonl", summary)
    return summary


def schedule_evidence(bundle: Path, ledger: list[dict]) -> dict | None:
    for entry in ledger:
        if entry.get("role") != "schedule" or entry.get("status") != "DOWNLOADED":
            continue
        if entry.get("requested_url") != POLICY:
            continue
        try:
            raw = checked_raw(bundle, entry)
            text = re.sub(r"</(?:p|div|li|tr)>|<br\s*/?>", "\n", raw.decode("utf-8-sig"), flags=re.I)
            text = re.sub(r"<[^>]*>", " ", text)
            # Require the crop, weekday, hour and zone in one bounded statement;
            # unrelated scheduling text elsewhere on a page is not evidence.
            for statement in text.splitlines():
                if (len(statement) <= 600 and re.search(r"Crop Progress", statement, re.I)
                        and re.search(r"\bMonday", statement, re.I)
                        and re.search(r"\b4(?::00)?\s*p\.?\s*m\.?", statement, re.I)
                        and re.search(r"Eastern|\bET\b", statement, re.I)):
                    return entry
        except (OSError, ValueError, KeyError):
            continue
    return None


def time_fields(report_day: str, schedule: dict | None) -> dict:
    fields = dict(published_at_utc="", available_at_utc="", evidence_url="",
                  timestamp_quality="UNKNOWN", scheduled_release_at_utc="",
                  schedule_evidence_url="", schedule_evidence_sha256="")
    if schedule:
        day = date.fromisoformat(report_day)
        # Generic Monday guidance does not establish a holiday Tuesday/Wednesday schedule.
        if day.weekday() == 0:
            dt = datetime.combine(day, time(16), ZoneInfo("America/New_York"))
            fields.update(timestamp_quality="OFFICIAL_SCHEDULE_PROXY",
                          scheduled_release_at_utc=dt.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                          schedule_evidence_url=schedule["source_url"],
                          schedule_evidence_sha256=schedule["source_sha256"])
    return fields


def write_csv(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def season_sundays(year: int) -> list[str]:
    """April-November audit grid, explicitly not an official reporting calendar."""
    day, end = date(year, 4, 1), date(year, 11, 30)
    day += timedelta(days=(6 - day.weekday()) % 7)
    days = []
    while day <= end:
        days.append(day.isoformat())
        day += timedelta(days=7)
    return days


def build(bundle: Path, output: Path) -> dict:
    """Replay immutable receipts. No clock or network calls; bytes determine output."""
    ledger = read_ledger(bundle)
    discovery_audit = read_jsonl(bundle / "discovery_log.jsonl")
    schedule = schedule_evidence(bundle, ledger)
    observations, sources, issues = [], [], []
    seen_versions = set()
    for entry in ledger:
        if entry.get("role") != "report":
            continue
        source = {k: v for k, v in entry.items() if k != "raw_path"}
        if entry.get("status") != "DOWNLOADED":
            source["parse_status"] = "SOURCE_UNAVAILABLE"
            sources.append(source)
            continue
        try:
            raw = checked_raw(bundle, entry)
            if "SYNTHETIC OFFLINE FIXTURE" in raw.decode("utf-8-sig"):
                raise SourceError("FIXTURE_IS_NOT_A_PRODUCTION_OBSERVATION")
            parsed = parse_report(raw, entry.get("expected_report_date"))
            version = (entry["source_url"], entry["source_sha256"], parsed["report_date"])
            if version in seen_versions:
                continue  # Same immutable bytes; keep FIRST actual retrieval receipt.
            seen_versions.add(version)
            source.update({k: v for k, v in parsed.items() if k not in ("rows", "issues")},
                          parse_status=parsed["status"], accepted_state_rows=len(parsed["rows"]),
                          issues=parsed["issues"])
            for issue in parsed["issues"]:
                issues.append({"source_url": entry["source_url"], "source_sha256": entry["source_sha256"],
                               "report_date": parsed["report_date"], **issue})
            for row in parsed["rows"]:
                week = date.fromisoformat(parsed["week_ending"])
                observations.append({
                    "report_date": parsed["report_date"], "week_ending": parsed["week_ending"],
                    "calendar_year": week.year, "iso_week": week.isocalendar().week,
                    "marketing_year": f"{week.year}/{str(week.year + 1)[-2:]}", "crop": "CORN",
                    **row, "source_url": entry["source_url"], "source_sha256": entry["source_sha256"],
                    "source_version_id": sha256((entry["source_url"] + "\n" + entry["source_sha256"]).encode()),
                    "source_version_status": "ARCHIVE_RETRIEVED_EDITION_ORIGINALITY_UNVERIFIED",
                    "revision_marker": str(parsed["revision_marker"]).lower(),
                    "retrieved_at_utc": entry["retrieved_at_utc"], **time_fields(parsed["report_date"], schedule),
                    "quality_status": "REVISED_EDITION_PIT_UNVERIFIED" if parsed["revision_marker"] else "PIT_UNVERIFIED",
                })
        except (OSError, ValueError, KeyError) as exc:
            source.update(parse_status="PARSE_ERROR", error=f"{type(exc).__name__}: {exc}")
            issues.append({"code": "PARSE_ERROR", "requested_url": entry["requested_url"], "error": str(exc)})
        sources.append(source)
    editions = defaultdict(list)
    for row in observations:
        editions[(row["week_ending"], row["state"])].append(row)
    for (week, state), rows in sorted(editions.items()):
        if len(rows) > 1:
            conflict = len({tuple(r[k] for k in RATINGS) for r in rows}) > 1
            issues.append({"code": "VINTAGE_VALUE_CONFLICT" if conflict else "MULTIPLE_SOURCE_EDITIONS",
                           "week_ending": week, "state": state,
                           "source_version_ids": sorted(r["source_version_id"] for r in rows)})
            if conflict:
                for row in rows:
                    row["quality_status"] = "VINTAGE_CONFLICT_PIT_UNVERIFIED"
    observations.sort(key=lambda r: (r["week_ending"], r["state"], r["report_date"],
                                      r["source_url"], r["source_sha256"]))
    coverage = []
    for year in YEARS:
        rows = [r for r in observations if r["calendar_year"] == year]
        weeks = sorted({r["week_ending"] for r in rows})
        states = sorted({r["state"] for r in rows})
        year_sources = [s for s in sources if (s.get("report_date") or s.get("expected_report_date", "")).startswith(str(year))]
        coverage.append({
            "year": year, "observation_rows_including_editions": len(rows),
            "distinct_state_weeks": len({(r["state"], r["week_ending"]) for r in rows}),
            "accepted_condition_weeks": weeks, "accepted_states": states,
            "first_condition_week": weeks[0] if weeks else "", "last_condition_week": weeks[-1] if weeks else "",
            "reference_states_without_accepted_rows": sorted(set(REFERENCE_STATES) - set(states)),
            "other_states_outside_reference_scope": sorted(set(ALL_STATES) - set(REFERENCE_STATES)),
            "audit_grid_weeks_without_accepted_conditions": sorted(set(season_sundays(year)) - set(weeks)),
            "unresolved_sources": [s for s in year_sources if s["parse_status"] not in ("PARSED", "NOT_REPORTED_IN_RETRIEVED_REPORT")],
            "reports_without_condition_table": [s["report_date"] for s in year_sources
                                                 if s["parse_status"] == "NOT_REPORTED_IN_RETRIEVED_REPORT"],
            "coverage_status": "PARTIAL_OFFICIAL_SOURCE_RECOVERY" if rows else "NO_OFFICIAL_OBSERVATIONS_RECOVERED",
        })
    network = Counter(e.get("status", "INVALID") for e in ledger)
    report = {
        "schema_version": "signal-k37-nass-v1", "scope_years": list(YEARS),
        "status": "PARTIAL_OFFICIAL_SOURCE_RECOVERY_PIT_UNVERIFIED" if observations else "SOURCE_FEASIBILITY_BLOCKED_OR_NO_DATA",
        "observation_rows": len(observations), "verified_public_timestamp_rows": 0,
        "timestamp_quality_counts": dict(sorted(Counter(r["timestamp_quality"] for r in observations).items())),
        "rounding_tolerance_percentage_points": SUM_TOLERANCE_PP,
        "network_attempt_counts": dict(sorted(network.items())), "network_attempts": ledger,
        "discovery_audit": discovery_audit,
        "source_parse_audit": sources, "issues": issues, "seasonal_coverage": coverage,
        "reference_states": list(REFERENCE_STATES),
        "audit_grid_policy": "April-November Sundays are an audit grid, NOT an official release calendar. Empty weeks are UNKNOWN, not proven missing reports or unreported conditions.",
        "vintage_policy": "Keep every distinct URL+raw-SHA256 edition; first retrieval for identical bytes. No latest-value substitution. Original publication authenticity remains unverified.",
        "timestamp_policy": "Exact published/available fields and evidence_url remain blank. Observed current official Monday guidance can support only a separate OFFICIAL_SCHEDULE_PROXY; holidays remain UNKNOWN. HTTP Last-Modified is not release evidence.",
        "limitations": [
            "Parser fixtures are synthetic format tests, not historical observations; real historical parser validation requires downloaded official reports.",
            "No source recovery does not prove a release was never published. Discovery errors and page limits prevent claims of complete coverage.",
            "Missing/non-numeric/invalid ratings are rejected to the audit; no interpolation, national-to-state allocation, or zero substitution.",
            "Archives retrieved today may contain later corrections. Neither URL dates nor raw hashes certify the original historical version or public availability.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "nass_state_weekly.csv", observations)
    (output / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# USDA NASS K3.7 資料品質報告", "", f"狀態：`{report['status']}`", "",
             f"正式觀測列：{len(observations)}；已驗證歷史公開時間：0。", "",
             f"五類整數百分比須各在 0–100，加總允許 100 ± {SUM_TOLERANCE_PP} 個百分點；99/101 會另標示。", "",
             "| 年度 | 觀測列（含版本） | 有資料週數 | 有資料州數 |", "| --- | ---: | ---: | ---: |"]
    lines += [f"| {c['year']} | {c['observation_rows_including_editions']} | {len(c['accepted_condition_weeks'])} | {len(c['accepted_states'])} |" for c in coverage]
    lines += ["", "所有來源、實際下載時間、失敗原因、逐來源解析異常及逐年缺州／缺週清單見 `quality_report.json`。",
              "", "4–11 月週日僅為稽核格線，空白不代表官方漏發；報告缺表、解析失敗與尚未取得分開記錄。",
              "", "18 州為稽核參考範圍，其餘 32 州不應被視為官方每週必報而缺漏。",
              "", "來源版本與歷史可用時間均未獨立認證；本資料不可當作 PIT 認證輸入。",
              "", "離線單元測試與線上下載為獨立驗收；數值樣本測試不代表歷史資料下載成功。", ""]
    (output / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "build"))
    parser.add_argument("--bundle", type=Path, default=HERE / "data")
    parser.add_argument("--output", type=Path, default=HERE / "out")
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args(argv)
    if args.command == "fetch":
        result = fetch_sources(args.bundle, args.max_pages)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        # Transport success alone is insufficient. Offline build is a separate command.
        return 0 if (result["status"] == "OBSERVED_PAGINATION_END" and result["report_downloads_succeeded"]
                     and not result["report_downloads_failed"] and not result["discovery_issue_count"]) else 2
    report = build(args.bundle, args.output)
    print(json.dumps({"status": report["status"], "observation_rows": report["observation_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

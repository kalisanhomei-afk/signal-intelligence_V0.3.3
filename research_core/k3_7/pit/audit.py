"""Offline documentary PIT audit. A schedule or archive capture is never exact proof.

Evidence review is a human trust boundary, not cryptographic authentication of
the publisher. Every approved interpretation retains its raw document and quote.
No producer's timestamp_quality or published_at claim is trusted as evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

YEARS = (2016, 2020, 2022)
KINDS = ("WASDE", "NASS")
VERIFIED = "VERIFIED_PUBLIC_TIMESTAMP"
PROXY = "OFFICIAL_SCHEDULE_PROXY"
UNKNOWN = "UNKNOWN"
QUALITIES = (VERIFIED, PROXY, UNKNOWN)
HERE = Path(__file__).resolve().parent
COLS = (
    "source_type", "source_release_date", "source_url", "source_sha256",
    "vintage_id", "revision_kind", "supersedes_vintage_id",
    "published_at_utc", "available_at_utc", "first_published_at_utc",
    "corrected_at_utc", "retrieved_at_utc", "retrieval_receipt_sha256",
    "official_schedule_utc", "observed_public_by_utc", "timestamp_quality",
    "quality_status", "evidence_url", "evidence_sha256", "evidence_format",
    "documentary_evidence", "reason", "pit_certified",
)


class AuditError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(code + (": " + detail if detail else ""))


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_json(raw: bytes) -> object:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY", key)
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError("INVALID_JSON") from exc


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise AuditError(code, detail)


def text(value: object, field: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), "MISSING_FIELD", field)
    return value


def instant(value: str) -> datetime:
    try:
        # Explicit offset only; date-only and naive timestamps are prohibited.
        require(isinstance(value, str) and "T" in value, "INVALID_TIME", str(value))
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(result.tzinfo is not None and result.utcoffset() is not None,
                "NAIVE_TIME", value)
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError("INVALID_TIME", str(value)) from exc


def iso(value: str | datetime) -> str:
    dt = instant(value) if isinstance(value, str) else value
    require(dt.tzinfo is not None, "NAIVE_TIME")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def local_instant(value: str, zone: str, offset: str = "") -> str:
    """Reject nonexistent wall clocks and require an offset for a DST fold."""
    try:
        wall = datetime.fromisoformat(value)
        require(wall.tzinfo is None and "T" in value, "LOCAL_TIME_REQUIRED")
        tz = ZoneInfo(zone)
    except (ValueError, TypeError, ZoneInfoNotFoundError) as exc:
        raise AuditError("INVALID_LOCAL_TIME", str(value)) from exc
    candidates = {}
    for fold in (0, 1):
        candidate = wall.replace(tzinfo=tz, fold=fold)
        if candidate.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == wall:
            candidates[iso(candidate)] = candidate
    require(bool(candidates), "NONEXISTENT_LOCAL_TIME", value)
    if offset:
        chosen = instant(value + offset)
        require(iso(chosen) in candidates, "OFFSET_ZONE_MISMATCH", value)
        return iso(chosen)
    require(len(candidates) == 1, "AMBIGUOUS_LOCAL_TIME", value)
    return next(iter(candidates))


def url_host(url: str) -> str:
    try:
        parsed = urlsplit(url)
        require(parsed.scheme == "https" and bool(parsed.hostname)
                and not parsed.username and not parsed.password
                and parsed.port in (None, 443) and not parsed.fragment,
                "INVALID_URL", url)
        return parsed.hostname.lower()
    except (ValueError, TypeError) as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError("INVALID_URL", str(url)) from exc


def official(host: str) -> bool:
    return host == "usda.gov" or host.endswith(".usda.gov") or host == "usda.azureedge.us"


def checked_bytes(root: Path, path: str, digest: str) -> bytes:
    text(path, "artifact path")
    require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            "INVALID_SHA256", path)
    target = (root / path).resolve()
    require(not Path(path).is_absolute() and target.is_relative_to(root.resolve()),
            "ARTIFACT_OUTSIDE_BUNDLE", path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise AuditError("MISSING_ARTIFACT", path) from exc
    require(sha(raw) == digest, "HASH_MISMATCH", path)
    return raw


def binding(item: dict, record: dict) -> None:
    for field in ("source_type", "source_release_date", "source_url", "source_sha256", "vintage_id"):
        require(item.get(field, "") == record.get(field, ""), "EVIDENCE_BINDING_MISMATCH", field)


def evidence_review(e: dict, root: Path, record: dict) -> tuple[str, dict]:
    require(isinstance(e, dict), "INVALID_EVIDENCE")
    raw = checked_bytes(root, e.get("path"), e.get("sha256"))
    host = url_host(e.get("url"))
    require(e.get("format") in {"text/plain", "text/html", "application/json"},
            "UNSUPPORTED_EVIDENCE_FORMAT")
    try:
        document = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise AuditError("EVIDENCE_NOT_UTF8") from exc
    review = e.get("review", {})
    require(isinstance(review, dict), "INVALID_REVIEW")
    require(review.get("verdict") == "APPROVED", "UNREVIEWED_EVIDENCE")
    text(review.get("reviewer"), "reviewer")
    text(review.get("reason"), "review reason")
    reviewed = instant(review.get("reviewed_at_utc"))
    captured = instant(e.get("captured_at_utc"))
    require(captured <= reviewed, "REVIEW_BEFORE_CAPTURE")
    quote = text(review.get("quote"), "documentary quote")
    require(quote in document, "QUOTE_NOT_IN_DOCUMENT")
    binding(review, record)
    return host, review


def audit_record(record: dict, root: Path) -> dict:
    require(isinstance(record, dict), "INVALID_RECORD")
    kind = record.get("source_type")
    require(kind in KINDS, "INVALID_SOURCE_TYPE")
    day = record.get("source_release_date")
    try:
        require(isinstance(day, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) is not None,
                "INVALID_RELEASE_DATE")
        release = date.fromisoformat(day)
    except ValueError as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError("INVALID_RELEASE_DATE", str(day)) from exc
    require(release.year in YEARS, "OUTSIDE_PILOT_YEARS")
    require(official(url_host(record.get("source_url"))), "NON_OFFICIAL_SOURCE")
    text(record.get("vintage_id"), "vintage_id")
    revision = record.get("revision_kind")
    require(revision in {"INITIAL", "CORRECTION"}, "INVALID_REVISION_KIND")
    predecessor = record.get("supersedes_vintage_id", "")
    require((revision == "INITIAL" and not predecessor)
            or (revision == "CORRECTION" and isinstance(predecessor, str) and bool(predecessor)),
            "REVISION_LINK_REQUIRED")
    row = {field: "" for field in COLS}
    for field in ("source_type", "source_release_date", "source_url", "source_sha256",
                  "vintage_id", "revision_kind", "supersedes_vintage_id"):
        row[field] = record.get(field, "")
    row.update(timestamp_quality=UNKNOWN, quality_status="PIT_UNVERIFIED", pit_certified="false")
    # A date-only entry may be audited as UNKNOWN even when no source bytes exist.
    if record.get("source_path") or record.get("source_sha256"):
        checked_bytes(root, record.get("source_path"), record.get("source_sha256"))
    if record.get("retrieved_at_utc"):
        raise AuditError("UNSUPPORTED_RETRIEVAL_CLAIM", "use a raw download receipt")
    receipt = record.get("retrieval_receipt")
    if receipt:
        raw = checked_bytes(root, receipt.get("path"), receipt.get("sha256"))
        try:
            rec = parse_json(raw)
        except (ValueError, UnicodeError) as exc:
            raise AuditError("INVALID_RETRIEVAL_RECEIPT") from exc
        require(isinstance(rec, dict) and rec.get("kind") == "SIGNAL_HTTP_DOWNLOAD_V1",
                "INVALID_RETRIEVAL_RECEIPT")
        require(rec.get("source_url") == row["source_url"]
                and rec.get("source_sha256") == row["source_sha256"] and bool(row["source_sha256"]),
                "RETRIEVAL_BINDING_MISMATCH")
        started = instant(rec.get("started_at_utc"))
        finished = instant(rec.get("finished_at_utc"))
        require(started <= finished, "INVALID_RETRIEVAL_ORDER")
        row["retrieved_at_utc"] = iso(finished)
        row["retrieval_receipt_sha256"] = sha(raw)
    proofs, schedules, bounds, documentary = set(), set(), [], []
    evidence = record.get("evidence", [])
    require(isinstance(evidence, list), "INVALID_EVIDENCE_LIST")
    for e in evidence:
        host, review = evidence_review(e, root, record)
        e_kind = e.get("kind")
        quote = review["quote"]
        summary = {k: e[k] for k in ("kind", "url", "path", "sha256", "format", "captured_at_utc")}
        summary["review"] = review
        documentary.append(summary)
        if e_kind == "OFFICIAL_SCHEDULE":
            require(official(host), "NON_OFFICIAL_SCHEDULE")
            require(review.get("assertion") == "SCHEDULE_ONLY", "WRONG_SCHEDULE_ASSERTION")
            local = review.get("scheduled_local")
            require(isinstance(local, str) and local[:10] == day, "SCHEDULE_DATE_MISMATCH")
            require(review.get("timezone") == "America/New_York", "INVALID_SCHEDULE_ZONE")
            schedules.add(local_instant(local, review["timezone"], review.get("offset", "")))
        elif e_kind == "PUBLIC_RELEASE_LOG":
            # Different URL alone is insufficient: review must attest independence
            # of custody and exact times for these bytes, not a mirror of a schedule.
            require(not official(host) and host != url_host(row["source_url"]),
                    "NOT_INDEPENDENT_EVIDENCE")
            require(review.get("assertion") == "ACTUAL_PUBLICATION_AND_AVAILABILITY_FOR_EXACT_BYTES"
                    and review.get("independent_custody") is True, "INSUFFICIENT_PUBLIC_PROOF")
            require(bool(row["source_sha256"]), "MISSING_SOURCE_BYTES")
            for key in ("published_at_utc", "available_at_utc"):
                value = text(review.get(key), key)
                require(value in quote, "TIME_NOT_IN_DOCUMENT", key)
            require(row["source_sha256"] in quote, "VERSION_NOT_IN_DOCUMENT")
            published, available = (instant(review[k]) for k in ("published_at_utc", "available_at_utc"))
            require(published <= available, "AVAILABLE_BEFORE_PUBLICATION")
            require(available <= instant(e["captured_at_utc"]), "EVIDENCE_FROM_FUTURE")
            if revision == "INITIAL":
                require(published.astimezone(ZoneInfo("America/New_York")).date() == release,
                        "PUBLICATION_DATE_MISMATCH")
            else:
                require(published.astimezone(ZoneInfo("America/New_York")).date() >= release,
                        "CORRECTION_BEFORE_RELEASE_DATE")
            proofs.add((iso(published), iso(available)))
        elif e_kind in {"ARCHIVE_CAPTURE", "HTTP_METADATA", "REPORTED_DATE", "CORRECTION_NOTICE"}:
            # An archive proves at most an upper bound, never first publication.
            if e_kind == "ARCHIVE_CAPTURE":
                bound = text(review.get("observed_public_by_utc"), "archive bound")
                require(bound in quote, "TIME_NOT_IN_DOCUMENT", "archive bound")
                require(instant(bound) <= instant(e["captured_at_utc"]), "EVIDENCE_FROM_FUTURE")
                bounds.append(iso(bound))
        else:
            raise AuditError("INVALID_EVIDENCE_KIND", str(e_kind))
    row["documentary_evidence"] = json.dumps(documentary, ensure_ascii=False, sort_keys=True)
    row["observed_public_by_utc"] = min(bounds, key=instant) if bounds else ""
    reasons = []
    conflict = len(proofs) > 1 or len(schedules) > 1
    if len(proofs) == 1:
        published, available = next(iter(proofs))
        if bounds and instant(min(bounds, key=instant)) < instant(available):
            conflict = True
            reasons.append("ARCHIVE_BOUND_CONFLICT")
        if row["retrieved_at_utc"] and instant(available) > instant(row["retrieved_at_utc"]):
            raise AuditError("UNAVAILABLE_AT_RETRIEVAL")
        if not conflict:
            row.update(published_at_utc=published, available_at_utc=available,
                       timestamp_quality=VERIFIED, quality_status="OK")
            if revision == "INITIAL":
                row["first_published_at_utc"] = published
            else:
                row["corrected_at_utc"] = published
            selected = [e for e in documentary if e["kind"] == "PUBLIC_RELEASE_LOG"]
            # Main evidence columns are for verified proof only, per shared contract.
            for column, key in (("evidence_url", "url"), ("evidence_sha256", "sha256"),
                                ("evidence_format", "format")):
                row[column] = "|".join(sorted({e[key] for e in selected}))
            reasons.append("REVIEWED_INDEPENDENT_EXACT_BYTE_TIME_EVIDENCE")
    if conflict:
        reasons.append("CONFLICTING_TIMESTAMP_EVIDENCE")
    elif not proofs and schedules:
        row.update(timestamp_quality=PROXY, official_schedule_utc=next(iter(schedules)))
        reasons.append("OFFICIAL_SCHEDULE_IS_NOT_ACTUAL_AVAILABILITY")
    elif not proofs:
        reasons.append("NO_INDEPENDENT_EXACT_PUBLIC_TIMESTAMP_EVIDENCE")
    if schedules and not conflict:
        row["official_schedule_utc"] = next(iter(schedules))
    if bounds:
        reasons.append("ARCHIVE_CAPTURE_IS_UPPER_BOUND_ONLY")
    if not row["retrieved_at_utc"]:
        reasons.append("SIGNAL_RETRIEVAL_UNPROVEN")
    if not row["source_sha256"]:
        reasons.append("SOURCE_BYTES_MISSING")
    row["reason"] = ";".join(reasons)
    return row


def audit_records(records: list[dict], root: Path) -> tuple[list[dict], list[dict]]:
    require(isinstance(records, list), "INVALID_RECORDS")
    rows, errors, identities = [], [], set()
    for index, record in enumerate(records):
        try:
            row = audit_record(record, root)
            key = (row["source_type"], row["source_release_date"], row["vintage_id"])
            require(key not in identities, "DUPLICATE_VINTAGE", str(key))
            identities.add(key)
            rows.append(row)
        except (AuditError, TypeError, AttributeError, KeyError) as exc:
            errors.append({"record_index": index, "error": str(exc)})
    lookup = {(r["source_type"], r["source_release_date"], r["vintage_id"]): r for r in rows}
    # Resolve full ancestry: no correction can borrow an initial release's time.
    def initial(row: dict, seen: set) -> dict:
        key = (row["source_type"], row["source_release_date"], row["vintage_id"])
        require(key not in seen, "REVISION_CYCLE")
        if row["revision_kind"] == "INITIAL":
            return row
        predecessor = lookup.get((row["source_type"], row["source_release_date"], row["supersedes_vintage_id"]))
        require(predecessor is not None, "MISSING_PREDECESSOR")
        require(predecessor["source_sha256"] != row["source_sha256"]
                or not row["source_sha256"], "UNCHANGED_CORRECTION_BYTES")
        if row["published_at_utc"] and predecessor["published_at_utc"]:
            require(instant(row["published_at_utc"]) > instant(predecessor["published_at_utc"]),
                    "CORRECTION_TIME_ORDER")
        return initial(predecessor, seen | {key})
    for row in rows:
        try:
            origin = initial(row, set())
            if row["revision_kind"] == "CORRECTION":
                row["first_published_at_utc"] = origin["first_published_at_utc"]
        except AuditError as exc:
            errors.append({"vintage_id": row["vintage_id"], "error": str(exc)})
    # A malformed/duplicate record could conceal a conflicting vintage. Block
    # the whole bundle rather than certify the surviving subset.
    if errors:
        for row in rows:
            row.update(timestamp_quality=UNKNOWN, quality_status="INPUT_VALIDATION_FAILED",
                       published_at_utc="", available_at_utc="", first_published_at_utc="",
                       corrected_at_utc="", evidence_url="", evidence_sha256="", evidence_format="")
            row["reason"] += ";BUNDLE_VALIDATION_FAILED"
    return sorted(rows, key=lambda r: (r["source_type"], r["source_release_date"], r["vintage_id"])), errors


def check_asof(row: dict, as_of: str, *, mode: str = "SYSTEM_REPLAY") -> None:
    """Call on re-audited rows, never an untrusted producer row or CSV alone."""
    require(mode in {"SYSTEM_REPLAY", "PUBLIC_INFORMATION_AUDIT"}, "INVALID_ASOF_MODE")
    cutoff = instant(as_of)
    require(row.get("timestamp_quality") == VERIFIED and row.get("quality_status") == "OK",
            "PIT_UNVERIFIED")
    published, available = instant(row.get("published_at_utc")), instant(row.get("available_at_utc"))
    require(published <= available, "AVAILABLE_BEFORE_PUBLICATION")
    require(published <= cutoff and available <= cutoff, "FUTURE_DATA")
    if mode == "SYSTEM_REPLAY":
        require(bool(row.get("retrieved_at_utc")), "RETRIEVAL_UNPROVEN")
        require(available <= instant(row["retrieved_at_utc"]), "UNAVAILABLE_AT_RETRIEVAL")
        require(instant(row["retrieved_at_utc"]) <= cutoff, "NOT_YET_RETRIEVED")


def load_manifest(path: Path) -> dict:
    try:
        manifest = parse_json(path.read_bytes())
    except (OSError, ValueError, UnicodeError) as exc:
        raise AuditError("INVALID_MANIFEST", str(path)) from exc
    require(isinstance(manifest, dict) and manifest.get("schema_version") == 1,
            "INVALID_MANIFEST_SCHEMA")
    require(isinstance(manifest.get("records"), list), "INVALID_RECORDS")
    return manifest


def certify_manifest(path: Path, as_of: str, *, mode: str = "SYSTEM_REPLAY") -> dict:
    """Recheck raw hashes and reviews before issuing an as-of-scoped result."""
    manifest = load_manifest(path)
    rows, errors = audit_records(manifest["records"], path.parent)
    require(not errors, "BUNDLE_VALIDATION_FAILED", json.dumps(errors))
    require(bool(rows), "EMPTY_CERTIFICATION_COHORT")
    for row in rows:
        check_asof(row, as_of, mode=mode)
    return {"status": "ASOF_CHECK_PASSED", "mode": mode, "as_of_utc": iso(as_of),
            "manifest_sha256": sha(path.read_bytes()), "row_count": len(rows),
            "signal_historical_possession_claim": mode == "SYSTEM_REPLAY"}


def run(path: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest = None
    source_access = []
    try:
        manifest = load_manifest(path)
        access = manifest.get("source_access")
        if access:
            source_access = parse_json(checked_bytes(path.parent, access["path"], access["sha256"]))
            require(isinstance(source_access, list), "INVALID_SOURCE_ACCESS")
            require(all(isinstance(item, dict) for item in source_access), "INVALID_SOURCE_ACCESS")
        rows, errors = audit_records(manifest["records"], path.parent)
    except (AuditError, ValueError, TypeError, KeyError) as exc:
        rows, errors = [], [{"error": str(exc)}]
        source_access = []
    counts = {quality: sum(r["timestamp_quality"] == quality for r in rows) for quality in QUALITIES}
    coverage = []
    for kind in KINDS:
        for year in YEARS:
            subset = [r for r in rows if r["source_type"] == kind and r["source_release_date"].startswith(str(year))]
            coverage.append({"source_type": kind, "year": year, "record_count": len(subset),
                             "counts": {q: sum(r["timestamp_quality"] == q for r in subset) for q in QUALITIES},
                             "status": "PARTIAL_INVENTORY_NOT_COMPLETENESS_PROOF" if subset else "NO_RELEASE_INVENTORY",
                             "expected_release_count": None})
    gaps = [{"source_type": c["source_type"], "year": c["year"],
             "missing": "official release inventory, original bytes, historical exact public-time evidence, SIGNAL retrieval receipts"}
            for c in coverage if not c["record_count"]]
    unverified = [{k: r[k] for k in ("source_type", "source_release_date", "source_url", "vintage_id", "reason")}
                  for r in rows if r["timestamp_quality"] != VERIFIED]
    status = ("INPUT_VALIDATION_FAILED" if errors else
              "SOURCE_FEASIBILITY_BLOCKED" if not rows else "AUDITED_REQUIRES_ASOF_GATE")
    report = {"version": "K3.7-PIT-v1", "status": status,
              "manifest_sha256": sha(path.read_bytes()) if path.is_file() else "",
              "input_record_count": len(manifest["records"]) if manifest else 0,
              "ledger_record_count": len(rows),
              "rejected_record_count": len(manifest["records"]) - len(rows) if manifest else 0,
              "validation_error_count": len(errors),
              "counts": counts, "asof_certified_count": 0,
              "coverage": coverage, "source_year_gaps": gaps, "unverified_records": unverified,
              "source_access": source_access, "errors": errors,
              "limitations": [
                  "A zero-row ledger is not six UNKNOWN releases; six source/year inventories are missing.",
                  "No missing dates, weeks or release counts are inferred.",
                  "Verified documentary time evidence still requires an explicit as-of gate and exact source-byte join.",
                  "Reviewed documentary interpretations trust the reviewer; hashes do not authenticate an issuer.",
                  "An archive capture is an upper bound, not first-publication proof.",
                  "SYSTEM_REPLAY additionally requires an authentic contemporaneous SIGNAL download receipt.",
                  "No producer A/B data is integrated; source URLs/dates/vintages/digests must match before use.",
              ]}
    with (output / "pit_evidence_ledger.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (output / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "rejections.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# K3.7 Agent C PIT 證據品質報告", "", f"狀態：`{status}`。", "",
             f"輸入 {report['input_record_count']} 筆；ledger {len(rows)} 筆；拒絕／錯誤 {len(errors)} 筆。", "",
             "| VERIFIED | PROXY | UNKNOWN | 已通過 as-of 認證 |", "|---:|---:|---:|---:|",
             f"| {counts[VERIFIED]} | {counts[PROXY]} | {counts[UNKNOWN]} | 0 |", "",
             "沒有發布清單時，不產生虛構 UNKNOWN 紀錄；下列缺口是來源／年度，並非已知發布筆數。", "",
             "| 來源 | 年度 | 實際紀錄 | 清單狀態 |", "|---|---:|---:|---|"]
    lines.extend(f"| {c['source_type']} | {c['year']} | {c['record_count']} | {c['status']} |" for c in coverage)
    lines += ["", "## 尚缺證據", ""]
    lines.extend(f"- {g['source_type']} {g['year']}：官方逐期發布清單、原始檔、歷史實際公開時間證據及 SIGNAL 下載收據。" for g in gaps)
    lines.extend(f"- {r['source_type']} {r['source_release_date']} {r['vintage_id']}：{r['reason']}" for r in unverified)
    lines += ["", "## 來源存取紀錄", ""]
    lines.extend(f"- {a.get('url')}：{a.get('status')}；嘗試時間 {a.get('attempted_at_utc')}；{a.get('error', '')}" for a in source_access)
    lines += ["", "## 驗收限制", "",
              "稽核與資料取得成功均不自動代表正式 PIT 認證。預設 SYSTEM_REPLAY 必須驗證公開時間與 SIGNAL 實際取得時間皆不晚於 as-of；PUBLIC_INFORMATION_AUDIT 必須明確標示，不能宣稱 SIGNAL 當年已持有資料。", "",
              "人工核准的文件解讀是信任邊界。SHA-256 核對只證明保存位元組一致，不認證第三方真實性；官方排程、HTTP Date／Last-Modified、目前下載時間及檔案 mtime 皆不足以認證歷史公開時間。", "",
              "Agent D 後續必須以 source_type、source_release_date、source_url、vintage_id、source_sha256 精確核對，重新稽核原始證據並執行 as-of gate。不得只依日期 join 或信任 CSV 分級欄位。", ""]
    if errors:
        lines += ["## 錯誤", "", *[f"- {e}" for e in errors], ""]
    (output / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "inputs" / "manifest.json")
    parser.add_argument("--output", type=Path, default=HERE / "out")
    parser.add_argument("--as-of", help="Require every input to pass the as-of certification gate")
    parser.add_argument("--mode", choices=("SYSTEM_REPLAY", "PUBLIC_INFORMATION_AUDIT"), default="SYSTEM_REPLAY")
    args = parser.parse_args(argv)
    report = run(args.manifest, args.output)
    print(json.dumps({k: report[k] for k in ("status", "counts", "ledger_record_count")}, ensure_ascii=False))
    if report["errors"]:
        return 2
    if args.as_of:
        try:
            print(json.dumps(certify_manifest(args.manifest, args.as_of, mode=args.mode)))
        except AuditError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

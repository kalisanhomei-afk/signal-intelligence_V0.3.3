"""Deterministic synthetic fixtures; no network and no real USDA observations."""
import copy
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from research_core.k3_7.pit import audit as a
from research_core.k3_7.pit import collect


FIXTURE = json.loads((a.HERE / "fixtures" / "scenarios.json").read_text())


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.put("source.txt", FIXTURE["source_bytes"].encode())
        self.record = dict(source_type="WASDE", source_release_date="2020-06-08",
                           source_url=FIXTURE["source_url"], source_sha256=self.source["sha256"],
                           source_path=self.source["path"], vintage_id="initial", revision_kind="INITIAL",
                           evidence=[])

    def put(self, name, raw):
        path = self.root / name
        path.write_bytes(raw)
        return {"path": name, "sha256": a.sha(raw)}

    def review(self, record):
        return {**{k: record.get(k, "") for k in
                   ("source_type", "source_release_date", "source_url", "source_sha256", "vintage_id")},
                "verdict": "APPROVED", "reviewer": "SYNTHETIC-REVIEWER",
                "reviewed_at_utc": FIXTURE["reviewed"], "reason": "SYNTHETIC TEST ONLY"}

    def proof(self, record=None, published=None, available=None, name="proof.txt"):
        record = record or self.record
        published = published or FIXTURE["published"]
        available = available or FIXTURE["available"]
        quote = f"SYNTHETIC actual publication {published}; exact public availability {available}; bytes {record['source_sha256']}"
        entry = {**self.put(name, quote.encode()), "kind": "PUBLIC_RELEASE_LOG",
                 "url": FIXTURE["independent_url"], "format": "text/plain",
                 "captured_at_utc": FIXTURE["retrieved"],
                 "review": {**self.review(record), "quote": quote,
                            "assertion": "ACTUAL_PUBLICATION_AND_AVAILABILITY_FOR_EXACT_BYTES",
                            "independent_custody": True, "published_at_utc": published,
                            "available_at_utc": available}}
        record["evidence"].append(entry)
        return entry

    def receipt(self, record=None, finished=None):
        record = record or self.record
        finished = finished or FIXTURE["retrieved"]
        raw = json.dumps({"kind": "SIGNAL_HTTP_DOWNLOAD_V1", "source_url": record["source_url"],
                          "source_sha256": record["source_sha256"], "started_at_utc": finished,
                          "finished_at_utc": finished}).encode()
        record["retrieval_receipt"] = self.put(record["vintage_id"] + ".receipt.json", raw)

    def schedule(self, record=None):
        record = record or self.record
        quote = "SYNTHETIC official schedule: WASDE at 12:00 ET; this is not an actual release log."
        entry = {**self.put("schedule.txt", quote.encode()), "kind": "OFFICIAL_SCHEDULE",
                 "url": "https://www.usda.gov/synthetic-schedule", "format": "text/plain",
                 "captured_at_utc": FIXTURE["retrieved"],
                 "review": {**self.review(record), "quote": quote, "assertion": "SCHEDULE_ONLY",
                            "scheduled_local": record["source_release_date"] + "T12:00:00",
                            "timezone": "America/New_York"}}
        record["evidence"].append(entry)
        return entry

    def manifest(self, records=None):
        path = self.root / "manifest.json"
        path.write_text(json.dumps({"schema_version": 1, "records": records if records is not None else [self.record]}))
        return path

    def rows(self, records=None):
        return a.audit_records(records if records is not None else [self.record], self.root)

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(a.AuditError) as cm:
            function(*args, **kwargs)
        self.assertEqual(cm.exception.code, code)

    def test_missing_evidence_stays_unknown(self):
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.UNKNOWN)
        self.assertEqual(row["available_at_utc"], "")
        self.assert_code("PIT_UNVERIFIED", a.check_asof, row, FIXTURE["reviewed"])

    def test_schedule_never_verifies_even_with_download(self):
        self.schedule()
        self.receipt()
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.PROXY)
        self.assertEqual(row["official_schedule_utc"], FIXTURE["published"])
        for key in ("published_at_utc", "available_at_utc", "evidence_url", "evidence_sha256"):
            self.assertEqual(row[key], "")
        self.assertIn("schedule.txt", row["documentary_evidence"])
        self.assert_code("PIT_UNVERIFIED", a.check_asof, row, FIXTURE["reviewed"])

    def test_producer_claims_are_not_evidence(self):
        self.record.update(timestamp_quality=a.VERIFIED, published_at_utc=FIXTURE["published"],
                           available_at_utc=FIXTURE["available"], pit_certified="true")
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.UNKNOWN)
        self.assertEqual(row["pit_certified"], "false")

    def test_verified_proof_keeps_all_documentary_fields(self):
        entry = self.proof()
        self.receipt()
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.VERIFIED)
        self.assertEqual(row["evidence_sha256"], entry["sha256"])
        self.assertEqual(row["first_published_at_utc"], FIXTURE["published"])
        self.assertEqual(row["retrieved_at_utc"], FIXTURE["retrieved"])
        self.assertEqual(row["pit_certified"], "false")

    def test_download_cannot_be_backdated_by_producer(self):
        self.record["retrieved_at_utc"] = FIXTURE["published"]
        self.assert_code("UNSUPPORTED_RETRIEVAL_CLAIM", a.audit_record, self.record, self.root)

    def test_system_replay_blocks_current_download_at_historical_origin(self):
        self.proof()
        self.receipt()
        row = a.audit_record(self.record, self.root)
        self.assert_code("NOT_YET_RETRIEVED", a.check_asof, row, "2020-06-08T17:00:00Z")
        a.check_asof(row, "2020-06-08T17:00:00Z", mode="PUBLIC_INFORMATION_AUDIT")

    def test_no_receipt_blocks_system_replay(self):
        self.proof()
        row = a.audit_record(self.record, self.root)
        self.assert_code("RETRIEVAL_UNPROVEN", a.check_asof, row, FIXTURE["reviewed"])

    def test_same_day_before_and_at_exact_availability(self):
        self.proof()
        row = a.audit_record(self.record, self.root)
        self.assert_code("FUTURE_DATA", a.check_asof, row, FIXTURE["published"], mode="PUBLIC_INFORMATION_AUDIT")
        a.check_asof(row, FIXTURE["available"], mode="PUBLIC_INFORMATION_AUDIT")

    def test_same_day_nass_after_wasde_is_future(self):
        self.record["source_type"] = "NASS"
        self.proof(published="2020-06-08T20:00:00Z", available="2020-06-08T20:00:01Z")
        row = a.audit_record(self.record, self.root)
        self.assert_code("FUTURE_DATA", a.check_asof, row, "2020-06-08T16:00:00Z", mode="PUBLIC_INFORMATION_AUDIT")

    def test_timezone_equivalent_asof(self):
        self.proof()
        row = a.audit_record(self.record, self.root)
        for cutoff in ("2020-06-08T12:00:01-04:00", "2020-06-09T00:00:01+08:00", FIXTURE["available"]):
            a.check_asof(row, cutoff, mode="PUBLIC_INFORMATION_AUDIT")

    def test_all_pilot_years_summer_and_winter(self):
        for year in a.YEARS:
            for month, expected in (("01", "17"), ("07", "16")):
                with self.subTest(year=year, month=month):
                    self.assertEqual(a.local_instant(f"{year}-{month}-10T12:00:00", "America/New_York"),
                                     f"{year}-{month}-10T{expected}:00:00Z")

    def test_dst_spring_transition_each_pilot_year(self):
        for day in ("2016-03-13", "2020-03-08", "2022-03-13"):
            with self.subTest(day=day):
                self.assert_code("NONEXISTENT_LOCAL_TIME", a.local_instant, day + "T02:30:00", "America/New_York")
                self.assertEqual(a.local_instant(day + "T03:30:00", "America/New_York"), day + "T07:30:00Z")

    def test_dst_fall_fold_and_explicit_offset_each_pilot_year(self):
        for day in ("2016-11-06", "2020-11-01", "2022-11-06"):
            with self.subTest(day=day):
                value = day + "T01:30:00"
                self.assert_code("AMBIGUOUS_LOCAL_TIME", a.local_instant, value, "America/New_York")
                self.assertEqual(a.local_instant(value, "America/New_York", "-04:00"), day + "T05:30:00Z")
                self.assertEqual(a.local_instant(value, "America/New_York", "-05:00"), day + "T06:30:00Z")
                self.assert_code("OFFSET_ZONE_MISMATCH", a.local_instant, value, "America/New_York", "+08:00")

    def test_naive_and_date_only_timestamps_fail(self):
        self.assert_code("NAIVE_TIME", a.instant, "2020-06-08T12:00:00")
        self.assert_code("INVALID_TIME", a.instant, "2020-06-08")

    def test_conflicting_independent_timestamps_downgrade_unknown(self):
        self.proof()
        self.proof(available="2020-06-08T16:01:00Z", name="other.txt")
        self.schedule()
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.UNKNOWN)
        self.assertEqual(row["published_at_utc"], "")
        self.assertIn("CONFLICTING_TIMESTAMP_EVIDENCE", row["reason"])

    def test_equivalent_offsets_do_not_conflict(self):
        self.proof()
        self.proof(published="2020-06-08T12:00:00-04:00", available="2020-06-08T12:00:01-04:00", name="other.txt")
        self.assertEqual(a.audit_record(self.record, self.root)["timestamp_quality"], a.VERIFIED)

    def test_source_and_evidence_tampering_rejected(self):
        self.proof()
        (self.root / "source.txt").write_text("tampered")
        self.assert_code("HASH_MISMATCH", a.audit_record, self.record, self.root)
        (self.root / "source.txt").write_bytes(FIXTURE["source_bytes"].encode())
        (self.root / "proof.txt").write_text("tampered")
        self.assert_code("HASH_MISMATCH", a.audit_record, self.record, self.root)

    def test_unreviewed_or_missing_document_is_not_verified(self):
        entry = self.proof()
        entry["review"]["verdict"] = "PENDING"
        self.assert_code("UNREVIEWED_EVIDENCE", a.audit_record, self.record, self.root)
        entry["review"]["verdict"] = "APPROVED"
        (self.root / "proof.txt").unlink()
        self.assert_code("MISSING_ARTIFACT", a.audit_record, self.record, self.root)

    def test_quote_and_timestamp_must_be_in_raw_document(self):
        entry = self.proof()
        entry["review"]["available_at_utc"] = "2020-06-08T16:00:02Z"
        self.assert_code("TIME_NOT_IN_DOCUMENT", a.audit_record, self.record, self.root)
        entry["review"]["quote"] = "invented text"
        self.assert_code("QUOTE_NOT_IN_DOCUMENT", a.audit_record, self.record, self.root)

    def test_duplicate_json_keys_cannot_conceal_conflicting_claims(self):
        self.assert_code("DUPLICATE_JSON_KEY", a.parse_json, b'{"timestamp":"old","timestamp":"new"}')

    def test_publication_date_uses_new_york_not_utc_calendar_day(self):
        self.proof(published="2020-06-09T00:30:00Z", available="2020-06-09T00:30:01Z")
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.VERIFIED)
        self.record["evidence"] = []
        self.proof(published="2020-06-08T00:30:00Z", available="2020-06-08T00:30:01Z")
        self.assert_code("PUBLICATION_DATE_MISMATCH", a.audit_record, self.record, self.root)

    def test_review_and_public_evidence_chronology_checked(self):
        entry = self.proof()
        entry["review"]["reviewed_at_utc"] = "2020-06-08T10:00:00Z"
        self.assert_code("REVIEW_BEFORE_CAPTURE", a.audit_record, self.record, self.root)
        entry["review"]["reviewed_at_utc"] = FIXTURE["reviewed"]
        entry["captured_at_utc"] = "2020-06-08T10:00:00Z"
        self.assert_code("EVIDENCE_FROM_FUTURE", a.audit_record, self.record, self.root)

    def test_schedule_relabelled_as_public_proof_rejected(self):
        entry = self.schedule()
        entry["kind"] = "PUBLIC_RELEASE_LOG"
        self.assert_code("NOT_INDEPENDENT_EVIDENCE", a.audit_record, self.record, self.root)
        entry["url"] = FIXTURE["independent_url"]
        self.assert_code("INSUFFICIENT_PUBLIC_PROOF", a.audit_record, self.record, self.root)

    def test_exact_byte_vintage_and_url_binding(self):
        entry = self.proof()
        for field in ("source_sha256", "vintage_id", "source_url", "source_release_date"):
            with self.subTest(field=field):
                old = entry["review"][field]
                entry["review"][field] = "other"
                self.assert_code("EVIDENCE_BINDING_MISMATCH", a.audit_record, self.record, self.root)
                entry["review"][field] = old

    def test_archive_capture_upper_bound_not_first_availability(self):
        bound = "2020-06-10T08:00:00Z"
        quote = "SYNTHETIC archive capture " + bound
        entry = {**self.put("archive.txt", quote.encode()), "kind": "ARCHIVE_CAPTURE",
                 "url": FIXTURE["independent_url"], "format": "text/plain",
                 "captured_at_utc": FIXTURE["retrieved"],
                 "review": {**self.review(self.record), "quote": quote, "observed_public_by_utc": bound}}
        self.record["evidence"].append(entry)
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.UNKNOWN)
        self.assertEqual(row["observed_public_by_utc"], bound)
        self.assertEqual(row["available_at_utc"], "")
        self.proof()
        entry["review"]["observed_public_by_utc"] = "2020-06-08T15:00:00Z"
        entry["review"]["quote"] = "SYNTHETIC archive capture 2020-06-08T15:00:00Z"
        updated = self.put("archive.txt", entry["review"]["quote"].encode())
        entry.update(updated)
        self.assertEqual(a.audit_record(self.record, self.root)["timestamp_quality"], a.UNKNOWN)

    def test_http_metadata_and_reported_date_are_unknown(self):
        for kind in ("HTTP_METADATA", "REPORTED_DATE", "CORRECTION_NOTICE"):
            with self.subTest(kind=kind):
                entry = self.proof()
                entry["kind"] = kind
                self.assertEqual(a.audit_record(self.record, self.root)["timestamp_quality"], a.UNKNOWN)
                self.record["evidence"] = []

    def correction(self):
        correction = copy.deepcopy(self.record)
        correction.update(vintage_id="correction", revision_kind="CORRECTION",
                          supersedes_vintage_id="initial", evidence=[])
        artifact = self.put("correction.txt", FIXTURE["correction_bytes"].encode())
        correction.update(source_path=artifact["path"], source_sha256=artifact["sha256"])
        correction.pop("retrieval_receipt", None)
        return correction

    def test_later_correction_never_uses_first_release_time(self):
        self.proof()
        correction = self.correction()
        self.proof(correction, FIXTURE["correction_published"], FIXTURE["correction_available"], "correction-proof.txt")
        rows, errors = self.rows([correction, self.record])
        self.assertFalse(errors)
        changed = next(r for r in rows if r["revision_kind"] == "CORRECTION")
        self.assertEqual(changed["first_published_at_utc"], FIXTURE["published"])
        self.assertEqual(changed["published_at_utc"], FIXTURE["correction_published"])
        self.assertEqual(changed["corrected_at_utc"], FIXTURE["correction_published"])
        self.assert_code("FUTURE_DATA", a.check_asof, changed, "2020-06-08T17:00:00Z", mode="PUBLIC_INFORMATION_AUDIT")

    def test_missing_correction_proof_is_unknown(self):
        self.proof()
        rows, errors = self.rows([self.record, self.correction()])
        self.assertFalse(errors)
        changed = next(r for r in rows if r["revision_kind"] == "CORRECTION")
        self.assertEqual(changed["timestamp_quality"], a.UNKNOWN)
        self.assertEqual(changed["available_at_utc"], "")

    def test_correction_cannot_reuse_original_release_clock(self):
        self.proof()
        correction = self.correction()
        self.proof(correction, name="correction-proof.txt")
        rows, errors = self.rows([self.record, correction])
        self.assertTrue(any("CORRECTION_TIME_ORDER" in e["error"] for e in errors))
        self.assertTrue(all(r["timestamp_quality"] == a.UNKNOWN for r in rows))

    def test_correction_cannot_relabel_unchanged_bytes(self):
        self.proof()
        correction = self.correction()
        correction.update(source_path=self.record["source_path"], source_sha256=self.record["source_sha256"])
        rows, errors = self.rows([self.record, correction])
        self.assertTrue(any("UNCHANGED_CORRECTION_BYTES" in e["error"] for e in errors))

    def test_missing_predecessor_and_revision_cycle_block_bundle(self):
        correction = self.correction()
        rows, errors = self.rows([correction])
        self.assertIn("MISSING_PREDECESSOR", errors[0]["error"])
        self.record.update(revision_kind="CORRECTION", supersedes_vintage_id="correction")
        rows, errors = self.rows([self.record, correction])
        self.assertTrue(any("REVISION_CYCLE" in e["error"] for e in errors))
        self.assertTrue(all(r["timestamp_quality"] == a.UNKNOWN for r in rows))

    def test_duplicate_vintage_blocks_entire_bundle(self):
        self.proof()
        rows, errors = self.rows([self.record, self.record])
        self.assertIn("DUPLICATE_VINTAGE", errors[0]["error"])
        self.assertEqual(rows[0]["timestamp_quality"], a.UNKNOWN)

    def test_bad_record_cannot_hide_conflict_in_surviving_subset(self):
        self.proof()
        malformed = copy.deepcopy(self.record)
        malformed["source_type"] = "BAD"
        rows, errors = self.rows([self.record, malformed])
        self.assertTrue(errors)
        self.assertEqual(rows[0]["quality_status"], "INPUT_VALIDATION_FAILED")

    def test_available_after_retrieval_and_before_publication_rejected(self):
        self.proof()
        self.receipt(finished="2020-06-08T16:00:00Z")
        self.assert_code("UNAVAILABLE_AT_RETRIEVAL", a.audit_record, self.record, self.root)
        self.record.pop("retrieval_receipt")
        self.record["evidence"] = []
        self.proof(published="2020-06-08T16:00:02Z")
        self.assert_code("AVAILABLE_BEFORE_PUBLICATION", a.audit_record, self.record, self.root)

    def test_path_escape_and_symlink_rejected(self):
        self.assert_code("ARTIFACT_OUTSIDE_BUNDLE", a.checked_bytes, self.root, "../other", "a" * 64)
        (self.root / "link").symlink_to(self.root.parent)
        self.assert_code("ARTIFACT_OUTSIDE_BUNDLE", a.checked_bytes, self.root, "link/other", "a" * 64)

    def test_out_of_scope_year_and_malformed_date_rejected(self):
        self.record["source_release_date"] = "2023-06-08"
        self.assert_code("OUTSIDE_PILOT_YEARS", a.audit_record, self.record, self.root)
        self.record["source_release_date"] = "2020-02-30"
        self.assert_code("INVALID_RELEASE_DATE", a.audit_record, self.record, self.root)

    def test_missing_source_bytes_can_only_remain_unknown(self):
        self.record.pop("source_sha256")
        self.record.pop("source_path")
        row = a.audit_record(self.record, self.root)
        self.assertEqual(row["timestamp_quality"], a.UNKNOWN)
        self.assertIn("SOURCE_BYTES_MISSING", row["reason"])

    def test_empty_inventory_is_six_gaps_not_six_invented_rows(self):
        path = self.manifest([])
        report = a.run(path, self.root / "out")
        self.assertEqual(report["status"], "SOURCE_FEASIBILITY_BLOCKED")
        self.assertEqual(report["counts"], {q: 0 for q in a.QUALITIES})
        self.assertEqual(len(report["source_year_gaps"]), 6)
        self.assertEqual(report["ledger_record_count"], 0)
        self.assert_code("EMPTY_CERTIFICATION_COHORT", a.certify_manifest, path, FIXTURE["reviewed"])

    def test_report_counts_csv_escaping_and_deterministic_replay(self):
        self.schedule()
        path = self.manifest()
        report = a.run(path, self.root / "out")
        self.assertEqual(report["counts"][a.PROXY], 1)
        raw = (self.root / "out" / "pit_evidence_ledger.csv").read_bytes()
        a.run(path, self.root / "out")
        self.assertEqual(raw, (self.root / "out" / "pit_evidence_ledger.csv").read_bytes())
        with (self.root / "out" / "pit_evidence_ledger.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(json.loads(rows[0]["documentary_evidence"])[0]["kind"], "OFFICIAL_SCHEDULE")

    def test_manifest_certification_rechecks_hash_not_csv(self):
        self.proof()
        self.receipt()
        path = self.manifest()
        result = a.certify_manifest(path, FIXTURE["reviewed"])
        self.assertEqual(result["mode"], "SYSTEM_REPLAY")
        self.assertTrue(result["signal_historical_possession_claim"])
        (self.root / "proof.txt").write_text("tampered after audit")
        self.assert_code("BUNDLE_VALIDATION_FAILED", a.certify_manifest, path, FIXTURE["reviewed"])

    def test_cli_invalid_input_writes_report_and_nonzero(self):
        path = self.root / "bad.json"
        path.write_text("invalid json")
        with redirect_stdout(io.StringIO()):
            code = a.main(["--manifest", str(path), "--output", str(self.root / "out")])
        self.assertEqual(code, 2)
        report = json.loads((self.root / "out" / "quality_report.json").read_text())
        self.assertEqual(report["status"], "INPUT_VALIDATION_FAILED")
        self.assertEqual(report["asof_certified_count"], 0)

    def test_malformed_source_access_and_receipt_fail_closed(self):
        source_access = self.put("access.json", b'["invalid"]')
        path = self.manifest()
        obj = json.loads(path.read_bytes())
        obj["source_access"] = source_access
        path.write_text(json.dumps(obj))
        report = a.run(path, self.root / "out")
        self.assertEqual(report["status"], "INPUT_VALIDATION_FAILED")
        self.record["retrieval_receipt"] = self.put("bad-receipt.json", b'[]')
        self.assert_code("INVALID_RETRIEVAL_RECEIPT", a.audit_record, self.record, self.root)

    def test_cli_asof_fails_closed_on_unknown(self):
        path = self.manifest()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = a.main(["--manifest", str(path), "--output", str(self.root / "out"), "--as-of", FIXTURE["reviewed"]])
        self.assertEqual(code, 2)

    def test_public_audit_result_explicitly_disclaims_signal_possession(self):
        self.proof()
        result = a.certify_manifest(self.manifest(), FIXTURE["available"], mode="PUBLIC_INFORMATION_AUDIT")
        self.assertFalse(result["signal_historical_possession_claim"])
        self.assertEqual(result["mode"], "PUBLIC_INFORMATION_AUDIT")

    def test_offline_audit_never_opens_network(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network forbidden")):
            a.run(self.manifest(), self.root / "out")


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_current_download_ignores_historical_headers(self):
        class Response:
            headers = {"Last-Modified": "Mon, 08 Jun 2020 16:00:00 GMT"}
            def geturl(self): return FIXTURE["source_url"]
            def read(self, limit): return FIXTURE["source_bytes"].encode()
            def __enter__(self): return self
            def __exit__(self, *args): return False
        class Opener:
            def open(self, request, timeout): return Response()
        times = iter(["2026-11-13T12:00:00Z", "2026-11-13T12:00:01Z"])
        result = collect.capture(FIXTURE["source_url"], self.root, "source", opener=Opener(), clock=lambda: next(times))
        self.assertEqual(result["retrieved_at_utc"], "2026-11-13T12:00:01Z")
        self.assertEqual(result["status"], "FETCHED_LOCATOR_NOT_TIME_EVIDENCE")
        receipt = json.loads((self.root / "source.receipt.json").read_text())
        self.assertEqual(receipt["finished_at_utc"], result["retrieved_at_utc"])
        with self.assertRaises(a.AuditError):
            collect.capture(FIXTURE["source_url"], self.root, "source", opener=Opener())

    def test_blocked_capture_has_no_fabricated_retrieval_or_hash(self):
        class Opener:
            def open(self, request, timeout):
                raise collect.URLError("Tunnel connection failed: 403 Forbidden")
        result = collect.capture(FIXTURE["source_url"], self.root, "blocked", opener=Opener())
        self.assertEqual(result["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(result["retrieved_at_utc"], "")
        self.assertEqual(result["source_sha256"], "")
        self.assertFalse((self.root / "blocked.raw").exists())

    def test_nonofficial_redirect_rejected(self):
        with self.assertRaises(a.AuditError):
            collect.OfficialRedirects().redirect_request(None, None, 302, "", {}, "https://untrusted.example/test")
        with self.assertRaises(a.AuditError):
            collect.capture("https://usda.gov.attacker.example/test", self.root, "unsafe")

    def test_oversized_capture_does_not_create_a_receipt(self):
        class Response:
            def geturl(self): return FIXTURE["source_url"]
            def read(self, limit): return b"x" * limit
            def __enter__(self): return self
            def __exit__(self, *args): return False
        class Opener:
            def open(self, request, timeout): return Response()
        result = collect.capture(FIXTURE["source_url"], self.root, "large", opener=Opener())
        self.assertIn("OVERSIZED_SOURCE", result["error"])
        self.assertEqual(result["source_sha256"], "")
        self.assertFalse((self.root / "large.receipt.json").exists())


if __name__ == "__main__":
    unittest.main()

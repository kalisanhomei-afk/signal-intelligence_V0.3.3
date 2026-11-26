"""Offline synthetic response tests, never real 2026-12-03 EIA outcome data."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from research_core.k5.forward_event_score import evaluate, DEC03, blob_sha, DEC03_BLOB

PRIOR = Path(__file__).resolve().parents[1]/"evidence"/"eia"/"EIA_WNGSR_20261113_6eb6c699b789d713_original.json"


def synthetic_bytes(*,change=-30,current=3828,previous=3858):
    o=json.loads(PRIOR.read_text(encoding="utf-8-sig"))
    o["release_date"]="2026-Dec-03 00:00:00"
    o["current_week"]="2026-11-27"
    o["week_ago"]="2026-11-20"
    for s in o["series"]:
        if s.get("series_id")=="png.nw2_epg0_swo_r48_bcf.w":
            s["data"]=[["2026-11-27",current],["2026-11-20",previous],["2025-11-27",3800]]
            s["calculated"]["net_change"]=change
    return json.dumps(o,ensure_ascii=False,separators=(",",":")).encode("utf-8")


def receipt(raw):
    return {"source_url":"https://ir.eia.gov/ngs/wngsr.json",
            "response_url":"https://ir.eia.gov/secure/ngs/wngsr.json",
            "capture_started_utc":"2026-12-03T15:32:00Z",
            "capture_finished_utc":"2026-12-03T15:32:01Z",
            "source_raw_sha256":hashlib.sha256(raw).hexdigest(),
            "source_raw_bytes":len(raw),
            "first_published_pit_authenticated":False,
            "trade_eligible":False}


class EIAForwardScoreTests(unittest.TestCase):
    def setUp(self):
        self.frozen=DEC03.read_bytes()
        self.raw=synthetic_bytes()
        self.receipt=receipt(self.raw)

    def good(self, *,raw=None,receipt_=None,frozen=None):
        return evaluate(self.frozen if frozen is None else frozen,
                        event_raw=self.raw if raw is None else raw,
                        receipt=self.receipt if receipt_ is None else receipt_)

    def test_frozen_blob_and_absent_result(self):
        self.assertEqual(blob_sha(self.frozen),DEC03_BLOB)
        x=evaluate(self.frozen)
        self.assertEqual(x["status"],"WAITING_FOR_EIA_ORIGINAL_RAW_BYTES")
        self.assertIsNone(x["actual_net_change_bcf"])
        self.assertIsNone(x["absolute_error_bcf"])

    def test_synthetic_score_never_tradable(self):
        x=self.good()
        self.assertEqual(x["actual_net_change_bcf"],-30)
        self.assertEqual(x["absolute_error_bcf"],6)
        self.assertEqual(x["prior_stock_revision_vs_published_baseline_bcf"],0)
        self.assertFalse(x["trade_eligible"])
        self.assertFalse(x["independent_first_public_pit_verified"])
        self.assertFalse(x["market_consensus_pit_verified"])

    def test_capture_missing_rejected(self):
        with self.assertRaisesRegex(ValueError,"EIA_RAW_AND_RECEIPT_REQUIRED_TOGETHER"):
            evaluate(self.frozen,event_raw=self.raw)

    def test_forecast_tamper_rejected(self):
        x=json.loads(self.frozen)
        x["forecast_net_change_bcf"]=-23
        with self.assertRaisesRegex(ValueError,"FROZEN_FORECAST_BYTES_CHANGED"):
            self.good(frozen=json.dumps(x).encode())

    def test_wrong_release_rejected(self):
        x=json.loads(self.raw)
        x["release_date"]="2026-Nov-25 00:00:00"
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_RELEASE"):
            self.good(raw=json.dumps(x).encode())

    def test_wrong_target_week_rejected(self):
        x=json.loads(self.raw)
        x["current_week"]="2026-11-20"
        with self.assertRaisesRegex(ValueError,"WRONG_EIA_RELEASE"):
            self.good(raw=json.dumps(x).encode())

    def test_wrong_unit_rejected(self):
        x=json.loads(self.raw)
        x["series"][0]["unitsshort"]="Mcf"
        with self.assertRaisesRegex(ValueError,"EIA_SERIES_IDENTITY"):
            self.good(raw=json.dumps(x).encode())

    def test_duplicate_series_rejected(self):
        x=json.loads(self.raw)
        x["series"].append(copy.deepcopy(x["series"][0]))
        with self.assertRaisesRegex(ValueError,"EIA_LOWER48_SERIES"):
            self.good(raw=json.dumps(x).encode())

    def test_wrong_storage_reconciliation_rejected(self):
        x=synthetic_bytes(change=-30,current=3800,previous=3858)
        with self.assertRaisesRegex(ValueError,"EIA_STOCK_CHANGE_RECONCILIATION"):
            self.good(raw=x)

    def test_prior_stock_revision_preserved(self):
        raw=synthetic_bytes(change=-30,current=3830,previous=3860)
        x=self.good(raw=raw,receipt_=receipt(raw))
        self.assertEqual(x["prior_stock_revision_vs_published_baseline_bcf"],2)

    def test_forged_raw_sha_rejected(self):
        x=copy.deepcopy(self.receipt)
        x["source_raw_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"CAPTURE_RAW_SHA_MISMATCH"):
            self.good(receipt_=x)

    def test_capture_before_release_rejected(self):
        x=copy.deepcopy(self.receipt)
        x["capture_started_utc"]="2026-12-03T15:29:59Z"
        with self.assertRaisesRegex(ValueError,"CAPTURE_CHRONOLOGY_INVALID"):
            self.good(receipt_=x)

    def test_reversed_capture_rejected(self):
        x=copy.deepcopy(self.receipt)
        x["capture_finished_utc"]="2026-12-03T15:31:00Z"
        with self.assertRaisesRegex(ValueError,"CAPTURE_CHRONOLOGY_INVALID"):
            self.good(receipt_=x)

    def test_foreign_capture_host_rejected(self):
        x=copy.deepcopy(self.receipt)
        x["response_url"]="https://fake-eia.org/ngs/wngsr.json"
        with self.assertRaisesRegex(ValueError,"NON_OFFICIAL_EIA_CAPTURE"):
            self.good(receipt_=x)

    def test_fake_public_time_certification_rejected(self):
        x=copy.deepcopy(self.receipt)
        x["first_published_pit_authenticated"]=True
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_CAPTURE_SOURCE"):
            self.good(receipt_=x)

    def test_event_timestamp_with_timezone_offset_rejected(self):
        x=copy.deepcopy(self.receipt)
        x["capture_started_utc"]="2026-12-03T10:32:00-05:00"
        with self.assertRaisesRegex(ValueError,"UTC_TIMESTAMP_REQUIRED"):
            self.good(receipt_=x)

if __name__=="__main__": unittest.main()

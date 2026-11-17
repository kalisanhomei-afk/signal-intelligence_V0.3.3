"""K5.1 real committed official EIA prior-release evidence, byte-level regression."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

from research_core.k5.eia_prior_original_capture import validate_data

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"evidence/eia/EIA_WNGSR_20261113_6eb6c699b789d713_original.json"
RECEIPT=ROOT/"evidence/eia/EIA_WNGSR_20261113_6eb6c699b789d713_receipt.json"
FROZEN=ROOT/"cases/2026-11-19-eia-frozen-v0-forecast.json"
SHA256="6eb6c699b789d7130d3f50dbe5681e835b57bc25dd118380398169dda63fe252"

def utc(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise ValueError("INVALID_UTC")
    return datetime.fromisoformat(value[:-1]+"+00:00")

class RealEIAOriginalEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=RAW.read_bytes()
        cls.receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_git_stored_original_exact_bytes(self):
        self.assertEqual(len(self.raw),7197)
        self.assertTrue(self.raw.startswith(b"\xef\xbb\xbf{"))
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),SHA256)
        self.assertEqual(self.receipt["source_raw_sha256"],SHA256)
        self.assertEqual(self.receipt["source_raw_bytes"],len(self.raw))
        self.assertEqual(self.receipt["source_raw_file"],RAW.name)

    def test_original_numbers_reparsed_directly_from_bytes(self):
        parsed=validate_data(self.raw)
        self.assertEqual(parsed,self.receipt["source_report"])
        self.assertEqual(parsed["storage_bcf"],3862)
        self.assertEqual(parsed["prior_week_storage_bcf"],3801)
        self.assertEqual(parsed["five_year_average_storage_bcf"],3787)
        self.assertEqual(parsed["year_ago_storage_bcf"],3954)
        self.assertEqual(parsed["net_change_bcf"],61)

    def test_capture_utc_strictly_precedes_next_report(self):
        meta=self.receipt["source"]
        self.assertLessEqual(utc(meta["capture_started_utc"]),utc(meta["capture_finished_utc"]))
        self.assertLess(utc(meta["capture_finished_utc"]),
                        utc(self.receipt["next_eia_event_scheduled_utc"]))
        self.assertEqual(meta["requested_url"],"https://ir.eia.gov/ngs/wngsr.json")
        self.assertEqual(meta["response_host"],"ir.eia.gov")
        self.assertEqual(meta["response_path"],"/secure/ngs/wngsr.json")
        self.assertTrue(meta["signed_redirect_query_deliberately_omitted"])

    def test_retrospective_or_alpha_promotions_forbidden(self):
        r=self.receipt
        self.assertEqual(r["status"],"PRIOR_EIA_ORIGINAL_BYTES_CAPTURED_BEFORE_NEXT_EVENT")
        self.assertFalse(r["official_first_publication_time_independently_verified"])
        self.assertFalse(r["source_corrections_and_history_independently_verified"])
        self.assertFalse(r["noaa_ex_ante_vintages_verified"])
        self.assertFalse(r["market_consensus_pre_event_verified"])
        self.assertFalse(r["investment_edge_verified"])
        self.assertFalse(r["trade_eligible"])

    def test_earlier_frozen_forecast_remains_unmodified(self):
        f=json.loads(FROZEN.read_text(encoding="utf-8"))
        self.assertEqual(f["forecast_net_change_bcf"],61)
        self.assertIsNone(f["actual_next_release_net_change_bcf"])
        self.assertIsNone(f["source_raw_sha256"])
        self.assertFalse(f["source_raw_bytes_verified"])
        self.assertFalse(f["independent_pit_certified"])
        self.assertFalse(f["trade_eligible"])
        self.assertEqual(f["release_scheduled_utc"],"2026-11-19T15:30:00Z")

if __name__=="__main__":
    unittest.main()

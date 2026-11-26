"""Offline acquisition gate using synthetic EIA fixtures. NEVER a real outcome."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research_core.k5.eia_dec03_capture import capture
from research_core.k5.tests.test_forward_event_score import synthetic_bytes

PRE = "2026-12-03T15:29:59Z"
AFTER = "2026-12-03T15:35:00Z"


def src():
    return {"requested_url":"https://ir.eia.gov/ngs/wngsr.json",
            "response_host":"ir.eia.gov",
            "response_path":"/secure/ngs/wngsr.json",
            "capture_started_utc":"2026-12-03T15:32:00Z",
            "capture_finished_utc":"2026-12-03T15:32:01Z"}


class Dec03CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = synthetic_bytes()

    def run_capture(self, raw=None, metadata=None, now=AFTER):
        return capture(self.root, fetcher=lambda: (
            self.raw if raw is None else raw,
            src() if metadata is None else metadata),
            clock=lambda:now)

    def test_before_release_does_not_call_network_or_make_dir(self):
        marker = [False]
        def net():
            marker[0] = True
            raise RuntimeError("DO_NOT_FETCH")
        out = self.root / "not-created"
        x = capture(out, fetcher=net, clock=lambda:PRE)
        self.assertEqual(x["status"],"BLOCKED_RELEASE_NOT_YET_DUE")
        self.assertFalse(marker[0])
        self.assertFalse(out.exists())

    def test_synthetic_raw_receipt_score_triplet_created(self):
        x=self.run_capture()
        self.assertEqual(x["status"],"OFFICIAL_RAW_AND_SCORE_CAPTURED")
        self.assertEqual(x["actual_net_change_bcf"],-30)
        self.assertEqual(x["absolute_error_bcf"],6)
        self.assertFalse(x["trade_eligible"])
        receipt=json.loads((self.root/x["receipt_file"]).read_text())
        self.assertFalse(receipt["first_published_pit_authenticated"])
        score=json.loads((self.root/x["score_file"]).read_text())
        self.assertIsNone(score["market_consensus_bcf"])
        self.assertEqual((self.root/x["raw_file"]).read_bytes(),self.raw)

    def test_duplicate_files_preserved(self):
        first=self.run_capture()
        old=(self.root/first["raw_file"]).read_bytes()
        second=self.run_capture()
        self.assertEqual(second["status"],"BLOCKED_EIA_RESULT_NOT_VALIDATED")
        self.assertEqual((self.root/first["raw_file"]).read_bytes(),old)

    def test_stale_week_rejected_without_creating_files(self):
        old=json.loads(self.raw)
        old["current_week"]="2026-11-20"
        x=self.run_capture(raw=json.dumps(old).encode())
        self.assertEqual(x["status"],"BLOCKED_EIA_RESULT_NOT_VALIDATED")
        self.assertEqual(list(self.root.iterdir()),[])

    def test_untrusted_redirect_rejected(self):
        m=src();m["response_host"]="bad.eia.example"
        x=self.run_capture(metadata=m)
        self.assertEqual(x["status"],"BLOCKED_EIA_RESULT_NOT_VALIDATED")
        self.assertFalse(list(self.root.iterdir()))

    def test_impossible_early_receipt_rejected(self):
        m=src();m["capture_started_utc"]=PRE
        x=self.run_capture(metadata=m)
        self.assertEqual(x["status"],"BLOCKED_EIA_RESULT_NOT_VALIDATED")
        self.assertFalse(list(self.root.iterdir()))


if __name__=="__main__":unittest.main()

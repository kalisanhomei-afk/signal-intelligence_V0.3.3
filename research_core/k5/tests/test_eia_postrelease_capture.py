"""K5.2 post-release workflow tests; November 19 report here is SYNTHETIC only."""
import hashlib,json
from pathlib import Path
import tempfile,unittest

from research_core.k5.eia_postrelease_capture import capture
from research_core.k5.official_event_score import FIRST,evaluate_with_receipt

def future_raw():
    data=json.loads(FIRST.read_bytes().decode("utf-8-sig"))
    data["release_date"]="2026-Nov-19 00:00:00"
    data["current_week"]="2026-11-13"
    data["week_ago"]="2026-11-06"
    data["year_ago"]="2025-11-13"
    s=next(x for x in data["series"] if x["series_id"]=="png.nw2_epg0_swo_r48_bcf.w")
    s["data"]=[["2026-11-13",3890],["2026-11-06",3862],["2025-11-13",3920]]
    s["calculated"]["net_change"]=28
    s["calculated"]["implied_flow"]=28
    return json.dumps(data,separators=(",",":"),ensure_ascii=True).encode()

def source():
    return {"requested_url":"https://ir.eia.gov/ngs/wngsr.json",
            "response_host":"ir.eia.gov","response_path":"/secure/ngs/wngsr.json",
            "capture_started_utc":"2026-11-19T15:31:00Z",
            "capture_finished_utc":"2026-11-19T15:31:01Z"}

def clock():
    return "2026-11-19T15:31:02Z"

class PostReleaseK52Tests(unittest.TestCase):
    def test_pre_release_never_contacts_eia(self):
        def forbidden():
            raise AssertionError("NETWORK_MUST_NOT_BE_CALLED")
        with tempfile.TemporaryDirectory() as d:
            r=capture(d,forbidden,clock=lambda:"2026-11-17T03:00:00Z")
            self.assertEqual(r["status"],"BLOCKED_EIA_RELEASE_NOT_YET_DUE")
            self.assertEqual(list(Path(d).glob("*")),[])

    def test_mock_future_official_capture_scores_and_preserves_bytes(self):
        b=future_raw()
        with tempfile.TemporaryDirectory() as d:
            r=capture(d,lambda:(b,source()),clock)
            self.assertEqual(r["status"],"OFFICIAL_ORIGINAL_SOURCE_AND_V0_EVALUATION_CAPTURED")
            self.assertEqual(r["actual_change_bcf"],28)
            self.assertEqual(r["v0_absolute_error_bcf"],33)
            self.assertEqual(Path(d,r["raw_file"]).read_bytes(),b)
            self.assertEqual(r["source_raw_sha256"],hashlib.sha256(b).hexdigest())
            receipt=json.loads(Path(d,r["receipt_file"]).read_text())
            score=json.loads(Path(d,r["score_file"]).read_text())
            self.assertEqual(score,evaluate_with_receipt(b,receipt))
            self.assertFalse(score["trade_eligible"])
            self.assertFalse(score["consensus_vintage_verified"])

    def test_real_prior_report_cannot_masquerade_as_future(self):
        with tempfile.TemporaryDirectory() as d:
            r=capture(d,lambda:(FIRST.read_bytes(),source()),clock)
            self.assertEqual(r["status"],"BLOCKED_EIA_REPORT_NOT_VALIDATED")
            self.assertEqual(r["reason"],"WRONG_EIA_EVENT_WEEK")
            self.assertEqual(list(Path(d).glob("*")),[])

    def test_provenance_source_request_before_release_rejected(self):
        m=source();m["capture_started_utc"]="2026-11-19T15:29:59Z"
        with tempfile.TemporaryDirectory() as d:
            r=capture(d,lambda:(future_raw(),m),clock)
            self.assertEqual(r["status"],"BLOCKED_EIA_REPORT_NOT_VALIDATED")
            self.assertEqual(r["reason"],"EVENT_CAPTURE_BEFORE_RELEASE")

    def test_never_overwrites_a_first_source_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            a=capture(d,lambda:(future_raw(),source()),clock)
            b=capture(d,lambda:(future_raw(),source()),clock)
            self.assertTrue(a["status"].startswith("OFFICIAL_"))
            self.assertEqual(b["status"],"BLOCKED_EIA_REPORT_NOT_VALIDATED")
            self.assertEqual(b["reason"],"EVIDENCE_COLLISION_NO_OVERWRITE")
            self.assertEqual(len(list(Path(d).glob("*"))),3)

    def test_forged_receipt_hash_cannot_get_a_score(self):
        raw=future_raw()
        rec={
            "schema":"signal-k52-post-eia-original-evidence-v1",
            "event_id":"EIA-WNGSR-2026-11-19",
            "target_week_end":"2026-11-13",
            "source_raw_sha256":"a"*64,"source_raw_bytes":len(raw),
            "capture":source(),
            "first_published_pit_authenticated":False,
            "trade_eligible":False}
        with self.assertRaisesRegex(ValueError,"POSTRELEASE_RAW_BYTE_SHA_MISMATCH"):
            evaluate_with_receipt(raw,rec)

if __name__=="__main__":
    unittest.main()

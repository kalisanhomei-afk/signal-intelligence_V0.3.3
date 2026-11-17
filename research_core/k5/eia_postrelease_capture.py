"""One-shot post-release EIA Nov19 official raw acquisition and fixed V0 evaluation.

Will not fetch before 2026-11-19T15:30Z. Stale/wrong-week pages create NO
official result. Saves exact original bytes and a SHA-bound receipt; no trades.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from research_core.k5.official_event_score import (
    RELEASE,WEEK,MAX_BYTES, parse_utc, official_parsed, evaluate_with_receipt
)

URL="https://ir.eia.gov/ngs/wngsr.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def fetch():
    started=utc_now()
    with urlopen(Request(URL,headers={"User-Agent":"SIGNAL-K52-EIA-PostEvent-Evidence/1.0"}),timeout=16) as r:
        dest=urlsplit(r.geturl())
        if dest.scheme!="https" or dest.hostname!="ir.eia.gov" or dest.path not in (
            "/ngs/wngsr.json","/secure/ngs/wngsr.json"):
            raise ValueError("UNTRUSTED_EIA_REDIRECT")
        raw=r.read(MAX_BYTES+1)
        return raw,{
            "requested_url":URL,"response_host":dest.hostname,
            "response_path":dest.path,
            "capture_started_utc":started,
            "capture_finished_utc":utc_now()
        }

def capture(output_dir,fetcher=fetch,clock=utc_now):
    if parse_utc(clock())<parse_utc(RELEASE):
        return {"status":"BLOCKED_EIA_RELEASE_NOT_YET_DUE",
                "source_raw_sha256":None,"trade_eligible":False}
    try:
        raw,src=fetcher()
        if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:
            raise ValueError("INVALID_EIA_BYTES")
        if not (parse_utc(RELEASE)<=parse_utc(src["capture_started_utc"])
                <=parse_utc(src["capture_finished_utc"])):
            raise ValueError("EVENT_CAPTURE_BEFORE_RELEASE")
        # First verify the *actual response body*, not a form or source claim.
        official_parsed(raw)
        sha=hashlib.sha256(raw).hexdigest()
        receipt={
            "schema":"signal-k52-post-eia-original-evidence-v1",
            "event_id":"EIA-WNGSR-2026-11-19",
            "target_week_end":WEEK,
            "source_raw_sha256":sha,
            "source_raw_bytes":len(raw),
            "capture":src,
            "first_published_pit_authenticated":False,
            "trade_eligible":False
        }
        score=evaluate_with_receipt(raw,receipt)
        root=Path(output_dir)
        root.mkdir(parents=True,exist_ok=True)
        stem=f"EIA_WNGSR_20261119_{sha[:16]}"
        outputs={
            "raw":root/(stem+"_original.json"),
            "receipt":root/(stem+"_receipt.json"),
            "score":root/(stem+"_v0_score.json")
        }
        if any(p.exists() for p in outputs.values()):
            raise ValueError("EVIDENCE_COLLISION_NO_OVERWRITE")
        # All files are opened EXCLUSIVELY. A second runner may pass the
        # existence pre-check concurrently; never overwrite its evidence.
        owned=[]
        try:
            with outputs["raw"].open("xb") as f:
                owned.append(outputs["raw"])
                f.write(raw)
            for key,obj in (("receipt",receipt),("score",score)):
                with outputs[key].open("x",encoding="utf-8") as f:
                    owned.append(outputs[key])
                    json.dump(obj,f,indent=2,ensure_ascii=False)
                    f.write("\n")
        except BaseException:
            # Remove only files created by THIS attempt, not an archive
            # committed concurrently by another task.
            for p in reversed(owned):
                p.unlink(missing_ok=True)
            raise
        return {"status":"OFFICIAL_ORIGINAL_SOURCE_AND_V0_EVALUATION_CAPTURED",
                "raw_file":outputs["raw"].name,
                "receipt_file":outputs["receipt"].name,
                "score_file":outputs["score"].name,
                "source_raw_sha256":sha,
                "actual_change_bcf":score["actual_net_change_bcf"],
                "v0_absolute_error_bcf":score["v0_absolute_error_bcf"],
                "trade_eligible":False}
    except (ValueError,HTTPError,URLError,TimeoutError,OSError,UnicodeError) as exc:
        return {"status":"BLOCKED_EIA_REPORT_NOT_VALIDATED",
                "error_type":type(exc).__name__,
                "reason":str(exc)[:100] if isinstance(exc,ValueError) else None,
                "source_raw_sha256":None,"trade_eligible":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args()
    result=capture(a.output_dir)
    print(json.dumps(result,ensure_ascii=False))
    if not result["status"].startswith("OFFICIAL_"):
        raise SystemExit(2)
if __name__=="__main__":main()

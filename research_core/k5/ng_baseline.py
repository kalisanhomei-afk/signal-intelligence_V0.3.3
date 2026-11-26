"""K5: 2026-11-19 EIA WNGSR prior-week persistence benchmark. Research only."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path

SCHEMA="signal-k5-ng-weekly-persistence-input-v1"
RULE="PREVIOUS_RELEASE_WEEKLY_NET_CHANGE_UNCHANGED"
SCHEDULE="2026-11-19T15:30:00Z"
REQUIRED={"schema","hypothesis_id","event_id","event_scheduled_utc",
          "target_week_end","target","target_unit","model_id","source_url",
          "source_report_release_utc_claim","source_report_week_end",
          "source_raw_sha256","source_raw_bytes_verified",
          "prior_lower48_storage_bcf","prior_prior_lower48_storage_bcf",
          "source_reported_net_change_bcf","source_five_year_avg_stocks_bcf",
          "source_year_ago_stocks_bcf","point_forecast_is_trade_signal"}

def parse_utc(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    try:
        dt=datetime.fromisoformat(value[:-1]+"+00:00")
    except ValueError as exc:
        raise ValueError("UTC_INVALID") from exc
    if dt.utcoffset()!=timedelta(0):
        raise ValueError("UTC_INVALID")
    return dt

def compute(x):
    if not isinstance(x,dict) or set(x)!=REQUIRED:
        raise ValueError("CONTRACT_KEYS_MISMATCH")
    if (x["schema"]!=SCHEMA or x["hypothesis_id"]!="H-NG-001" or
        x["event_id"]!="EIA-WNGSR-2026-11-19" or
        x["event_scheduled_utc"]!=SCHEDULE or
        x["target_week_end"]!="2026-11-13" or
        x["target"]!="US_LOWER48_WORKING_GAS_WEEKLY_NET_CHANGE" or
        x["target_unit"]!="Bcf" or x["model_id"]!=RULE or
        x["source_url"]!="https://ir.eia.gov/ngs/wngsr.json" or
        x["source_report_week_end"]!="2026-11-06" or
        x["source_raw_bytes_verified"] is not False or
        x["source_raw_sha256"] is not None or
        x["point_forecast_is_trade_signal"] is not False):
        raise ValueError("MODEL_OR_PROVENANCE_MISMATCH")
    if not parse_utc(x["source_report_release_utc_claim"])<parse_utc(SCHEDULE):
        raise ValueError("LOOKAHEAD_RELEASE")
    for key in ("prior_lower48_storage_bcf","prior_prior_lower48_storage_bcf",
                "source_reported_net_change_bcf","source_five_year_avg_stocks_bcf",
                "source_year_ago_stocks_bcf"):
        if type(x[key]) is not int or x[key]<-500 or x[key]>100000:
            raise ValueError("INVALID_NUMBER")
    latest=x["prior_lower48_storage_bcf"]
    older=x["prior_prior_lower48_storage_bcf"]
    delta=x["source_reported_net_change_bcf"]
    if latest<=0 or older<=0 or delta!=latest-older:
        raise ValueError("STORAGE_FLOW_MISMATCH")
    if (latest!=3862 or older!=3801 or delta!=61 or
        x["source_five_year_avg_stocks_bcf"]!=3787 or
        x["source_year_ago_stocks_bcf"]!=3954):
        raise ValueError("OFFICIAL_SOURCE_SNAPSHOT_MISMATCH")
    return {
        "schema":"signal-k5-ng-weekly-pre-registered-forecast-v1",
        "hypothesis_id":x["hypothesis_id"],"event_id":x["event_id"],
        "release_scheduled_utc":x["event_scheduled_utc"],
        "target_week_end":x["target_week_end"],
        "target":x["target"],"unit":x["target_unit"],
        "method_id":RULE,"forecast_net_change_bcf":delta,
        "baseline_storage_asof_2026_11_06_bcf":latest,
        "baseline_storage_5yr_comparison_bcf":x["source_five_year_avg_stocks_bcf"],
        "baseline_vs_5yr_stocks_bcf":latest-x["source_five_year_avg_stocks_bcf"],
        "source_url":x["source_url"],
        "source_release_utc_claim":x["source_report_release_utc_claim"],
        "source_raw_sha256":None,"source_raw_bytes_verified":False,
        "market_consensus_bcf":None,"noaa_forecast_vintage_verified":False,
        "actual_next_release_net_change_bcf":None,
        "status":"FROZEN_PERSISTENCE_BENCHMARK_ONLY_NOT_PREDICTIVE_MODEL",
        "independent_pit_certified":False,"trade_eligible":False
    }

def score(forecast,outcome):
    if (forecast["schema"]!="signal-k5-ng-weekly-pre-registered-forecast-v1" or
        forecast["trade_eligible"] is not False):
        raise ValueError("UNRECOGNIZED_FROZEN_FORECAST")
    expected={"event_id","actual_net_change_bcf","source_raw_sha256","source_capture_utc"}
    if not isinstance(outcome,dict) or set(outcome)!=expected:
        raise ValueError("OUTCOME_CONTRACT_KEYS_MISMATCH")
    if outcome["event_id"]!=forecast["event_id"]:
        raise ValueError("EVENT_MISMATCH")
    if any(outcome[k] is None for k in expected-{"event_id"}):
        return {"status":"WAITING_FOR_REAL_POST_RELEASE_EIA_OUTCOME",
                "absolute_error_bcf":None,"trade_eligible":False}
    value=outcome["actual_net_change_bcf"]
    if type(value) not in (int,float) or not -1000<=value<=1000:
        raise ValueError("INVALID_OFFICIAL_VALUE")
    sha=outcome["source_raw_sha256"]
    if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("INVALID_ORIGINAL_BYTES_SHA")
    if parse_utc(outcome["source_capture_utc"])<parse_utc(forecast["release_scheduled_utc"]):
        raise ValueError("OUTCOME_PRECEDES_SCHEDULED_RELEASE")
    return {"status":"DESCRIPTIVE_ONE_EVENT_SCORE_NOT_INDEPENDENT_PIT_CERTIFIED",
            "absolute_error_bcf":abs(value-forecast["forecast_net_change_bcf"]),
            "actual_net_change_bcf":value,
            "independent_pit_certified":False,"trade_eligible":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=compute(json.loads(a.case.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"forecast_bcf":result["forecast_net_change_bcf"],
                      "status":result["status"],"trade_eligible":False}))
if __name__=="__main__":main()

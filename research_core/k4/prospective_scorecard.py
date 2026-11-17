"""K4.10 baseline performance reference and prospective frozen forecast-vs-consensus score.

Reads only committed official historical WASDE outcome labels and a frozen forecast.
No historical predictor features, API calls, model tuning or trading capability.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from research_core.k4.nine_year_revision_catalog import OLDER, NEWER, combine
from research_core.k4.fgis_weekly_vintage import timestamp

ROOT=Path(__file__).resolve().parent
FROZEN=ROOT/"cases"/"2026-12-10-forward-baseline-forecast.json"
CONTRACT=ROOT/"cases"/"2026-12-10-v0-scoring-contract.json"
EMPTY_EVIDENCE=ROOT/"cases"/"2026-12-10-v0-scoring-evidence-empty.json"
SCHEMA="signal-k410-dec2026-baseline-scoring-contract-v1"
EVIDENCE_SCHEMA="signal-k410-dec2026-evaluation-evidence-v1"
EVENT="USDA-WASDE-2026-12-10"
TARGET="US_CORN_2026_27_ENDING_STOCKS_MBU"
SCHEDULE="2026-12-10T17:00:00Z"
MODEL="USDA_PREVIOUS_WASDE_PERSISTENCE_V0"
RULE="ABSOLUTE_ERROR_MILLION_BUSHELS_LOWER_BETTER"
REQUIRED_EVIDENCE={
    "consensus_value_mbu","consensus_provider","consensus_methodology",
    "consensus_source_url","consensus_publication_utc","consensus_capture_utc",
    "consensus_raw_sha256","official_value_mbu","official_source_url",
    "official_capture_utc","official_raw_sha256",
}

def decimal_value(value):
    if isinstance(value,bool) or type(value) not in (int,float,str):
        raise ValueError("INVALID_QUANTITY")
    try:
        d=Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("INVALID_QUANTITY") from exc
    if not d.is_finite() or d<0 or d>100_000:
        raise ValueError("INVALID_QUANTITY")
    return d

def displayed(d):
    return str(d.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))

def validate_sha(x):
    if not isinstance(x,str) or len(x)!=64 or any(c not in "0123456789abcdef" for c in x):
        raise ValueError("INVALID_SOURCE_SHA256")

def https_source(x,official=False):
    if not isinstance(x,str):
        raise ValueError("SOURCE_URL_REQUIRED")
    u=urlsplit(x)
    if u.scheme!="https" or not u.hostname or u.username or u.password:
        raise ValueError("SOURCE_URL_REQUIRED")
    if official and u.hostname not in ("www.usda.gov","usda.azureedge.us","esmis.nal.usda.gov"):
        raise ValueError("UNRECOGNIZED_OFFICIAL_USDA_HOST")

def historical_baseline():
    old=json.loads(OLDER.read_text(encoding="utf-8"))
    new=json.loads(NEWER.read_text(encoding="utf-8"))
    catalog=combine(old,new)
    rows=catalog["observations"]
    errors=[Decimal(r["delta_ending_stocks_mbu"]) for r in rows]
    n=len(errors)
    if n!=9:
        raise ValueError("HISTORY_SCOPE_MISMATCH")
    err_abs=sorted(abs(x) for x in errors)
    mae=sum(err_abs)/n
    mse=sum(x*x for x in errors)/n
    return {
        "schema":"signal-k410-nine-year-persistence-benchmark-v1",
        "status":"HISTORICAL_OUTCOME_LABEL_REFERENCE_ONLY",
        "label_years":n,
        "years":catalog["years_complete"],
        "target_unit":"million_bushels",
        "baseline":"USDA_NOVEMBER_ESTIMATE_UNCHANGED_TO_DECEMBER",
        "absolute_error_mae_mbu":displayed(mae),
        "median_absolute_error_mbu":displayed(err_abs[n//2]),
        "root_mean_squared_error_mbu":displayed(mse.sqrt()),
        "signed_error_actual_minus_forecast_mean_mbu":displayed(sum(errors)/n),
        "max_abs_error_mbu":displayed(err_abs[-1]),
        "no_change_years":sum(x==0 for x in errors),
        "revision_up_years":sum(x>0 for x in errors),
        "revision_down_years":sum(x<0 for x in errors),
        "sample_size_too_small_for_confidence_interval":True,
        "historical_predictors_pit_verified":False,
        "sample_out_of_time_validation_completed":False,
        "trading_edge_verified":False,
        "trade_eligible":False,
    }

def score(contract,evidence,forecast_bytes):
    if not isinstance(contract,dict) or set(contract)!={
        "schema","event_id","target","release_scheduled_utc","model_id",
        "forecast_value_mbu","forecast_raw_sha256","scoring_rule",
        "has_separately_frozen_v1","trade_eligible"
    }:
        raise ValueError("CONTRACT_KEYS_MISMATCH")
    if (contract["schema"]!=SCHEMA or contract["event_id"]!=EVENT or
        contract["target"]!=TARGET or contract["release_scheduled_utc"]!=SCHEDULE or
        contract["model_id"]!=MODEL or contract["scoring_rule"]!=RULE or
        contract["forecast_value_mbu"]!=1758 or
        contract["has_separately_frozen_v1"] is not False or
        contract["trade_eligible"] is not False):
        raise ValueError("FROZEN_CONTRACT_MISMATCH")
    validate_sha(contract["forecast_raw_sha256"])
    if hashlib.sha256(forecast_bytes).hexdigest()!=contract["forecast_raw_sha256"]:
        raise ValueError("FROZEN_FORECAST_BYTES_TAMPERED")
    locked=json.loads(forecast_bytes.decode("utf-8"))
    if (locked["forecast_value_mbu"]!=1758 or locked["event_id"]!=EVENT or
        locked["method_id"]!=MODEL or locked["target"]!=TARGET or
        locked["release_scheduled_utc"]!=SCHEDULE or locked["trade_eligible"] is not False):
        raise ValueError("FROZEN_FORECAST_SCHEMA_MISMATCH")
    if timestamp(locked["forecast_created_utc"])>=timestamp(SCHEDULE):
        raise ValueError("FORECAST_CREATED_AFTER_EVENT")
    if not isinstance(evidence,dict) or set(evidence)!=REQUIRED_EVIDENCE|{"schema","event_id"}:
        raise ValueError("EVIDENCE_CONTRACT_KEYS_MISMATCH")
    if evidence["schema"]!=EVIDENCE_SCHEMA or evidence["event_id"]!=EVENT:
        raise ValueError("EVIDENCE_EVENT_MISMATCH")
    missing=sorted(k for k in REQUIRED_EVIDENCE if evidence[k] is None)
    status="WAITING_FOR_DECEMBER_PRE_RELEASE_CONSENSUS_AND_USDA_OUTCOME"
    result={
        "schema":"signal-k410-dec2026-scoring-result-v1",
        "event_id":EVENT,
        "forecast_v0_mbu":"1758",
        "historical_reference":historical_baseline(),
        "scoring_rule":RULE,
        "evidence_complete":False,
        "missing_evidence":missing,
        "status":status,
        "consensus_forecast_mbu":None,
        "official_december_ending_stocks_mbu":None,
        "v0_abs_error_mbu":None,
        "consensus_abs_error_mbu":None,
        "v0_minus_consensus_abs_error_mbu":None,
        "model_v1_abs_error_mbu":None,
        "prospective_one_event_comparison_is_predictive_edge_proof":False,
        "independent_pit_source_certification":False,
        "trading_edge_verified":False,
        "trade_eligible":False,
    }
    if missing:
        return result
    for key in ("consensus_raw_sha256","official_raw_sha256"):
        validate_sha(evidence[key])
    https_source(evidence["consensus_source_url"])
    https_source(evidence["official_source_url"],official=True)
    for key in ("consensus_provider","consensus_methodology"):
        if not isinstance(evidence[key],str) or not evidence[key].strip():
            raise ValueError("MISSING_CONSENSUS_PROVENANCE")
    event=timestamp(SCHEDULE)
    pub=timestamp(evidence["consensus_publication_utc"])
    cap=timestamp(evidence["consensus_capture_utc"])
    official=timestamp(evidence["official_capture_utc"])
    if not pub<=cap<event:
        raise ValueError("CONSENSUS_NOT_PROVEN_CAPTURED_BEFORE_EVENT")
    if official<event:
        raise ValueError("OFFICIAL_OUTCOME_CAPTURED_BEFORE_EVENT")
    consensus=decimal_value(evidence["consensus_value_mbu"])
    outcome=decimal_value(evidence["official_value_mbu"])
    v0_error=abs(Decimal(1758)-outcome)
    con_error=abs(consensus-outcome)
    result.update({
        "status":"DESCRIPTIVE_SINGLE_EVENT_COMPARISON_REQUIRES_INDEPENDENT_PIT_REVIEW",
        "evidence_complete":True,
        "missing_evidence":[],
        "consensus_forecast_mbu":str(consensus),
        "official_december_ending_stocks_mbu":str(outcome),
        "v0_abs_error_mbu":displayed(v0_error),
        "consensus_abs_error_mbu":displayed(con_error),
        "v0_minus_consensus_abs_error_mbu":displayed(v0_error-con_error),
    })
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--contract",type=Path,default=CONTRACT)
    p.add_argument("--evidence",type=Path,default=EMPTY_EVIDENCE)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=score(json.loads(a.contract.read_text(encoding="utf-8")),
            json.loads(a.evidence.read_text(encoding="utf-8")), FROZEN.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"historical_MAE":r["historical_reference"]["absolute_error_mae_mbu"],
                      "comparison_ready":r["evidence_complete"],"trade_eligible":False}))

if __name__=="__main__":
    main()

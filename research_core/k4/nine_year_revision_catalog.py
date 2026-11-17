"""K4.7 reconcile nine years of as-reported USDA outcome labels, without PIT features."""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLDER=HERE/"cases"/"2017-2020-official-wasde-december-corn-revision-evidence.json"
NEWER=HERE/"cases"/"2021-2025-official-wasde-december-corn-revision-evidence.json"

def combine(older,newer):
    if older.get("schema")!="signal-k47-official-usda-2017-2020-outcome-label-evidence-v1":
        raise ValueError("OLDER_CONTRACT")
    if newer.get("schema")!="signal-k46-usda-as-reported-december-corn-revision-evidence-v1":
        raise ValueError("NEWER_CONTRACT")
    if older.get("archive_retrieved_after_all_historical_events") is not True or newer.get("observations_retrieved_after_the_events") is not True:
        raise ValueError("AS_REPORTED_PROVENANCE_MISSING")
    if older.get("historical_asof_features_authenticated") is not False or newer.get("prospective_fgis_feature_vintages_verified") is not False:
        raise ValueError("UNEXPECTED_PIT_PROMOTION")
    rows=older["rows"]+newer["observations"]
    expected=[f"{y}/{(y+1)%100:02d}" for y in range(2017,2026)]
    if len(rows)!=len(expected) or [x.get("marketing_year") for x in rows]!=expected:
        raise ValueError("YEAR_GAP_OR_DUPLICATE")
    result=[]
    for x in rows:
        y=x["marketing_year"]
        if x["nov_release_date"] >= x["dec_release_date"]:
            raise ValueError("INVALID_RELEASE_ORDER")
        e0,e1=(Decimal(str(x[k])) for k in ("nov_exports_mbu","dec_exports_mbu"))
        s0,s1=(Decimal(str(x[k])) for k in ("nov_ending_stocks_mbu","dec_ending_stocks_mbu"))
        de,ds=e1-e0,s1-s0
        if de!=Decimal(str(x["delta_exports_mbu"])) or ds!=Decimal(str(x["delta_ending_stocks_mbu"])):
            raise ValueError("REVISION_RECONCILIATION_FAILURE")
        if ds+de != Decimal(str(x["other_net_stock_change_mbu"])):
            raise ValueError("NON_EXPORT_BALANCE_RECONCILIATION_FAILURE")
        if e0<0 or e1<0 or s0<0 or s1<0:
            raise ValueError("NEGATIVE_OFFICIAL_LEVEL")
        result.append({"marketing_year":y,"delta_exports_mbu":str(de),
                       "delta_ending_stocks_mbu":str(ds),
                       "other_net_stock_change_mbu":str(ds+de),
                       "nov_release_date":x["nov_release_date"],
                       "dec_release_date":x["dec_release_date"]})
    return {
        "schema":"signal-k47-nine-year-usda-december-revision-catalog-v1",
        "status":"OUTCOME_LABEL_CATALOG_ONLY",
        "marketing_years":len(result),"years_complete":expected,
        "observations":result,
        "export_revision_nonzero_years":[r["marketing_year"] for r in result
                                          if Decimal(r["delta_exports_mbu"])!=0],
        "stocks_revision_nonzero_years":[r["marketing_year"] for r in result
                                          if Decimal(r["delta_ending_stocks_mbu"])!=0],
        "other_balance_nonzero_years":[r["marketing_year"] for r in result
                                          if Decimal(r["other_net_stock_change_mbu"])!=0],
        "source_sha_digests_in_input_evidence":True,
        "fgis_features_by_announcement_asof_available":False,
        "independent_historical_pit_certified":False,
        "model_calibrated":False,
        "out_of_sample_edge_verified":False,
        "formal_backtest_eligible":False,
        "trade_eligible":False
    }

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    o=json.loads(OLDER.read_text(encoding="utf-8"))
    n=json.loads(NEWER.read_text(encoding="utf-8"))
    r=combine(o,n)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"marketing_years":r["marketing_years"],
        "export_revision_nonzero_years":r["export_revision_nonzero_years"],
        "stocks_revision_nonzero_years":r["stocks_revision_nonzero_years"],
        "other_balance_nonzero_years":r["other_balance_nonzero_years"],
        "trade_eligible":False}))

if __name__=="__main__":main()

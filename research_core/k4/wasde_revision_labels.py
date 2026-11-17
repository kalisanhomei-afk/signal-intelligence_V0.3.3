"""Extract official USDA as-reported November/December US corn revision LABELS only."""
from __future__ import annotations
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
from research_core.k4.historical_source_probe import fetch, BASE

TITLE = "U.S. Feed Grain and Corn Supply and Use"
FIELDS = {"Exports", "Ending Stocks"}
NEEDED = {"ReportTitle", "Commodity", "Region", "MarketYear", "ProjEstFlag",
          "Attribute", "Value", "Unit", "ReleaseDate", "ForecastYear", "ForecastMonth"}

def extract_vintage(raw: bytes, year: int, month: int):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict")))
    if not reader.fieldnames or not NEEDED.issubset(reader.fieldnames):
        raise ValueError("MISSING_REQUIRED_CSV_COLUMNS")
    market_year = f"{year}/{(year+1)%100:02d}"
    selected = {}
    for r in reader:
        if (r["ReportTitle"] != TITLE or r["Commodity"] != "Corn" or
            r["Region"] != "United States" or r["MarketYear"] != market_year or
            r["ProjEstFlag"] != "Proj." or r["Unit"] != "Million Bushels" or
            r["Attribute"] not in FIELDS):
            continue
        if r["ForecastYear"] != str(year) or r["ForecastMonth"] != str(month):
            raise ValueError("FORECAST_VINTAGE_MISMATCH")
        when = date.fromisoformat(r["ReleaseDate"])
        if when.year != year or when.month != month:
            raise ValueError("RELEASE_DATE_VINTAGE_MISMATCH")
        try:
            val = Decimal(r["Value"])
        except InvalidOperation as exc:
            raise ValueError("INVALID_VALUE") from exc
        if not val.is_finite() or val < 0:
            raise ValueError("INVALID_VALUE")
        if r["Attribute"] in selected:
            raise ValueError("AMBIGUOUS_DUPLICATE_SERIES")
        selected[r["Attribute"]] = {"value_mbu":str(val),"release_date":str(when)}
    if set(selected) != FIELDS:
        raise ValueError("MISSING_OFFICIAL_US_CORN_CURRENT_YEAR_PROJECTION")
    if selected["Exports"]["release_date"] != selected["Ending Stocks"]["release_date"]:
        raise ValueError("MIXED_RELEASE_DATE")
    return selected

def pair(raw_nov: bytes, raw_dec: bytes, year: int, urls: dict):
    n = extract_vintage(raw_nov, year, 11)
    d = extract_vintage(raw_dec, year, 12)
    if d["Exports"]["release_date"] <= n["Exports"]["release_date"]:
        raise ValueError("RELEASE_ORDER")
    e0,e1 = (Decimal(n["Exports"]["value_mbu"]),Decimal(d["Exports"]["value_mbu"]))
    s0,s1 = (Decimal(n["Ending Stocks"]["value_mbu"]),Decimal(d["Ending Stocks"]["value_mbu"]))
    return {"marketing_year":f"{year}/{(year+1)%100:02d}",
            "nov_release_date":n["Exports"]["release_date"],
            "dec_release_date":d["Exports"]["release_date"],
            "nov_exports_mbu":str(e0),"dec_exports_mbu":str(e1),
            "delta_exports_mbu":str(e1-e0),
            "nov_ending_stocks_mbu":str(s0),"dec_ending_stocks_mbu":str(s1),
            "delta_ending_stocks_mbu":str(s1-s0),
            "other_net_stock_change_mbu":str((s1-s0)+(e1-e0)),
            "raw_urls":urls,
            "raw_sha256":{"nov":hashlib.sha256(raw_nov).hexdigest(),
                          "dec":hashlib.sha256(raw_dec).hexdigest()},
            "as_reported_label_retrieved_after_release":True,
            "independent_pit_features_verified":False}

def build(years):
    if not years or len(years)>15 or any(not 2011<=y<=2025 for y in years):
        raise ValueError("OUTSIDE_FIXED_HISTORY_RANGE")
    result = {"schema":"signal-k46-as-published-december-corn-revision-labels-v1",
              "source":"USDA_OCE_HISTORICAL_WASDE_AS_REPORTED",
              "status":"OUTCOME_LABELS_ONLY",
              "rows":[],"gaps":[],"predictor_features":[],
              "historical_pit_features_verified":False,
              "ready_for_backtest":False,"independent_edge_verified":False,
              "trade_eligible":False}
    for year in years:
        urls = {k:f"{BASE}{year}-{k}.csv" for k in ("11","12")}
        try:
            raw_nov,actual_nov=fetch(urls["11"])
            raw_dec,actual_dec=fetch(urls["12"])
            result["rows"].append(pair(raw_nov,raw_dec,year,{"nov":actual_nov,"dec":actual_dec}))
        except Exception as exc:
            result["gaps"].append({"marketing_year":f"{year}/{(year+1)%100:02d}",
                                   "error_type":type(exc).__name__,
                                   "status":"SOURCE_OR_SCHEMA_UNVERIFIED"})
    result["label_pairs_count"]=len(result["rows"])
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--start-year",type=int,default=2017)
    p.add_argument("--end-year",type=int,default=2025)
    a=p.parse_args()
    data=build(list(range(a.start_year,a.end_year+1)))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":data["status"],
                      "label_pairs_count":len(data["rows"]),"gaps":data["gaps"],
                      "revisions":[{k:r[k] for k in ("marketing_year","delta_exports_mbu","delta_ending_stocks_mbu")}
                                   for r in data["rows"]],
                      "ready_for_backtest":False}))

if __name__=="__main__":
    main()

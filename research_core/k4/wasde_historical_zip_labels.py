"""Extract 2017–2020 Nov/Dec corn outcome labels from USDA official history ZIP.

Single stream pass over one archived CSV. Research-only outcome labels; NOT ex-ante model features.
"""
from __future__ import annotations
import argparse
import csv
from datetime import date, datetime
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
from research_core.k4.wasde_revision_labels import TITLE, pair
from research_core.k4.historical_source_probe import fetch

URL = "https://usda.azureedge.us/sites/default/files/documents/oce-wasde-report-data-2016-01-to-2020-12.zip"
MEMBER = "oce-wasde-report-data-2016-01-to-2020-12.csv"
YEARS = (2017, 2018, 2019, 2020)
TARGET_FIELDS = ("Exports", "Ending Stocks")
EXPECTED_SCHEMA = {
    "ReportTitle","Commodity","Region","MarketYear","ProjEstFlag","Attribute",
    "Value","Unit","ReleaseDate","ForecastYear","ForecastMonth"
}

def extract_archived(raw_zip: bytes):
    zip_sha256 = hashlib.sha256(raw_zip).hexdigest()
    with ZipFile(io.BytesIO(raw_zip)) as z:
        entries=z.infolist()
        if len(entries)!=1 or entries[0].filename!=MEMBER or entries[0].file_size>75_000_000:
            raise ValueError("UNEXPECTED_ZIP_CONTENTS")
        with z.open(MEMBER) as f:
            # Read bounded uncompressed file for SHA and normalized strict UTF-8 parsing.
            raw_csv=f.read(75_000_001)
    if len(raw_csv)>75_000_000:
        raise ValueError("CSV_TOO_LARGE")
    csv_sha256=hashlib.sha256(raw_csv).hexdigest()
    reader=csv.DictReader(io.StringIO(raw_csv.decode("utf-8-sig",errors="strict")))
    if not reader.fieldnames or not EXPECTED_SCHEMA.issubset(reader.fieldnames):
        raise ValueError("UNRECOGNIZED_ARCHIVE_SCHEMA")
    buckets={(y,m):[] for y in YEARS for m in (11,12)}
    for row in reader:
        if row["ReportTitle"] != TITLE or row["Commodity"] != "Corn" or row["Region"] != "United States":
            continue
        if row["ProjEstFlag"]!="Proj." or row["Unit"]!="Million Bushels":
            continue
        if row["Attribute"] not in TARGET_FIELDS:
            continue
        try:
            y=int(row["ForecastYear"]);m=int(row["ForecastMonth"])
        except (ValueError,TypeError):
            continue
        if (y,m) not in buckets:continue
        expected_year=f"{y}/{(y+1)%100:02d}"
        if row["MarketYear"] != expected_year:continue
        buckets[(y,m)].append(row)

    def single_month(year,month):
        out=io.StringIO(newline="")
        writer=csv.DictWriter(out,fieldnames=reader.fieldnames,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(buckets[(year,month)])
        return out.getvalue().encode("utf-8")

    result={"schema":"signal-k47-usda-archive-corn-revision-labels-v1",
            "status":"OUTCOME_LABELS_ONLY","source_url":URL,
            "downloaded_zip_sha256":zip_sha256,"archived_csv_sha256":csv_sha256,
            "archived_csv_member":MEMBER,
            "raw_zip_bytes_republished":False,
            "independent_pit_features_verified":False,
            "calibrated_model_ready":False,"trade_eligible":False,
            "rows":[],"gaps":[]}
    for year in YEARS:
        try:
            n=single_month(year,11)
            d=single_month(year,12)
            rec=pair(n,d,year,{"nov":URL+"#"+MEMBER,"dec":URL+"#"+MEMBER})
            # pair hashes identify generated filtered subsets, not the official 2016-2020 archive.
            rec["selected_rows_sha256"]=rec.pop("raw_sha256")
            rec["source_zip_sha256"]=zip_sha256
            rec["source_csv_sha256"]=csv_sha256
            rec["selected_rows_nov"]=len(buckets[(year,11)])
            rec["selected_rows_dec"]=len(buckets[(year,12)])
            result["rows"].append(rec)
        except (ValueError,KeyError) as exc:
            result["gaps"].append({"marketing_year":f"{year}/{(year+1)%100:02d}",
                                   "status":"SCHEMA_OR_SERIES_UNVERIFIED","error_type":type(exc).__name__,
                                   "detail":str(exc)[:100]})
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    raw,_=fetch(URL,limit=4_000_000)
    r=extract_archived(raw)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("K47_ARCHIVE_LABELS",json.dumps({
        "zip_sha256":r["downloaded_zip_sha256"],"csv_sha256":r["archived_csv_sha256"],
        "rows":[{k:x[k] for k in ("marketing_year","nov_exports_mbu","dec_exports_mbu",
                                 "delta_exports_mbu","nov_ending_stocks_mbu",
                                 "dec_ending_stocks_mbu","delta_ending_stocks_mbu",
                                 "selected_rows_nov","selected_rows_dec")} for x in r["rows"]],
        "gaps":r["gaps"],"trade_eligible":False}))

if __name__=="__main__":main()

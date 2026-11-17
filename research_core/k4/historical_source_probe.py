"""Read-only fixed-source historical data probe. No API key, no market quotes, no PIT claims."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlsplit

BASE = "https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-"
WASDE = {f"{y}-{m}": f"{BASE}{y}-{m}.csv" for y in (2024, 2025) for m in ("11", "12")}
FGIS = "https://agtransport.usda.gov/resource/sruw-w49i.json?%24limit=2"
ALLOWED = {"www.usda.gov", "usda.azureedge.us", "agtransport.usda.gov"}

def fetch(url: str, limit: int = 2_500_000):
    if urlsplit(url).hostname not in ALLOWED or urlsplit(url).scheme != "https":
        raise ValueError("SOURCE_NOT_ALLOWLISTED")
    with urlopen(Request(url, headers={"User-Agent": "SIGNAL-K46-Research-Source-Probe/1.0"}), timeout=16) as r:
        actual = r.geturl()
        if urlsplit(actual).hostname not in ALLOWED or urlsplit(actual).scheme != "https":
            raise ValueError("UNEXPECTED_SOURCE_REDIRECT")
        raw = r.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("EXCESSIVE_SOURCE_BYTES")
        return raw, actual

def assess_wasde(raw: bytes, actual: str):
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict")))
    cols = rows.fieldnames or []
    if not cols:
        raise ValueError("NO_CSV_COLUMNS")
    examples, target_examples, total = [], [], 0
    for x in rows:
        total += 1
        if (str(x.get("Commodity", "")).strip().lower() == "corn"
            and str(x.get("Attribute", "")).strip().lower() in ("exports", "ending stocks")
            and len(examples) < 10):
            examples.append({k: str(x.get(k, ""))[:90] for k in
                ("ReportTitle","Commodity","Region","MarketYear","ProjEstFlag",
                 "Attribute","Value","Unit","ReleaseDate","ForecastYear","ForecastMonth")})
        if (str(x.get("Commodity", "")).strip() == "Corn"
            and str(x.get("Region", "")).strip() == "United States"
            and str(x.get("MarketYear", "")).strip() in ("2024/25","2025/26")
            and str(x.get("Attribute", "")).strip() in ("Exports","Ending Stocks")
            and str(x.get("Unit", "")).strip() == "Million Bushels"
            and len(target_examples) < 20):
            target_examples.append({k: str(x.get(k, ""))[:90] for k in
                ("ReportTitle","Commodity","Region","MarketYear","ProjEstFlag",
                 "Attribute","Value","Unit","ReleaseDate","ForecastYear","ForecastMonth")})
    return {"source_url":actual,"sha256":hashlib.sha256(raw).hexdigest(),
            "bytes":len(raw),"columns":cols,"rows":total,"corn_rows_sample":examples,
            "us_corn_supply_rows_sample":target_examples,
            "status":"RETRIEVED_SCHEMA_ONLY_NOT_PIT_CERTIFIED"}

def probe():
    result = {"schema":"signal-k46-history-source-probe-v1","sources":{},
              "market_data_purchased":False,"pit_certified":False,"trade_eligible":False}
    for date, url in WASDE.items():
        try:
            raw, actual = fetch(url)
            result["sources"][date] = assess_wasde(raw, actual)
        except Exception as exc:
            result["sources"][date] = {"source_url":url,"status":"SOURCE_UNAVAILABLE",
                                       "error_type":type(exc).__name__}
    try:
        raw, actual = fetch(FGIS, limit=350_000)
        sample = json.loads(raw)
        if not isinstance(sample,list): raise ValueError("UNEXPECTED_FGIS_SHAPE")
        result["fgis_api"] = {"url":actual,"status":"DATASET_ENDPOINT_FOUND_NOT_VINTAGE_CERTIFIED",
                              "sample_size":len(sample),"columns":sorted({k for r in sample for k in r}),
                              "sample":sample[:1]}
    except Exception as exc:
        result["fgis_api"] = {"url":FGIS,"status":"SOURCE_UNAVAILABLE",
                              "error_type":type(exc).__name__}
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args = p.parse_args()
    r = probe()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"statuses":{k:v["status"] for k,v in r["sources"].items()},
                      "fgis_status":r["fgis_api"]["status"],"pit_certified":False}))
    for key in ("2024-11","2024-12","2025-11","2025-12"):
        item=r["sources"][key]
        if item["status"].startswith("RETRIEVED"):
            print("K46_WASDE_SAMPLE",json.dumps({"file":key,"columns":item["columns"],"rows":item["rows"],
                                                "corn_samples":item["corn_rows_sample"][:1],
                                                "target_rows":item["us_corn_supply_rows_sample"]}))
    item=r["fgis_api"]
    if item["status"]=="DATASET_ENDPOINT_FOUND_NOT_VINTAGE_CERTIFIED":
        print("K46_FGIS_SCHEMA",json.dumps({"columns":item["columns"],"sample":item["sample"][:1]}))

if __name__ == "__main__":
    main()

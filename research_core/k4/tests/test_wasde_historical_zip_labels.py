"""K4.7 archived official vintages: deterministic archive handling, no PIT promotion."""
from __future__ import annotations
import csv,io,json,unittest,zipfile
from research_core.k4.wasde_historical_zip_labels import extract_archived,MEMBER,YEARS

FIELDS=["WasdeNumber","ReportDate","ReportTitle","Attribute","ReliabilityProjection","Commodity",
        "Region","MarketYear","ProjEstFlag","AnnualQuarterFlag","Value","Unit",
        "ReleaseDate","ReleaseTime","ForecastYear","ForecastMonth"]

def archive(rows,member=MEMBER):
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=FIELDS);w.writeheader()
    for row in rows:w.writerow(row)
    sink=io.BytesIO()
    with zipfile.ZipFile(sink,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(member,s.getvalue().encode())
    return sink.getvalue()

def row(year,month,attribute,value):
    return {"ReportTitle":"U.S. Feed Grain and Corn Supply and Use",
            "Commodity":"Corn","Region":"United States",
            "MarketYear":f"{year}/{(year+1)%100:02d}","ProjEstFlag":"Proj.",
            "Unit":"Million Bushels","Attribute":attribute,"Value":str(value),
            "ForecastYear":str(year),"ForecastMonth":str(month),
            "ReleaseDate":f"{year}-{month:02d}-09"}

def filled():
    data=[]
    for year in YEARS:
        data.extend([row(year,11,"Exports",2000+year-2017),
                     row(year,11,"Ending Stocks",1500),
                     row(year,12,"Exports",2100+year-2017),
                     row(year,12,"Ending Stocks",1400)])
    return data

class ArchiveTests(unittest.TestCase):
    def test_four_years_complete_from_one_csv(self):
        r=extract_archived(archive(filled()))
        self.assertEqual(len(r["rows"]),4)
        self.assertEqual(r["gaps"],[])
        for v in r["rows"]:
            self.assertEqual(v["delta_exports_mbu"],"100")
            self.assertEqual(v["delta_ending_stocks_mbu"],"-100")
            self.assertEqual(v["selected_rows_nov"],2)
            self.assertEqual(v["selected_rows_dec"],2)
            self.assertEqual(len(v["source_zip_sha256"]),64)
            self.assertNotIn("raw_sha256",v)
        self.assertFalse(r["independent_pit_features_verified"])
        self.assertFalse(r["calibrated_model_ready"])
        self.assertFalse(r["trade_eligible"])

    def test_zip_extra_file_rejected(self):
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_ZIP_CONTENTS"):
            extract_archived(archive(filled(),member="../unsafe.csv"))

    def test_missing_month_is_reported_not_zero(self):
        data=[x for x in filled() if not (x["ForecastYear"]=="2018" and x["ForecastMonth"]=="12")]
        r=extract_archived(archive(data))
        self.assertEqual(len(r["rows"]),3)
        self.assertEqual(len(r["gaps"]),1)
        self.assertEqual(r["gaps"][0]["marketing_year"],"2018/19")

    def test_reliability_projection_is_excluded(self):
        data=filled()
        fake=row(2017,11,"Exports",9999)
        fake["ReportTitle"]="Reliability of United States November Projections"
        data.append(fake)
        r=extract_archived(archive(data))
        self.assertEqual(len(r["rows"]),4)
        self.assertEqual(r["rows"][0]["nov_exports_mbu"],"2000")

    def test_wrong_marketing_year_estimate_excluded(self):
        data=filled()
        fake=row(2017,11,"Exports",9999)
        fake["MarketYear"]="2016/17"
        fake["ProjEstFlag"]="Est."
        data.append(fake)
        r=extract_archived(archive(data))
        self.assertEqual(r["rows"][0]["nov_exports_mbu"],"2000")

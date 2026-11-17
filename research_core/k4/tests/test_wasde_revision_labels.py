"""K4.6 official vintage corn labels: strict no-leakage and false-match tests."""
from __future__ import annotations
from decimal import Decimal
import csv
import io
import unittest
from research_core.k4.wasde_revision_labels import extract_vintage, pair

HEADERS=["ReportTitle","Commodity","Region","MarketYear","ProjEstFlag","Attribute",
         "Value","Unit","ReleaseDate","ForecastYear","ForecastMonth"]
TITLE="U.S. Feed Grain and Corn Supply and Use"

def make_row(year,month,attr,value):
    return {"ReportTitle":TITLE,"Commodity":"Corn","Region":"United States",
            "MarketYear":f"{year}/{(year+1)%100:02d}","ProjEstFlag":"Proj.",
            "Attribute":attr,"Value":str(value),"Unit":"Million Bushels",
            "ReleaseDate":f"{year}-{month:02d}-10","ForecastYear":str(year),
            "ForecastMonth":str(month)}

def csv_bytes(rows):
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=HEADERS)
    w.writeheader()
    for row in rows:w.writerow(row)
    return s.getvalue().encode()

def fixture(year,month,exports,stocks):
    return csv_bytes([make_row(year,month,"Exports",exports),
                      make_row(year,month,"Ending Stocks",stocks)])

class WASDELabelTests(unittest.TestCase):
    def test_current_year_pair(self):
        r=pair(fixture(2024,11,2325,1938),fixture(2024,12,2475,1738),2024,{})
        self.assertEqual(Decimal(r["delta_exports_mbu"]),Decimal(150))
        self.assertEqual(Decimal(r["delta_ending_stocks_mbu"]),Decimal(-200))
        self.assertEqual(Decimal(r["other_net_stock_change_mbu"]),Decimal(-50))
        self.assertFalse(r["independent_pit_features_verified"])

    def test_reliability_statistics_never_used(self):
        bad=make_row(2024,11,"Ending Stocks",9999)
        bad["ReportTitle"]="Reliability of United States November Projections"
        b=csv_bytes([bad,*[make_row(2024,11,a,v) for a,v in [("Exports",2325),("Ending Stocks",1938)]]])
        r=extract_vintage(b,2024,11)
        self.assertEqual(Decimal(r["Ending Stocks"]["value_mbu"]),Decimal(1938))

    def test_last_year_estimate_never_used(self):
        bad=make_row(2024,11,"Exports",9999);bad["MarketYear"]="2023/24";bad["ProjEstFlag"]="Est."
        b=csv_bytes([bad,*[make_row(2024,11,a,v) for a,v in [("Exports",2325),("Ending Stocks",1938)]]])
        self.assertEqual(Decimal(extract_vintage(b,2024,11)["Exports"]["value_mbu"]),Decimal(2325))

    def test_duplicate_series_rejected(self):
        rows=[make_row(2024,11,"Exports",2325),make_row(2024,11,"Exports",2325),
              make_row(2024,11,"Ending Stocks",1938)]
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS"):extract_vintage(csv_bytes(rows),2024,11)

    def test_forecast_vintage_mismatch_rejected(self):
        row=make_row(2024,11,"Exports",2325);row["ForecastMonth"]="12"
        with self.assertRaisesRegex(ValueError,"FORECAST_VINTAGE"):extract_vintage(
            csv_bytes([row,make_row(2024,11,"Ending Stocks",1938)]),2024,11)

    def test_wrong_release_date_rejected(self):
        row=make_row(2024,11,"Exports",2325);row["ReleaseDate"]="2024-12-10"
        with self.assertRaisesRegex(ValueError,"RELEASE_DATE"):extract_vintage(
            csv_bytes([row,make_row(2024,11,"Ending Stocks",1938)]),2024,11)

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError,"INVALID_VALUE"):
            extract_vintage(fixture(2024,11,"NaN",1938),2024,11)

    def test_us_corn_only(self):
        row=make_row(2024,11,"Exports",2325);row["Commodity"]="Soybeans"
        with self.assertRaisesRegex(ValueError,"MISSING_OFFICIAL"):
            extract_vintage(csv_bytes([row,make_row(2024,11,"Ending Stocks",1938)]),2024,11)

    def test_no_record_is_not_zero(self):
        with self.assertRaisesRegex(ValueError,"MISSING_OFFICIAL"):
            extract_vintage(csv_bytes([]),2024,11)

    def test_excessive_or_revised_report_not_prediction(self):
        r=pair(fixture(2025,11,3075,2154),fixture(2025,12,3200,2029),2025,{})
        self.assertEqual(Decimal(r["delta_exports_mbu"]),Decimal(125))
        self.assertEqual(Decimal(r["delta_ending_stocks_mbu"]),Decimal(-125))
        self.assertFalse(r["independent_pit_features_verified"])

if __name__=="__main__":unittest.main()

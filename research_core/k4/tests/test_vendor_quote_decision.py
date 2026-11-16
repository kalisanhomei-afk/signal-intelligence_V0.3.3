"""Deterministic quote decision tests: no credentials, purchases or network."""
import unittest
from research_core.k4.vendor_quote_decision import decision, QuoteReviewError

def quote(counts=(180,1250,3000), costs=("0.01","0.20","0.40")):
    return {
      "schema":"signal-k4-vendor-metadata-quote-only-v1",
      "request_scope":"ONE_CONTRACT_ONE_EVENT_THREE_SCHEMAS_NO_PURCHASE",
      "status":"VENDOR_METADATA_QUOTED_NO_HISTORY_PURCHASED",
      "vendor":"Databento","dataset":"GLBX.MDP3","raw_symbol":"ZCZ6",
      "instrument_id":"12345","quoted_at_utc":"2026-11-16T08:00:00Z",
      "quote_rows":[{"dataset":"GLBX.MDP3","raw_symbol":"ZCZ6","schema":s,
         "start_utc":"2026-11-10T16:30:00Z","end_utc":"2026-11-10T19:30:00Z",
         "record_count_metadata_only":n,"vendor_quoted_usd":c}
         for s,n,c in zip(("ohlcv-1m","trades","tbbo"),counts,costs)],
      "data_download_requests":0,"trading_orders":0,"actual_history_downloaded":False,
      "license_to_redistribute_verified":False,"market_data_asof_authenticated":False
    }

class Review(unittest.TestCase):
    def test_valid_metadata_still_cannot_buy_or_trade(self):
        x=decision(quote())
        self.assertEqual(x["decision"],"QUOTED_PENDING_LICENSE_AND_OWNER_APPROVAL")
        self.assertEqual(x["total_estimated_usd_all_schemas"],"0.61")
        self.assertFalse(x["owner_purchase_approval_given"])
        self.assertFalse(x["event_study_eligible"])

    def test_zero_minute_bars_stops(self):
        self.assertEqual(decision(quote(counts=(0,500,100)))["decision"],"NO_ONE_MINUTE_DATA_STOP")

    def test_nonzero_bars_only_not_executable(self):
        self.assertEqual(decision(quote(counts=(180,0,0)))["decision"],"ONLY_MINUTE_BARS_NOT_EXECUTABLE")

    def test_wrong_contract_stops(self):
        q=quote();q["raw_symbol"]="ZCH7"
        with self.assertRaisesRegex(QuoteReviewError,"SCOPE"):decision(q)

    def test_wrong_scope_date_stops(self):
        q=quote();q["quote_rows"][0]["start_utc"]="2026-11-09T16:30:00Z"
        with self.assertRaisesRegex(QuoteReviewError,"ROW_SCOPE"):decision(q)

    def test_bad_cost_stops(self):
        for bad in ("NaN","-1","Infinity",True):
            q=quote();q["quote_rows"][1]["vendor_quoted_usd"]=bad
            with self.subTest(bad=bad),self.assertRaises(QuoteReviewError):decision(q)

    def test_fake_download_or_trade_stops(self):
        for key,value in (("actual_history_downloaded",True),("trading_orders",1),("data_download_requests",1)):
            q=quote();q[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(QuoteReviewError,"NOT_METADATA_ONLY"):decision(q)

    def test_invalid_quote_time_stops(self):
        q=quote();q["quoted_at_utc"]="2026-11-16T08:00:00+08:00"
        with self.assertRaisesRegex(QuoteReviewError,"UTC"):decision(q)

if __name__=="__main__":
    unittest.main()

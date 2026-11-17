"""Databento quote-only fixture tests: no downloads, no billed API, no secret logs."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

from research_core.k4.vendor_quote_only import (
    DATASET, END, SCHEMAS, START, SYMBOL, QuoteGateError,
    metadata_only_preflight, validated_usd,
)


def fake_client(*, resolve=None, cost="0.015", count=180):
    seen = {"resolve": [], "get_cost": [], "get_record_count": [], "downloads": []}
    def resolved(**kwargs):
        seen["resolve"].append(kwargs)
        return resolve if resolve is not None else {
            "result": {"ZCZ6": [{"d0": "2026-11-10", "d1": "2026-11-11", "s": "12345"}]},
            "not_found": [],
            "message": "OK", "status": 0,
        }
    def quote(**kwargs):
        seen["get_cost"].append(kwargs)
        return cost
    def rows(**kwargs):
        seen["get_record_count"].append(kwargs)
        return count
    def no_download(*args,**kwargs):
        seen["downloads"].append(args)
        raise AssertionError("History downloads are prohibited")
    return SimpleNamespace(
        symbology=SimpleNamespace(resolve=resolved),
        metadata=SimpleNamespace(get_cost=quote,get_record_count=rows),
        timeseries=SimpleNamespace(get_range=no_download),
        batch=SimpleNamespace(submit_job=no_download),
    ),seen


class VendorReadOnlyQuoteTests(unittest.TestCase):
    def test_quote_all_three_schemas_exact_scope_no_history_data(self):
        obj, seen = fake_client()
        r = metadata_only_preflight(obj, clock=datetime(2026,11,16,tzinfo=timezone.utc))
        self.assertEqual(r["instrument_id"], "12345")
        self.assertEqual(r["status"], "VENDOR_METADATA_QUOTED_NO_HISTORY_PURCHASED")
        self.assertFalse(r["actual_history_downloaded"])
        self.assertFalse(r["market_data_asof_authenticated"])
        self.assertFalse(r["license_to_redistribute_verified"])
        self.assertEqual(r["data_download_requests"], 0)
        self.assertEqual(r["trading_orders"], 0)
        self.assertEqual([x["schema"] for x in r["quote_rows"]],list(SCHEMAS))
        self.assertEqual(r["quote_rows"][0]["vendor_quoted_usd"],"0.015")
        self.assertEqual(len(seen["get_cost"]),3)
        self.assertEqual(len(seen["get_record_count"]),3)
        self.assertEqual(seen["downloads"],[])
        for arg in seen["get_cost"]+seen["get_record_count"]:
            self.assertEqual(arg["dataset"], DATASET)
            self.assertEqual(arg["symbols"], [SYMBOL])
            self.assertEqual(arg["start"], START)
            self.assertEqual(arg["end"], END)
            self.assertEqual(arg["stype_in"],"raw_symbol")

    def test_missing_symbol_blocks_quotes(self):
        client,seen=fake_client(resolve={"result":{},"not_found":["ZCZ6"]})
        with self.assertRaisesRegex(QuoteGateError,"NOT_RESOLVED"):
            metadata_only_preflight(client)
        self.assertEqual(seen["get_cost"],[])
        self.assertEqual(seen["downloads"],[])

    def test_ambiguous_symbol_blocks_quotes(self):
        client,seen=fake_client(resolve={"result":{"ZCZ6":[{"s":"111"},{"s":"222"}]},"not_found":[]})
        with self.assertRaisesRegex(QuoteGateError,"AMBIGUOUS"):
            metadata_only_preflight(client)
        self.assertEqual(seen["get_cost"],[])

    def test_non_numeric_instrument_id_blocks_quotes(self):
        client,_=fake_client(resolve={"result":{"ZCZ6":[{"s":"unknown"}]},"not_found":[]})
        with self.assertRaisesRegex(QuoteGateError,"INSTRUMENT_ID_UNVERIFIED"):
            metadata_only_preflight(client)

    def test_negative_nan_and_wrong_type_costs_rejected(self):
        for val in ("NaN", "-1", float("inf"), -0.001, True, None):
            with self.subTest(value=str(val)),self.assertRaises(QuoteGateError):
                validated_usd(val)

    def test_empty_record_count_not_faked_as_real_ticks(self):
        client,_=fake_client(cost="0",count=0)
        r=metadata_only_preflight(client)
        self.assertEqual(r["quote_rows"][0]["record_count_metadata_only"],0)
        self.assertFalse(r["actual_history_downloaded"])

    def test_wrong_record_count_type_rejected(self):
        for val in (-1,True,1.2):
            with self.subTest(value=str(val)):
                client,_=fake_client(count=val)
                with self.assertRaisesRegex(QuoteGateError,"INVALID_VENDOR_RECORD_COUNT"):
                    metadata_only_preflight(client)


if __name__ == "__main__":
    unittest.main()

"""K4 archived pre-release survey poll vintage: index/content/time fail closed."""
import json
import unittest

from research_core.k4.poll_archive_preflight import (
    EVENT, SOURCES, canonical_time, content_matches, index_candidates,
    inspect_capture, inspect_source,
)


class PreReleaseArchiveGateTests(unittest.TestCase):
    def _cdx(self, *rows):
        return {
            "status": "OK",
            "bytes": json.dumps([
                ["timestamp", "original", "digest", "statuscode"], *rows
            ]).encode("utf-8"),
        }

    def test_index_only_accepts_before_17z_on_nov10(self):
        x=self._cdx(
            ["20261110165959", SOURCES[1]["url"], "GOOD", "200"],
            ["20261110170000", SOURCES[1]["url"], "TOO_LATE", "200"],
            ["20261110150000", SOURCES[1]["url"], "BAD_HTTP", "404"],
            ["20261104000000", SOURCES[1]["url"], "TOO_EARLY", "200"])
        hits, status=index_candidates(x)
        self.assertEqual(status,"PRE_RELEASE_INDEX_HITS")
        self.assertEqual(len(hits),1)
        self.assertEqual(hits[0]["at_utc"],"2026-11-10T16:59:59Z")

    def test_blocked_index_does_not_mean_website_never_existed(self):
        hits,status=index_candidates({"status":"ARCHIVE_HTTP_ERROR","http_status":403})
        self.assertEqual(status,"INDEX_UNAVAILABLE")
        self.assertEqual(hits,[])

    def test_malformed_index_refused(self):
        for bad in (b"",b"[]",b"not json"):
            hits,status=index_candidates({"status":"OK","bytes":bad})
            self.assertEqual(hits,[])
            self.assertEqual(status,"INDEX_RESPONSE_UNPARSABLE")

    def test_publisher_quoted_value_requires_corn_context(self):
        self.assertTrue(content_matches(b"<p>corn carryout 1.840 billion bushels</p>", SOURCES[0]))
        self.assertTrue(content_matches(b"<p>U.S. corn ending stocks 1.826 bb</p>", SOURCES[1]))
        self.assertFalse(content_matches(b"<p>soybean 1.840 billion bushels</p>", SOURCES[0]))
        self.assertFalse(content_matches(b"<p>1.826 bb unrelated to corn</p>", SOURCES[0]))

    def test_nonmatching_wayback_memento_replay_never_verifies(self):
        hit={"timestamp":"20261108120000","at_utc":"2026-11-08T12:00:00Z",
             "original_url":SOURCES[0]["url"],"index_digest":"ABC"}
        class FakeHeaders:
            def get(self,name,default=""):
                return "Sun, 08 Nov 2026 12:00:00 GMT" if name == "Memento-Datetime" else default
        class FakeResponse:
            status=200
            headers=FakeHeaders()
            def geturl(self):
                return ("https://web.archive.org/web/20261110120000id_/"
                        + SOURCES[0]["url"])
            def read(self,n):
                return b"<p>corn stocks 1.840 billion bushels</p>"
            def __enter__(self):return self
            def __exit__(self,*_):pass
        res=inspect_capture(hit,SOURCES[0],getter=lambda *a,**k:FakeResponse())
        self.assertEqual(res["status"],"WAYBACK_REPLAY_TIME_MISMATCH")
        self.assertFalse(res["pre_release_value_capture_verified"])

    def test_memento_must_match_timestamp_even_if_body_matches(self):
        hit={"timestamp":"20261108120000","at_utc":"2026-11-08T12:00:00Z",
             "original_url":SOURCES[0]["url"],"index_digest":"ABC"}
        class Headers:
            def get(self,k,default=""):return "Mon, 09 Nov 2026 12:00:00 GMT"
        class Response:
            status=200
            headers=Headers()
            def geturl(self):return "https://web.archive.org/web/20261108120000id_/"+SOURCES[0]["url"]
            def read(self,n):return b"corn stocks 1.840 billion bushels"
            def __enter__(self):return self
            def __exit__(self,*_):pass
        res=inspect_capture(hit,SOURCES[0],getter=lambda *a,**k:Response())
        self.assertEqual(res["status"],"WAYBACK_MEMENTO_TIME_MISMATCH")
        self.assertFalse(res["pre_release_value_capture_verified"])

    def test_unavailable_does_not_certify(self):
        src=inspect_source(SOURCES[0], getter=lambda *args,**kw: (
            (_ for _ in ()).throw(TimeoutError("archive unavailable"))))
        self.assertEqual(src["cdx_status"],"INDEX_UNAVAILABLE")
        self.assertEqual(src["verified_independent_pre_release_value_captures"],0)
        self.assertFalse(src["trade_eligible"])

    def test_wrong_timestamp_format_blocked(self):
        for timestamp in ("202611081200","20261108120000Z","2026110812000x"):
            with self.assertRaises(ValueError):
                canonical_time(timestamp)


if __name__ == "__main__":
    unittest.main()

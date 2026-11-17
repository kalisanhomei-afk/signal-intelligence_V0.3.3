"""K5.2 one-time bounded pre-EIA web-source receipt for two distinct forecasts.

Never treats one named model or a mutable calendar widget as analyst consensus.
Only compact numeric/source metadata is committed; copyright-protected third-party
HTML is not redistributed with source control.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html.parser import HTMLParser
import argparse, hashlib, json, re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SOURCES={
    "named_forecaster_arc":"https://www.getarcresearch.com/commodities/natural-gas/scorecard/",
    "metatrader_event_calendar":"https://www.metatrader.com/en/economic-calendar/united-states/eia-natural-gas-storage-change",
}
HOSTS={"www.getarcresearch.com","getarcresearch.com","www.metatrader.com","metatrader.com"}
MAX_BYTES=1_000_000

class ExtractText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript") and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
    def joined(self):
        return " ".join(" ".join(self.parts).split())

def parse_candidate(key,text):
    text=" ".join(text.split())
    if key=="named_forecaster_arc":
        if not re.search(r"Week ending Nov 13, 2026",text):
            raise ValueError("TARGET_WEEK_NOT_PRESENT")
        m=re.search(r"Open call\s*\+?(-?\d+(?:\.\d+)?)\s*Bcf,\s*build",text)
        if not m:
            raise ValueError("NAMED_CALL_NOT_FOUND")
        p=re.search(r"Published\s+(Fri Nov 13,\s*7:21 PM ET)",text)
        if not p:
            raise ValueError("PUBLISHER_CLAIM_NOT_FOUND")
        val=float(m.group(1))
        if val!=13.4:
            raise ValueError("WEB_EXPECTED_NUMBER_DIFFERENT")
        return {"event_id":"EIA-WNGSR-2026-11-19",
                "target_week_end":"2026-11-13","units":"Bcf",
                "forecast_net_change_bcf":val,
                "forecast_class":"SINGLE_NAMED_FORECASTER_NOT_CONSENSUS",
                "source_publisher":"Arc Research",
                "publisher_publication_time_claim":p.group(1),
                "publisher_claim_independently_authenticated":False}
    if key=="metatrader_event_calendar":
        if not re.search(r"19 Nov 2026",text):
            raise ValueError("TARGET_RELEASE_NOT_PRESENT")
        m=re.search(r"Next release\s+19 Nov 2026\s+15:30 GMT.{0,260}?\bForecast\s+(-?\d+(?:\.\d+)?)\s*B",text,re.I)
        if not m:
            raise ValueError("CALENDAR_NEXT_FORECAST_NOT_FOUND")
        val=float(m.group(1))
        if val!=69:
            raise ValueError("WEB_EXPECTED_NUMBER_DIFFERENT")
        return {"event_id":"EIA-WNGSR-2026-11-19",
                "target_week_end":"2026-11-13","units":"Bcf",
                "forecast_net_change_bcf":val,
                "forecast_class":"CALENDAR_INDICATIVE_VALUE_CONSENSUS_METHOD_UNVERIFIED",
                "source_publisher":"MetaTrader economic calendar",
                "publisher_publication_time_claim":None,
                "publisher_claim_independently_authenticated":False}
    raise ValueError("UNRECOGNIZED_SOURCE_ROLE")

def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def capture(url,expected_role):
    if SOURCES.get(expected_role)!=url:
        raise ValueError("SOURCE_NOT_ALLOWLISTED")
    started=now()
    try:
        with urlopen(Request(url,headers={"User-Agent":"SIGNAL-K52-PreRelease-Research/1.0"}),timeout=12) as response:
            actual=response.geturl()
            u=urlsplit(actual)
            if u.scheme!="https" or u.hostname not in HOSTS or u.username or u.password:
                raise ValueError("OFFDOMAIN_REDIRECT")
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:
                raise ValueError("OVERSIZED_HTML")
            finished=now()
            if finished>="2026-11-19T15:30:00Z":
                raise ValueError("TOO_LATE_FOR_PRE_RELEASE_SNAPSHOT")
            page=ExtractText()
            page.feed(raw.decode("utf-8",errors="replace"))
            summary=parse_candidate(expected_role,page.joined())
            return {
                "status":"WEB_BYTES_CAPTURED_TARGET_VERIFIED_NO_INDEPENDENT_PIT",
                "source_role":expected_role,
                "source_url":url,
                "response_url":actual,
                "source_raw_html_sha256":hashlib.sha256(raw).hexdigest(),
                "source_raw_html_bytes":len(raw),
                "capture_started_utc":started,
                "capture_finished_utc":finished,
                "source_metadata_no_immutable_first_publication_proof":True,
                "raw_html_not_committed_to_public_repository":True,
                **summary,
                "trade_eligible":False
            }
    except (ValueError,HTTPError,URLError,TimeoutError,OSError) as exc:
        return {"status":"SOURCE_UNAVAILABLE_OR_TARGET_NOT_VERIFIED",
                "source_role":expected_role,"source_url":url,
                "failure_type":type(exc).__name__,
                "failure_code":str(exc)[:100] if isinstance(exc,(ValueError,HTTPError)) else None,
                "source_raw_html_sha256":None,
                "forecast_net_change_bcf":None,
                "trade_eligible":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    data={
        "schema":"signal-k52-public-pre-eia-external-forecast-observations-v1",
        "status":"UNVERIFIED_CONSENSUS_CONFLICTING_FORECAST_CANDIDATES",
        "event_id":"EIA-WNGSR-2026-11-19",
        "event_scheduled_utc":"2026-11-19T15:30:00Z",
        "frozen_signal_v0_bcf":61,
        "market_analyst_consensus_certified":False,
        "observations":[capture(url,role) for role,url in SOURCES.items()],
        "trade_eligible":False
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("K52_EXTERNAL_FORECAST_RECEIPTS="+json.dumps(data,ensure_ascii=True,separators=(",",":")))
if __name__=="__main__":main()

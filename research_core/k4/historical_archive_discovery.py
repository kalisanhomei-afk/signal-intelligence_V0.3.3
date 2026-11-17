"""K4.7 bounded official-source discovery only; do not infer PIT from a dated URL."""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

USDA_ZIP_PATH="sites/default/files/documents/oce-wasde-report-data-2016-01-to-2020-12.zip"
CANDIDATES={
    "historic_usda_zip_primary":"https://www.usda.gov/"+USDA_ZIP_PATH,
    "historic_usda_zip_mirror":"https://usda.azureedge.us/"+USDA_ZIP_PATH,
    "fgis_report_index":"https://mymarketnews.ams.usda.gov/filerepo/reports?field_slug_id_value=3071",
    "fgis_report_index_slug":"https://mymarketnews.ams.usda.gov/filerepo/reports?field_slug_id_value=WA_GR101",
}
HOSTS={"www.usda.gov","usda.azureedge.us","mymarketnews.ams.usda.gov"}
MAX_BYTES=10_000_000
class Anchors(HTMLParser):
    def __init__(self):
        super().__init__();self.items=[];self.href=None;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a": self.href=dict(attrs).get("href");self.parts=[]
    def handle_data(self,data):
        if self.href is not None:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            title=" ".join(" ".join(self.parts).split())
            if any(k in (title+" "+self.href).upper() for k in ("WA_GR101","GR101","2025","2024","REPORT","TXT","CSV")):
                self.items.append({"label":title[:90],"href":self.href[:400]})
            self.href=None;self.parts=[]

def once(url):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname not in HOSTS:
        raise ValueError("SOURCE_NOT_ALLOWLISTED")
    try:
        with urlopen(Request(url,headers={"User-Agent":"SIGNAL-K47-SourceDiscovery/1"}),timeout=12) as resp:
            final=resp.geturl()
            final_u=urlsplit(final)
            if final_u.scheme!="https" or final_u.hostname not in HOSTS:
                raise ValueError("UNEXPECTED_REDIRECT")
            raw=resp.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError("OVERSIZED_RESPONSE")
            ctype=resp.headers.get("Content-Type","")
    except HTTPError as ex:
        return {"status":"HTTP_UNAVAILABLE","http_status":ex.code,"url":url}
    except (URLError,TimeoutError,OSError) as ex:
        return {"status":"NETWORK_UNAVAILABLE","error_type":type(ex).__name__,"url":url}
    record={"status":"RETRIEVED_NOT_PIT","url":final,"bytes":len(raw),
            "sha256":hashlib.sha256(raw).hexdigest(),"content_type":ctype}
    if url.endswith(".zip"):
        import zipfile,io
        try:
            z=zipfile.ZipFile(io.BytesIO(raw))
            record["archive_entries"]=[{"name":s.filename,"bytes":s.file_size} for s in z.infolist()[:100]]
            record["entry_count"]=len(z.infolist())
        except (zipfile.BadZipFile,ValueError):
            record["status"]="NOT_VALID_ZIP"
    else:
        p=Anchors();p.feed(raw.decode("utf-8",errors="replace"))
        record["candidate_links"]=p.items[:30]
        record["link_count"]=len(p.items)
        record["archive_dated_file_links"]=[l for l in p.items if
            l["href"].lower().endswith((".txt",".pdf")) and any(str(y) in l["href"] for y in (2024,2025,2026))][:12]
    return record

def probe():
    return {"schema":"signal-k47-official-archive-discovery-v1",
            "results":{k:once(u) for k,u in CANDIDATES.items()},
            "asof_official_raw_verified":False,
            "historical_feature_pit_certified":False,
            "training_eligible":False,"trade_eligible":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();r=probe()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("K47_DISCOVERY_ONLY",json.dumps({k:{field:value for field,value in v.items()
        if field in ("status","http_status","bytes","link_count","entry_count","archive_entries","archive_dated_file_links")}
        for k,v in r["results"].items()})[:9000])

if __name__=="__main__":main()

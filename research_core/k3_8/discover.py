"""Resolve one released USDA ESMIS .txt URL by exact report date.

The discovery page is NOT release-time proof. Never construct speculative
filenames. An empty, blocked, ambiguous, or stale listing fails closed.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
from html.parser import HTMLParser
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from research_core.k3_8.capture import CaptureError, checked_url

OFFICIAL_PUBLICATIONS = {
    "NASS": "https://esmis.nal.usda.gov/publication/crop-progress",
    "WASDE": "https://esmis.nal.usda.gov/publication/world-agricultural-supply-and-demand-estimates",
}
MAX_HTML_BYTES = 1_500_000

class CatalogRedirects(HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urlsplit(newurl)
        if u.scheme != "https" or u.hostname != "esmis.nal.usda.gov" or u.username or u.password:
            raise CaptureError("ESMIS_CATALOG_OFFICIAL_REDIRECT_REQUIRED")
        self.chain.append(newurl)
        if len(self.chain) > 3:
            raise CaptureError("ESMIS_CATALOG_REDIRECT_LIMIT")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag != "a" or self.active is not None:
            return
        opts = dict(attrs)
        if opts.get("href"):
            self.active = {"href": opts["href"], "title": opts.get("title", ""),
                           "aria": opts.get("aria-label", ""), "text": []}

    def handle_data(self, data):
        if self.active is not None:
            self.active["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            item = self.active
            item["text"] = " ".join(item["text"])
            self.links.append(item)
            self.active = None


def exact_day_regex(d: date):
    month = d.strftime("%b")
    long = d.strftime("%B")
    return re.compile(r"\b(?:" + re.escape(month) + "|" + re.escape(long) +
                      r")\.?\s+0?" + str(d.day) + r",?\s+" + str(d.year) + r"\b", re.I)


def extract_direct_txt(html: str, source: str, release_day: date) -> str:
    if source not in OFFICIAL_PUBLICATIONS:
        raise CaptureError("UNKNOWN_OFFICIAL_PUBLICATION")
    collector = LinkCollector()
    collector.feed(html)
    regex = exact_day_regex(release_day)
    candidates = set()
    for link in collector.links:
        href = link["href"]
        label = " ".join([link["text"], link["title"], link["aria"]])
        if not regex.search(label) or not re.search(r"(?:^|\W)txt(?:$|\W)", label, re.I):
            continue
        url = urljoin(OFFICIAL_PUBLICATIONS[source], href)
        if urlsplit(url).query:
            continue
        try:
            checked_url(url, source)
        except CaptureError:
            continue
        candidates.add(url)
    if not candidates:
        raise CaptureError("EXACT_RELEASE_DATE_OFFICIAL_TXT_NOT_LISTED")
    if len(candidates) != 1:
        raise CaptureError("AMBIGUOUS_MULTIPLE_OFFICIAL_TXT_FOR_RELEASE_DATE")
    return next(iter(candidates))


def discover_exact_txt_with_evidence(source: str, release_day: date) -> dict:
    """Observe original ESMIS listing bytes, not retrospective publication time.

    The collected HTML SHA-256 and UTC response-finish time bind the selected
    full-day TXT link to this runner's *contemporaneous* catalog observation.
    """
    if source not in OFFICIAL_PUBLICATIONS:
        raise CaptureError("UNKNOWN_OFFICIAL_PUBLICATION")
    handler = CatalogRedirects()
    address = OFFICIAL_PUBLICATIONS[source]
    request = Request(address, headers={
        "User-Agent": "SIGNAL-K38-ESMIS-exact-release-resolver/0.1",
        "Cache-Control": "no-cache", "Pragma": "no-cache",
        "Accept-Encoding": "identity",
    })
    started = datetime.now(timezone.utc)
    try:
        with build_opener(handler).open(request, timeout=12) as response:
            final_url = response.geturl()
            final = urlsplit(final_url)
            if final.hostname != "esmis.nal.usda.gov" or final.scheme != "https":
                raise CaptureError("ESMIS_CATALOG_UNAPPROVED_FINAL_URL")
            if response.status != 200:
                raise CaptureError("ESMIS_CATALOG_UNAVAILABLE")
            html = response.read(MAX_HTML_BYTES + 1)
            finished = datetime.now(timezone.utc)
    except HTTPError as e:
        raise CaptureError(f"ESMIS_CATALOG_HTTP_{e.code}") from e
    except (URLError, TimeoutError, OSError) as e:
        raise CaptureError("ESMIS_CATALOG_UNAVAILABLE") from e
    if not html or len(html) > MAX_HTML_BYTES:
        raise CaptureError("ESMIS_CATALOG_EMPTY_OR_TOO_LARGE")
    selected = extract_direct_txt(html.decode("utf-8", errors="replace"), source, release_day)
    return {
        "source": source, "release_date": release_day.isoformat(),
        "selected_url": selected, "catalog_bytes": html,
        "catalog_requested_url": address, "catalog_resolved_url": final_url,
        "catalog_sha256": hashlib.sha256(html).hexdigest(),
        "catalog_request_started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "catalog_response_finished_at_utc": finished.isoformat().replace("+00:00", "Z"),
    }


def discover_exact_txt(source: str, release_day: date) -> str:
    """Backwards-compatible URL-only locator used by layout smoke tests."""
    return discover_exact_txt_with_evidence(source, release_day)["selected_url"]

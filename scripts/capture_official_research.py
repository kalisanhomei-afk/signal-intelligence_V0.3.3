#!/usr/bin/env python3
"""Save bytes of one explicitly chosen US government research release.

No discovery/scraping. This captures today's HTTP response, NOT proof that its bytes
are identical to those present at the historical publication instant.
Only stdlib required; no data-model/financial action can be triggered.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from datetime import datetime, timezone
import zipfile

ALLOWED_HOSTS = {
    "www.federalreserve.gov": "federalreserve",
    "federalreserve.gov": "federalreserve",
    "home.treasury.gov": "treasury",
    "www.treasury.gov": "treasury",
    "ticdata.treasury.gov": "treasury",
}
SECRET_KEYS = {"key", "api_key", "apikey", "token", "access_token", "authorization", "auth", "secret"}
DEFAULT_LIMIT = 30 * 1024 * 1024
MAX_UNCOMPRESSED = 250 * 1024 * 1024
MAX_MEMBERS = 500


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def validate_url(url: str, origin_group: str | None = None) -> str:
    p = urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.port is not None or p.fragment:
        raise ValueError("Only simple HTTPS URLs with no credentials, port or fragment are accepted")
    if (p.hostname or "") not in ALLOWED_HOSTS:
        raise ValueError("URL host is not in the official government allowlist")
    if origin_group and ALLOWED_HOSTS[p.hostname] != origin_group:
        raise ValueError("Cross-agency redirects are not allowed")
    if any(k.lower() in SECRET_KEYS for k, _ in parse_qsl(p.query, keep_blank_values=True)):
        raise ValueError("Refusing URLs that might contain sensitive query parameters")
    return ALLOWED_HOSTS[p.hostname]


class RestrictedRedirect(HTTPRedirectHandler):
    def __init__(self, original_group: str):
        self.original_group = original_group
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.original_group)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_zip(data: bytes) -> dict:
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("ZIP signature missing")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        if not infos or len(infos) > MAX_MEMBERS:
            raise ValueError("ZIP member count is invalid or too large")
        total = 0
        for member in infos:
            name = member.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if not name or name.startswith("/") or ".." in path.parts or ":" in path.parts[0]:
                raise ValueError("Unsafe ZIP member name")
            if member.flag_bits & 1:
                raise ValueError("Encrypted ZIP member is not supported")
            total += member.file_size
            if total > MAX_UNCOMPRESSED:
                raise ValueError("Uncompressed ZIP contents exceed safety limit")
        return {"member_count": len(infos), "uncompressed_size_declared": total}


def validate_body(data: bytes, kind: str) -> dict:
    if kind == "zip":
        return validate_zip(data)
    if kind == "html":
        lower = data[:8192].lstrip(b"\xef\xbb\xbf \r\n\t").lower()
        if b"<html" not in lower and b"<!doctype html" not in lower:
            raise ValueError("Expected HTML: no HTML signature in initial bytes")
        return {}
    raise ValueError("Expected kind must be html or zip")


def capture(url: str, kind: str, output_dir: Path, *, max_bytes: int = DEFAULT_LIMIT, opener=None) -> dict:
    group = validate_url(url)
    if kind not in ("html", "zip") or not (1 <= max_bytes <= 100 * 1024 * 1024):
        raise ValueError("Invalid kind or byte limit")
    requester = opener or build_opener(RestrictedRedirect(group))
    request = Request(url, headers={"User-Agent": "SIGNAL-ResearchEvidence/0.1 (one-off source capture)",
                                    "Accept-Encoding": "identity"})
    started = utc_now()
    with requester.open(request, timeout=20) as response:
        final = response.geturl()
        validate_url(final, group)
        status = getattr(response, "status", 200)
        if status != 200:
            raise ValueError("Expected HTTP 200")
        headers = response.headers
        expected_len = headers.get("Content-Length")
        if expected_len and expected_len.isdigit() and int(expected_len) > max_bytes:
            raise ValueError("Server announced excessive response size")
        parts = []
        n = 0
        while True:
            chunk = response.read(min(65536, max_bytes - n + 1))
            if not chunk:
                break
            n += len(chunk)
            if n > max_bytes:
                raise ValueError("Downloaded body is larger than byte limit")
            parts.append(chunk)
        data = b"".join(parts)
        if not data:
            raise ValueError("Empty response cannot be archived")
        result = validate_body(data, kind)
        completed = utc_now()
        received_headers = {k.lower(): headers.get(k) for k in ("Content-Type", "Content-Length", "Last-Modified", "ETag")}
    sha = hashlib.sha256(data).hexdigest()
    safe_time = completed.replace(":", "").replace("-", "").replace(".", "_")
    prefix = f"{safe_time}_{sha[:12]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"{prefix}.{kind}"
    json_path = output_dir / f"{prefix}.receipt.json"
    receipt = {
        "schema": "signal.raw_capture_receipt.v0.1",
        "status": "CAPTURED_NOT_PIT_VERIFIED",
        "requested_url": url, "response_url": final,
        "source_agency_group": group,
        "http_status": status, "response_headers": received_headers,
        "started_retrieval_utc": started,
        "completed_retrieval_utc": completed,
        "reported_publication_utc": None,
        "contemporaneous_original_file_certified": False,
        "raw_body_byte_count": len(data), "raw_body_sha256": sha,
        "saved_raw_basename": raw_path.name,
        "archive_inspection": result,
        "license_status": "UNVERIFIED",
        "accepted_for_model": False,
        "note": "Hash belongs to exact HTTP body obtained now; historical release identity/time and rights still need independent proof.",
    }
    # Exclusive creation: no silent overwrite of historical evidence.
    with raw_path.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    with json_path.open("x", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    receipt["local_receipt_path"] = str(json_path)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture ONE official historical source response, no model actions")
    parser.add_argument("url", help="Exact, individually reviewed official file URL, HTTPS only")
    parser.add_argument("--kind", required=True, choices=["html", "zip"])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_LIMIT)
    a = parser.parse_args()
    receipt = capture(a.url, a.kind, a.out, max_bytes=a.max_bytes)
    print(json.dumps({"receipt": receipt["local_receipt_path"], "sha256": receipt["raw_body_sha256"],
                      "size": receipt["raw_body_byte_count"], "pit_verified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()

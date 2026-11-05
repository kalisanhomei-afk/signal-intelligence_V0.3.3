#!/usr/bin/env python3
"""SIGNAL V0.3 — 公開 RSS/Atom「發現層」。

只保存標題/原文連結/時間/來源與採集健康度。不抓全文、不產生 AI 事實摘要。
支援無網路 fixtures 完整測試、來源失敗保留舊資料、明確的 last_success 時間。
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import email.utils
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
ATOM = '{http://www.w3.org/2005/Atom}'
DC = '{http://purl.org/dc/elements/1.1/}'
MAX_BYTES = 3_000_000
USER_AGENT = 'SIGNAL-PrivateReader/0.3 (+RSS headlines and attribution)'
LOGGER = logging.getLogger('SIGNAL')


def utcnow():
    return dt.datetime.now(UTC)


def time_str(t):
    return t.astimezone(UTC).isoformat(timespec='seconds')


def parse_time(raw):
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        v = email.utils.parsedate_to_datetime(raw)
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return time_str(v)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        v = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return time_str(v)
    except ValueError:
        return None


def text_of(parent, name):
    node = parent.find(name)
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip() if node is not None else ''


def clean_text(text):
    return re.sub(r'\s+', ' ', text or '').strip()[:240]


def normalize_url(raw):
    if not raw:
        return ''
    try:
        u = urlsplit(raw.strip())
        if u.scheme.lower() not in ('http', 'https') or not u.hostname or u.username or u.password:
            return ''
        q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
             if not (k.lower().startswith('utm_') or k.lower() in ('fbclid', 'gclid', 'mc_cid', 'mc_eid'))]
        return urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path or '/', urlencode(q), '')).rstrip('/')
    except ValueError:
        return ''


def parse_xml(body, source, allow_empty=False):
    # RSS 不是可信程式碼；拒絕自訂 entity/DTD 並限制大小。
    if len(body) > MAX_BYTES or b'<!doctype' in body.lower() or b'<!entity' in body.lower():
        raise ValueError('XML rejected: size or DTD/entity not permitted')
    root = ET.fromstring(body)
    raw = []
    if root.tag == ATOM + 'feed' or root.tag.endswith('}feed'):
        for item in root.findall(ATOM + 'entry'):
            url = ''
            for link in item.findall(ATOM + 'link'):
                if link.get('rel', 'alternate') == 'alternate' and link.get('href'):
                    url = link.attrib['href']
                    break
            raw.append((text_of(item, ATOM + 'title'), url,
                        text_of(item, ATOM + 'published') or text_of(item, ATOM + 'updated')))
    else:
        # A valid RSS/RDF document can legitimately be empty (e.g. arXiv weekends).
        if not (root.tag.lower().endswith('rss') or root.tag.lower().endswith('rdf')):
            raise ValueError('Unexpected XML root, expected RSS/Atom/RDF')
        for item in list(root.findall('.//item')) + list(root.findall('.//{http://purl.org/rss/1.0/}item')):
            raw.append((text_of(item, 'title'), text_of(item, 'link'),
                        text_of(item, 'pubDate') or text_of(item, DC + 'date') or text_of(item, 'date')))
    records = []
    used = set()
    for title, url, published in raw:
        clean_url = normalize_url(url)
        title = clean_text(title)
        if not title or not clean_url or clean_url in used:
            continue
        used.add(clean_url)
        records.append({
            'id': 'rss-' + hashlib.sha256(clean_url.encode('utf-8')).hexdigest()[:22],
            'title': title, 'url': clean_url,
            'source_id': source['id'], 'publisher_id': source.get('publisher_id'), 'source': source['name'],
            'verification_state': '未審核／僅標題來源',
            'source_kind': source['kind'], 'category': source['category'],
            'published_at': parse_time(published), 'status': '未審核標題', 'summary': None,
        })
    if not records and not allow_empty:
        raise ValueError('RSS/Atom has no valid headline/link entries')
    return records[:source.get('limit', 18)]


def fetch(source):
    req = Request(source['url'], headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.8,*/*;q=0.3'
    })
    with urlopen(req, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status}')
        blob = response.read(MAX_BYTES + 1)
    return parse_xml(blob, source)


def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
        json.dump(obj, file, ensure_ascii=False, indent=2)
        file.write('\n')
        tmp = file.name
    os.replace(tmp, path)


def run_job(*, sources, previous, now, loader, max_items=350, ttl_days=45):
    previous_items = {x['id']: x for x in previous.get('items', []) if 'id' in x}
    prev_health = {x['source_id']: x for x in previous.get('sources', []) if 'source_id' in x}
    freshness = dict(previous_items)
    health = []
    successes = 0
    newly = 0

    def collect(src):
        t0 = time.monotonic()
        try:
            items = loader(src)
            return src, items, None, round((time.monotonic() - t0) * 1000)
        except Exception as exc:
            return src, [], f'{type(exc).__name__}: {exc}'[:220], round((time.monotonic() - t0) * 1000)

    with ThreadPoolExecutor(max_workers=min(len(sources), 5)) as executor:
        futures = [executor.submit(collect, s) for s in sources]
        # Keep report order stable, regardless of completion order.
        by_id = {entry[0]['id']: entry for entry in (future.result() for future in futures)}

    for src in sources:
        _, items, error, latency = by_id[src['id']]
        old = prev_health.get(src['id'], {})
        h = {'source_id': src['id'], 'publisher_id': src.get('publisher_id'), 'source': src['name'], 'category': src['category'],
             'source_kind': src['kind'], 'ok': error is None,
             'last_attempt_at': time_str(now), 'last_success_at': old.get('last_success_at'),
             'count': len(items), 'latency_ms': latency, 'error': error}
        if error is None:
            successes += 1
            h['last_success_at'] = time_str(now)
            for item in items:
                uid = item['id']
                if uid not in previous_items:
                    newly += 1
                previous_first = previous_items.get(uid, {}).get('first_seen_at')
                item['first_seen_at'] = previous_first or time_str(now)
                item['last_seen_at'] = time_str(now)
                freshness[uid] = item
        else:
            LOGGER.warning('%s: %s', src['id'], error)
        health.append(h)

    expire_before = now - dt.timedelta(days=ttl_days)
    def keep(item):
        date = parse_time(item.get('published_at') or item.get('first_seen_at'))
        if date is None:
            return False  # 舊版無時間又無 first_seen，不永久留存。
        t = dt.datetime.fromisoformat(date)
        return expire_before <= t <= now + dt.timedelta(days=2)
    kept = [item for item in freshness.values() if keep(item)]
    kept.sort(key=lambda x: (x.get('published_at') or x.get('first_seen_at') or '', x['id']), reverse=True)
    kept = kept[:max(1, max_items)]
    prev_meta = previous.get('meta', {})
    result = {
        'meta': {
            'version': '0.3', 'generated_at': time_str(now),
            'last_attempt_at': time_str(now),
            'last_success_at': time_str(now) if successes else prev_meta.get('last_success_at'),
            'successful_sources': successes, 'source_count': len(sources),
            'all_sources_healthy': successes == len(sources), 'new_items_in_run': newly,
            'item_count': len(kept), 'retention_days': ttl_days,
            'note': '未審核的原始標題。不得當作已核實的重大新聞、AI 分析結論或投資訊號。'
        },
        'items': kept,
        'sources': health,
    }
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture-dir', help='離線測試：依 source_id.xml 在此目錄讀取，不連外')
    p.add_argument('--output', default=str(BASE / 'data/discovered.json'))
    p.add_argument('--as-of', help='fixture 用的 UTC 時間，例如 2026-11-05T08:00:00+00:00')
    p.add_argument('--max-items', type=int, default=350)
    p.add_argument('--min-success', type=int, default=1, help='成功來源少於此數就以狀態碼 2 回報（仍保存健康紀錄）')
    p.add_argument('--production', action='store_true', help='正式上線前強制來源授權及 live-test 關卡')
    args = p.parse_args(argv)
    cfg = read_json(BASE / 'data/sources.json', {})
    from audit_sources import audit_registry
    governance = audit_registry(read_json(BASE / 'data/source_registry.json', {}), cfg, production=args.production)
    if governance['errors']:
        raise SystemExit('來源治理檢核失敗：' + '; '.join(governance['errors']))
    sources = [src for src in cfg.get('sources', []) if src.get('enabled', True)]
    if not sources:
        raise SystemExit('未設定可用來源')
    out_path = Path(args.output)
    previous = read_json(out_path, {'items': [], 'sources': [], 'meta': {}})
    now = dt.datetime.fromisoformat(args.as_of.replace('Z', '+00:00')).astimezone(UTC) if args.as_of else utcnow()

    if args.fixture_dir:
        fixtures = Path(args.fixture_dir)
        def loader(src):
            return parse_xml((fixtures / (src['id'] + '.xml')).read_bytes(), src)
    else:
        loader = fetch
    result = run_job(sources=sources, previous=previous, now=now, loader=loader, max_items=args.max_items)
    write_json(out_path, result)
    print(json.dumps({
        'item_count': len(result['items']), 'new_items': result['meta']['new_items_in_run'],
        'sources_ok': result['meta']['successful_sources'], 'sources_total': len(sources),
        'failed': [x['source_id'] for x in result['sources'] if not x['ok']],
        'output': str(out_path),
    }, ensure_ascii=False))
    # 部分來源故障仍繼續服務，但回報健康度；全部失敗讓排程工作標紅。
    return 0 if result['meta']['successful_sources'] >= max(1,args.min_success) else 2


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    sys.exit(main())

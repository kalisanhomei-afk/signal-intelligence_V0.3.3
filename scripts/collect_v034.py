#!/usr/bin/env python3
"""SIGNAL V0.3.4: fetch and persist only reviewed public RSS descriptive metadata.

No paywalled article content, API keys, social tracking, endorsements or AI inference.
If all sources fail, previous records remain but staleness/error are displayed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from refresh import parse_xml, parse_time, time_str, utcnow

BASE = Path(__file__).resolve().parents[1]
MAX_BYTES = 2_000_000
EXPECTED = {
    'fed-monetary': ('fed', 'www.federalreserve.gov', 'https://www.federalreserve.gov/feeds/press_monetary.xml'),
    'bea-news': ('bea', 'apps.bea.gov', 'https://apps.bea.gov/rss/rss.xml'),
    'arxiv-ai': ('arxiv', 'rss.arxiv.org', 'https://rss.arxiv.org/rss/cs.AI'),
    'arxiv-robotics': ('arxiv', 'rss.arxiv.org', 'https://rss.arxiv.org/rss/cs.RO'),
    'eia-energy': ('eia', 'www.eia.gov', 'https://www.eia.gov/rss/todayinenergy.xml'),
    'nasa-news': ('nasa', 'www.nasa.gov', 'https://www.nasa.gov/feed/'),
    'eu-press': ('eu_commission', 'ec.europa.eu', 'https://ec.europa.eu/commission/presscorner/api/rss?language=en'),
    'mit-research': ('mit_news', 'news.mit.edu', 'https://news.mit.edu/rss/research'),
}


def read_json(p: Path, default):
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


def atomic_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=p.parent, delete=False) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
        tmp = f.name
    os.replace(tmp, p)


def checked_sources(config):
    """Fail closed: this is a finite, reviewed list; cannot just append unreviewed feeds."""
    if config.get('review_scope') != 'descriptive_public_metadata_only':
        raise ValueError('Missing descriptive-metadata-only policy')
    checked = []
    seen = set()
    for raw in config.get('sources', []):
        source = dict(raw)
        sid = source.get('id')
        if sid not in EXPECTED or sid in seen:
            raise ValueError(f'Unreviewed or repeated feed: {sid}')
        seen.add(sid)
        pub_id, host, exact_url = EXPECTED[sid]
        parsed = urlsplit(source.get('url', ''))
        evidence = urlsplit(source.get('evidence_url', ''))
        if (source.get('publisher_id') != pub_id or parsed.scheme != 'https'
                or parsed.hostname != host or source.get('url') != exact_url or parsed.username or parsed.password
                or source.get('status') != 'metadata_only'
                or not source.get('terms_reviewed_at') or evidence.scheme != 'https'
                or not evidence.hostname or not source.get('scope_note')):
            raise ValueError(f'Policy review incomplete: {sid}')
        source['limit'] = min(20, max(1, int(source.get('max_items', 16))))
        checked.append(source)
    if not checked:
        raise ValueError('No approved metadata sources')
    return checked


def fetch_metadata(source):
    parsed = urlsplit(source['url'])
    req = Request(source['url'], headers={
        'User-Agent': 'SIGNAL-Reader/0.3.4 (source metadata; link attribution only)',
        'Accept': 'application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.8',
    })
    with urlopen(req, timeout=15) as resp:
        final = urlsplit(resp.url)
        if resp.status != 200 or final.scheme != 'https' or final.hostname != parsed.hostname:
            raise ValueError('Unsafe redirect / HTTP status')
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Feed exceeds size limit')
    # arXiv sometimes legitimately publishes zero new papers over weekends.
    return parse_xml(data, source, allow_empty=True)


def collect(sources, previous, loader, *, now=None, ttl_days=45, limit=420, pause=None):
    now = now or utcnow()
    tnow = time_str(now)
    old_by_id = {x['id']:x for x in previous.get('items', []) if x.get('id')}
    old_health = {x['source_id']:x for x in previous.get('sources', []) if x.get('source_id')}
    merged = dict(old_by_id)
    health = []
    success_count = new_count = 0
    last_arxiv_time = None
    pause = pause or time.sleep

    for src in sources:
        sid = src['id']
        if src['publisher_id'] == 'arxiv' and last_arxiv_time is not None:
            # arXiv limits all legacy API requests to one per three seconds and one connection at a time.
            wait = 3.6 - (time.monotonic() - last_arxiv_time)
            if wait > 0:
                pause(wait)
        start = time.monotonic()
        error = None
        fresh = []
        try:
            fresh = loader(src)
            if not isinstance(fresh, list):
                raise ValueError('Unexpected feed parser result')
            success_count += 1
            for raw in fresh:
                # Store metadata only; parser must not attach articles/summaries.
                obj = {k:raw.get(k) for k in ('id','title','url','source_id','publisher_id','source',
                                                'category','source_kind','published_at')}
                if not obj['id'] or not obj['title'] or not obj['url'] or obj['source_id'] != sid:
                    continue
                obj['status'] = '來源元資料，內容未查證'
                obj['verification_state'] = '原始發布標題／非 AI 精選'
                obj['summary'] = None
                obj['first_seen_at'] = old_by_id.get(obj['id'], {}).get('first_seen_at') or tnow
                obj['last_seen_at'] = tnow
                if obj['id'] not in merged:
                    new_count += 1
                merged[obj['id']] = obj
        except Exception as exc:
            error = (type(exc).__name__ + ': ' + str(exc))[:160]
        finally:
            if src['publisher_id'] == 'arxiv':
                last_arxiv_time = start
        old = old_health.get(sid, {})
        health.append({
            'source_id':sid, 'publisher_id':src['publisher_id'], 'source':src['name'],
            'source_kind':src['kind'], 'category':src['category'],
            'ok':error is None, 'count':len(fresh), 'error':error,
            'last_attempt_at':tnow,
            'last_success_at':tnow if error is None else old.get('last_success_at'),
            'latency_ms':round((time.monotonic()-start)*1000),
            'evidence_url':src['evidence_url'],
        })

    lower = now - dt.timedelta(days=ttl_days)
    upper = now + dt.timedelta(days=2)
    cleaned = []
    for item in merged.values():
        date = parse_time(item.get('published_at') or item.get('first_seen_at'))
        if not date:
            continue
        published = dt.datetime.fromisoformat(date)
        if lower <= published <= upper:
            cleaned.append(item)
    cleaned.sort(key=lambda x:(x.get('published_at') or x.get('first_seen_at') or '', x['id']),reverse=True)
    cleaned = cleaned[:limit]
    # Important: count only *retained* first-seen records. Older RSS items beyond
    # the 45-day window may recur in each poll; they are not new intelligence.
    new_count = sum(x['id'] not in old_by_id for x in cleaned)
    meta = previous.get('meta',{})
    return {
        'meta': {
            'version':'0.3.4', 'mode':'official_metadata', 'generated_at':tnow,
            'last_attempt_at':tnow, 'last_success_at':tnow if success_count else meta.get('last_success_at'),
            'successful_sources':success_count,'source_count':len(sources),
            'status': 'healthy' if success_count==len(sources) else ('partial' if success_count else 'unavailable'),
            'new_items_in_run':new_count, 'item_count':len(cleaned),
            'retention_days':ttl_days, 'rights_scope':'descriptive_public_metadata_only',
            'note':'僅公開公告或研究的描述性元資料；不代表全文被查證、來源互為獨立證據，亦非 AI 精選。'
        },
        'items':cleaned,
        'sources':health,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default=str(BASE/'data/live_items.json'))
    ap.add_argument('--fixtures', default='', help='Offline tests ONLY; missing fixtures reported failed')
    ap.add_argument('--as-of', default='', help='Offline deterministic timestamp UTC ISO8601')
    args = ap.parse_args(argv)
    sources = checked_sources(read_json(BASE/'data/v034_sources.json',{}))
    output = Path(args.output)
    old = read_json(output, {'meta':{},'items':[],'sources':[]})
    now = dt.datetime.fromisoformat(args.as_of.replace('Z','+00:00')).astimezone(dt.timezone.utc) if args.as_of else utcnow()
    if args.fixtures:
        base = Path(args.fixtures)
        def loader(src):
            return parse_xml((base/(src['id']+'.xml')).read_bytes(),src,allow_empty=True)
        # Fixtures do not incur external API rates.
        def no_pause(_): pass
        result = collect(sources,old,loader,now=now,pause=no_pause)
    else:
        result = collect(sources,old,fetch_metadata,now=now)
    atomic_json(output,result)
    print(json.dumps(result['meta'],ensure_ascii=False))
    for h in result['sources']:
        print(f"{h['source_id']:20} {str(h['ok']):5} {h['count']:2} {h['error'] or '-'}")
    # Partial failure remains visible; don't fabricate fresh success or drop last good metadata.
    if result['meta']['successful_sources']==0:
        print('::warning::All metadata sources failed. Historical records retained; no current news verified.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())

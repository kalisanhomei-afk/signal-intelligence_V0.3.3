#!/usr/bin/env python3
"""V0.3 deterministic offline acceptance tests; network access not required."""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh import parse_xml, normalize_url, parse_time, run_job, write_json, main

P = Path(__file__).resolve().parents[1]
F = P / 'tests/fixtures'
UTC = dt.timezone.utc
SOURCE_A = {'id': 'test-media', 'name': '測試媒體', 'category': '產業', 'kind': 'media', 'limit': 12}
SOURCE_B = {'id': 'test-science', 'name': '測試論文', 'category': '知識', 'kind': 'research', 'limit': 12}

# Parse both formats, normalize tracking parameters, reject invalid links and DTD.
a = parse_xml((F/'example-rss.xml').read_bytes(), SOURCE_A)
b = parse_xml((F/'example-atom.xml').read_bytes(), SOURCE_B)
assert len(a) == 2 and len(b) == 2
assert a[0]['title'].startswith('TEST ONLY')
assert a[0]['url'] == 'https://example.org/tech/research?id=5'
assert a[0]['published_at'] == '2026-11-05T06:10:00+00:00'
assert b[0]['url'] == 'https://example.org/robot/1'
assert parse_time('2026-11-05T22:01:00+08:00') == '2026-11-05T14:01:00+00:00'
assert normalize_url('javascript:alert(1)') == ''
assert normalize_url('https://name:pass@example.org/') == ''
try:
    parse_xml(b'<!DOCTYPE foo [ <!ENTITY x "abc"> ]><rss></rss>', SOURCE_A)
except ValueError:
    pass
else:
    raise AssertionError('DTD must be rejected')

now = dt.datetime(2026, 11, 5, 8, 0, tzinfo=UTC)
sources = [SOURCE_A, SOURCE_B]
def good_loader(src):
    return a if src['id'] == SOURCE_A['id'] else b
first = run_job(sources=sources, previous={'items': []}, now=now, loader=good_loader)
assert first['meta']['successful_sources'] == 2
assert first['meta']['new_items_in_run'] == 4
assert len(first['items']) == 4
assert first['meta']['all_sources_healthy']
assert all(item['status'] == '未審核標題' and item['summary'] is None for item in first['items'])

second = run_job(sources=sources, previous=first, now=now+dt.timedelta(hours=12), loader=good_loader)
assert second['meta']['new_items_in_run'] == 0
assert first['items'][0]['first_seen_at'] == second['items'][0]['first_seen_at']

def partial(src):
    if src['id'] == SOURCE_B['id']:
        raise TimeoutError('simulated unreachable source')
    return a
partial_result = run_job(sources=sources, previous=second, now=now+dt.timedelta(days=1), loader=partial)
assert partial_result['meta']['successful_sources'] == 1
assert len(partial_result['items']) == 4  # fallback news retained
assert partial_result['sources'][1]['ok'] is False
assert partial_result['sources'][1]['last_success_at'] == second['sources'][1]['last_success_at']

all_failed = run_job(sources=sources, previous=second, now=now+dt.timedelta(days=1), loader=lambda x: (_ for _ in ()).throw(ConnectionError('offline')))
assert all_failed['meta']['successful_sources'] == 0
assert all_failed['meta']['last_success_at'] == second['meta']['last_success_at']
assert len(all_failed['items']) == 4
stale = run_job(sources=sources, previous=all_failed, now=now+dt.timedelta(days=50), loader=lambda x: (_ for _ in ()).throw(ConnectionError('offline')))
assert len(stale['items']) == 0

# Full CLI offline simulation with source inventory; missing fixtures are reported as failed,
# not quietly treated as successful. Output is isolated from production data.
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    test_feed = folder/'data.json'
    fixture_dir = folder/'fixtures'
    fixture_dir.mkdir()
    (fixture_dir/'fed-monetary.xml').write_bytes((F/'example-rss.xml').read_bytes())
    ret = main(['--fixture-dir',str(fixture_dir),'--output',str(test_feed),'--as-of','2026-11-05T08:00:00+00:00'])
    obj = json.loads(test_feed.read_text(encoding='utf-8'))
    assert ret == 0
    assert obj['meta']['successful_sources'] == 1
    assert len(obj['sources']) == len(json.loads((P/'data/sources.json').read_text())['sources'])
    assert obj['meta']['item_count'] == 2
    assert obj['sources'][0]['ok']
    assert all(not x['ok'] for x in obj['sources'][1:])

# Editorial layer unchanged and dates are not silently treated as current news.
feed = json.loads((P/'data/feed.json').read_text(encoding='utf-8'))
assert len({x['id'] for x in feed['stories']}) == len(feed['stories'])
assert len({x['id'] for x in feed['events']}) == len(feed['events'])
assert any(x['id']=='fomc-20261210' and x['start']=='2026-12-10T03:00:00+08:00' for x in feed['events'])
assert all(x['date'] <= '2026-11-05' for x in feed['stories'])
print('PASS: RSS & Atom, URL canonicalization, 45-day retention, failures, health timestamps, fixture CLI and editorial separation.')

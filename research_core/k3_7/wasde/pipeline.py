#!/usr/bin/env python3
"""Limited official WASDE vintage intake, Python 3.10+ standard library only."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
PILOT_YEARS = (2016, 2020, 2022)
ARCHIVE_URL = 'https://www.usda.gov/historical-wasde-report-data-3'
HOSTS = {'www.usda.gov', 'usda.gov', 'usda.azureedge.us'}
MAX_BYTES = 40 * 1024 * 1024
MAX_UNPACKED = 100 * 1024 * 1024
TITLE = 'u.s. feed grain and corn supply and use'
# Attribute names and metric identifiers follow K3.4; explicit unit accompanies
# every observation (including the Bushels label used by USDA for yield).
METRICS = {
    'area planted': ('planted_area_million_acres', 'Million Acres'),
    'area harvested': ('harvested_area_million_acres', 'Million Acres'),
    'yield per harvested acre': ('yield_bushels_per_acre', 'Bushels'),
    'beginning stocks': ('beginning_stocks_million_bushels', 'Million Bushels'),
    'production': ('production_million_bushels', 'Million Bushels'),
    'imports': ('imports_million_bushels', 'Million Bushels'),
    'supply, total': ('total_supply_million_bushels', 'Million Bushels'),
    'feed and residual': ('feed_residual_million_bushels', 'Million Bushels'),
    'food, seed & industrial': ('food_seed_industrial_million_bushels', 'Million Bushels'),
    'ethanol & by-products': ('ethanol_million_bushels', 'Million Bushels'),
    'domestic, total': ('total_domestic_million_bushels', 'Million Bushels'),
    'exports': ('exports_million_bushels', 'Million Bushels'),
    'use, total': ('total_use_million_bushels', 'Million Bushels'),
    'ending stocks': ('ending_stocks_million_bushels', 'Million Bushels'),
}
REQUIRED_METRICS = {METRICS[k][0] for k in (
    'area harvested', 'yield per harvested acre', 'beginning stocks',
    'production', 'imports', 'domestic, total', 'exports', 'ending stocks')}
REQUIRED_COLUMNS = {'ReportTitle', 'Attribute', 'Commodity', 'Region',
                    'MarketYear', 'Value', 'Unit', 'ReleaseDate', 'AnnualQuarterFlag'}
FIELDS = ['release_date', 'marketing_year', 'commodity', 'region', 'metric',
          'value', 'unit', 'projection_estimate_flag', 'source_url',
          'source_sha256', 'source_member', 'source_member_sha256',
          'retrieved_at_utc', 'published_at_utc', 'available_at_utc',
          'timestamp_quality', 'evidence_url', 'quality_status']


def clean(value: str) -> str:
    return ' '.join(value.strip().lower().replace('’', "'").split())


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def check_time(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError('Retrieval time must have an explicit UTC timezone')


def check_url(url: str) -> None:
    p = urlsplit(url)
    if (p.scheme != 'https' or p.hostname not in HOSTS or p.username or
            p.password or p.port not in (None, 443) or p.fragment):
        raise ValueError(f'Unapproved official-source URL: {url}')


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate BEFORE making a redirected request.
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class Download:
    raw: bytes
    source_url: str
    retrieved_at_utc: str
    requested_url: str

    def __post_init__(self):
        check_url(self.source_url)
        check_url(self.requested_url)
        check_time(self.retrieved_at_utc)
        if not self.raw or len(self.raw) > MAX_BYTES:
            raise ValueError('Empty or oversized source')


def download(url: str) -> Download:
    check_url(url)
    req = Request(url, headers={'User-Agent': 'SIGNAL-K37-WASDE-research/1.0',
                                'Accept-Encoding': 'identity'})
    with build_opener(OfficialRedirects()).open(req, timeout=25) as response:
        check_url(response.geturl())
        raw = response.read(MAX_BYTES + 1)
        return Download(raw, response.geturl(), utc_now(), url)


def save_download(item: Download, raw_dir: Path) -> dict:
    """Content-addressed bytes plus a new receipt for EVERY acquisition."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256(item.raw)
    path = raw_dir / f'{digest}.bin'
    if path.exists():
        if sha256(path.read_bytes()) != digest:
            raise ValueError('Existing raw cache hash mismatch')
    else:
        with path.open('xb') as stream:
            stream.write(item.raw)
    receipt = {'source_url': item.source_url, 'requested_url': item.requested_url,
               'source_sha256': digest, 'retrieved_at_utc': item.retrieved_at_utc,
               'raw_file': path.name, 'input_bytes': len(item.raw)}
    receipt_name = f'receipt-{uuid.uuid4().hex}.json'
    with (raw_dir / receipt_name).open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    return dict(receipt, receipt_file=receipt_name)


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)


def discover(raw: bytes, page_url: str) -> list[dict]:
    """Use link targets actually present in the archive, never guessed files."""
    check_url(page_url)
    parser = Anchors()
    parser.feed(raw.decode('utf-8-sig'))
    found = {}
    for href in parser.links:
        url = urljoin(page_url, href)
        try:
            check_url(url)
        except ValueError:
            continue
        name = PurePosixPath(urlsplit(url).path).name
        if re.fullmatch(r'oce-wasde-report-data-2022-(?:0[1-9]|1[0-2])(?:-V\d+)?\.csv', name, re.I):
            found[url] = {'url': url, 'kind': 'monthly_csv',
                          'months': [re.search(r'2022-\d{2}', name).group()]}
        elif name.lower() == 'oce-wasde-report-data-2016-01-to-2020-12.zip':
            found[url] = {'url': url, 'kind': 'historical_zip',
                          'months': [f'{y}-{m:02}' for y in (2016, 2020) for m in range(1, 13)]}
    return [found[k] for k in sorted(found)]


def csv_members(raw: bytes, kind: str):
    if kind == 'monthly_csv':
        yield '', raw
        return
    if kind != 'historical_zip':
        raise ValueError(f'Unsupported source format: {kind}')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if len(members) > 100 or sum(m.file_size for m in members) > MAX_UNPACKED:
            raise ValueError('ZIP exceeds member/expanded-size limit')
        names = [m.filename for m in members]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP member names')
        csv_files = [m for m in members if not m.is_dir() and m.filename.lower().endswith('.csv')]
        if not csv_files:
            raise ValueError('ZIP has no CSV members')
        for member in sorted(csv_files, key=lambda m: m.filename):
            path = PurePosixPath(member.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in member.filename:
                raise ValueError('Unsafe ZIP member name')
            if member.flag_bits & 1:
                raise ValueError('Encrypted ZIP member')
            # Read in memory; never extract paths to the filesystem.
            yield member.filename, archive.read(member)


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f'Unsupported source release date: {value}')


def market_year(value: str) -> str:
    m = re.fullmatch(r'(20\d{2})/(\d{2}|20\d{2})', value.strip())
    if not m or int(m[2][-2:]) != (int(m[1]) + 1) % 100:
        raise ValueError(f'Invalid marketing year: {value}')
    return f'{m[1]}/{m[2][-2:]}'


def number(value: str) -> Decimal:
    value = value.strip()
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?', value):
        raise ValueError(f'Missing, negative, or unsupported numeric cell: {value}')
    try:
        result = Decimal(value.replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError('Invalid numeric cell') from exc
    if not result.is_finite():
        raise ValueError('Non-finite numeric cell')
    return result


def balance_audit(values: dict[str, Decimal]) -> dict:
    missing = sorted(REQUIRED_METRICS - values.keys())
    checks = {}
    def check(label, inputs, calculation, tolerance=Decimal('3')):
        if all(k in values for k in inputs):
            residual = calculation(*(values[k] for k in inputs))
            checks[label] = {'residual': str(residual), 'tolerance': str(tolerance),
                             'status': 'PASS' if abs(residual) <= tolerance else 'FAIL'}
    check('supply_use', ['beginning_stocks_million_bushels', 'production_million_bushels',
                        'imports_million_bushels', 'total_domestic_million_bushels',
                        'exports_million_bushels', 'ending_stocks_million_bushels'],
          lambda b, p, i, d, x, e: b + p + i - d - x - e)
    check('reported_total_supply', ['beginning_stocks_million_bushels', 'production_million_bushels',
                                   'imports_million_bushels', 'total_supply_million_bushels'],
          lambda b, p, i, s: b + p + i - s)
    check('reported_total_use', ['total_domestic_million_bushels', 'exports_million_bushels',
                                'total_use_million_bushels'], lambda d, x, u: d + x - u)
    check('domestic_components', ['feed_residual_million_bushels', 'food_seed_industrial_million_bushels',
                                  'total_domestic_million_bushels'], lambda f, i, d: f + i - d)
    area = values.get('harvested_area_million_acres')
    yield_ = values.get('yield_bushels_per_acre')
    if area is not None and yield_ is not None:
        # USDA area/yield rounded to tenths, production to million bushels.
        tolerance = yield_ * Decimal('.05') + area * Decimal('.05') + Decimal('.5025')
        check('area_yield_production', ['harvested_area_million_acres', 'yield_bushels_per_acre',
                                       'production_million_bushels'], lambda a, y, p: a * y - p, tolerance)
    status = ('BALANCE_MISMATCH' if any(c['status'] == 'FAIL' for c in checks.values())
              else 'INCOMPLETE_METRICS' if missing else 'PASS')
    return {'status': status, 'missing_metrics': missing, 'checks': checks}


def parse_csv(raw: bytes, item: Download, *, member: str = '',
              expected_months: list[str]) -> tuple[list[dict], list[dict], set[str]]:
    """Retain every source release and marketing year, estimates included.

    Reject a conflicting/invalid cohort as a whole, retaining its audit. A source
    with a different column layout fails closed rather than guessing positions.
    """
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    columns = reader.fieldnames or []
    if len(columns) != len(set(columns)) or not REQUIRED_COLUMNS <= set(columns):
        raise ValueError(f'Unsupported CSV schema: missing {sorted(REQUIRED_COLUMNS-set(columns))}')
    groups = defaultdict(dict)
    errors = defaultdict(list)
    unselected = defaultdict(Counter)
    observed = set()
    for lineno, row in enumerate(reader, 2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f'Malformed CSV row at line {lineno}')
        release = parse_date(row['ReleaseDate'])
        if release.year not in PILOT_YEARS:
            continue  # consolidated file contains years outside the pilot
        month = release.strftime('%Y-%m')
        if month not in expected_months:
            raise ValueError(f'Source release outside discovered file range: {release}')
        observed.add(str(release))
        if clean(row['ReportTitle']) != TITLE or clean(row['Commodity']) != 'corn' or clean(row['Region']) not in ('united states', 'us', 'u.s.'):
            continue
        if clean(row['AnnualQuarterFlag']) != 'annual':
            continue
        year = market_year(row['MarketYear'])
        key = (str(release), year)
        attr = clean(row['Attribute'])
        if attr not in METRICS:
            # The table includes other published attributes (e.g. farm prices).
            # Report their exact labels; missing required metrics still fail the
            # completeness gate. Never guess aliases for an unfamiliar label.
            unselected[key][row['Attribute']] += 1
            continue
        metric, unit = METRICS[attr]
        try:
            if clean(row['Unit']) != clean(unit):
                raise ValueError(f'UNIT_MISMATCH: {row["Unit"]} expected {unit}')
            val = number(row['Value'])
            if metric in groups[key]:
                raise ValueError(f'DUPLICATE_METRIC: {metric}')
            groups[key][metric] = (val, unit, row.get('ProjEstFlag', '').strip())
        except ValueError as exc:
            errors[key].append({'line': lineno, 'reason': str(exc), 'metric': metric})
    rows, audit = [], []
    provenance = dict(source_url=item.source_url, source_sha256=sha256(item.raw),
                      source_member=member, source_member_sha256=sha256(raw) if member else '',
                      retrieved_at_utc=item.retrieved_at_utc, published_at_utc='',
                      available_at_utc='', timestamp_quality='UNKNOWN', evidence_url='')
    for key in sorted(groups.keys() | errors.keys() | unselected.keys()):
        release, year = key
        vals = groups[key]
        check = balance_audit({k: v[0] for k, v in vals.items()})
        status = 'PARSE_ERROR' if errors[key] else check['status']
        audit.append(dict(release_date=release, marketing_year=year, source_member=member,
                          status=status, errors=errors[key], unselected_attributes=dict(unselected[key]),
                          **{k:v for k,v in check.items() if k != 'status'}))
        if status in ('PARSE_ERROR', 'BALANCE_MISMATCH'):
            continue
        for metric, (value, unit, flag) in sorted(vals.items()):
            rows.append(dict(release_date=release, marketing_year=year, commodity='Corn',
                             region='United States', metric=metric, value=str(value), unit=unit,
                             projection_estimate_flag=flag, **provenance,
                             quality_status='PIT_UNVERIFIED' if status == 'PASS' else status))
    return rows, audit, observed


def parse_source(item: Download, spec: dict):
    rows, audits, observed = [], [], set()
    seen = set()
    for member, raw in csv_members(item.raw, spec['kind']):
        parsed, checks, dates = parse_csv(raw, item, member=member, expected_months=spec['months'])
        for row in parsed:
            key = (row['release_date'], row['marketing_year'], row['metric'])
            if key in seen:
                raise ValueError(f'Duplicate cohort/metric across ZIP members: {key}')
            seen.add(key)
        rows.extend(parsed)
        audits.extend(checks)
        observed.update(dates)
    return rows, audits, observed


def source_error(exc: Exception) -> str:
    # HTTP 404 proves a missing RESOURCE, not a month with no issued report.
    return 'MISSING_SOURCE_RESOURCE' if isinstance(exc, HTTPError) and exc.code == 404 else 'SOURCE_UNAVAILABLE'


def collect(*, fetch=download, raw_dir: Path, archive_url: str = ARCHIVE_URL) -> tuple[list[dict], dict]:
    manifest = {'schema_version': 'K3.7-WASDE-1', 'mode': 'ONLINE', 'run_started_at_utc': utc_now(),
                'pilot_years': list(PILOT_YEARS), 'archive': {}, 'sources': [], 'cohorts': [],
                'timestamp_policy': 'UNKNOWN: no verified historical publication or availability evidence',
                'limitations': ['USDA consolidated vintages, not proof of original-file historical availability',
                                'No imputation; individual WASDE publications remain the official data of record']}
    rows = []
    try:
        archive = fetch(archive_url)
        manifest['archive'] = dict(save_download(archive, raw_dir), status='OK')
        specs = discover(archive.raw, archive.source_url)
        if not specs:
            raise ValueError('NO_SUPPORTED_PILOT_LINKS: inspect archive HTML/format before declaring releases missing')
    except (HTTPError, URLError, OSError, ValueError, UnicodeError) as exc:
        status = 'PARSE_ERROR' if 'raw_file' in manifest['archive'] else source_error(exc)
        manifest['archive'].update(requested_url=archive_url, status=status,
                                   attempted_at_utc=utc_now(), error=f'{type(exc).__name__}: {exc}')
        specs = []
    for spec in specs:
        entry = dict(spec, status='SOURCE_UNAVAILABLE', attempted_at_utc=utc_now(), observed_release_dates=[])
        manifest['sources'].append(entry)
        try:
            item = fetch(spec['url'])
            entry.update(save_download(item, raw_dir))
        except (HTTPError, URLError, OSError, ValueError) as exc:
            entry.update(status=source_error(exc), error=f'{type(exc).__name__}: {exc}')
            continue
        try:
            parsed, audits, observed = parse_source(item, spec)
            entry.update(status='PARSED' if parsed else 'NO_ACCEPTED_ROWS',
                         observed_release_dates=sorted(observed), records=len(parsed))
            rows.extend(parsed)
            manifest['cohorts'].extend(dict(a, source_sha256=entry['source_sha256'],
                                             source_url=item.source_url) for a in audits)
        except (ValueError, UnicodeError, zipfile.BadZipFile, RuntimeError, OSError) as exc:
            entry.update(status='PARSE_ERROR', error=f'{type(exc).__name__}: {exc}')
    # Preserve colliding source versions by SHA. Flag collisions for review.
    conflicts = defaultdict(set)
    for r in rows:
        conflicts[(r['release_date'], r['marketing_year'], r['metric'])].add((r['source_sha256'], r['value']))
    manifest['source_version_conflicts'] = [dict(release_date=k[0], marketing_year=k[1], metric=k[2],
                                                versions=sorted(v)) for k,v in sorted(conflicts.items()) if len(v)>1]
    if manifest['source_version_conflicts']:
        for r in rows:
            if len(conflicts[(r['release_date'], r['marketing_year'], r['metric'])]) > 1:
                r['quality_status'] = 'SOURCE_VERSION_CONFLICT'
    coverage = []
    for year in PILOT_YEARS:
        for month in range(1, 13):
            ym = f'{year}-{month:02}'
            candidates = [e for e in manifest['sources'] if ym in e['months']]
            observed = sorted({d for e in candidates for d in e['observed_release_dates'] if d.startswith(ym)})
            accepted = [r for r in rows if r['release_date'].startswith(ym)]
            cohorts = [c for c in manifest['cohorts'] if c['release_date'].startswith(ym)]
            if manifest['archive']['status'] == 'PARSE_ERROR':
                status = 'PARSE_ERROR'
            elif manifest['archive']['status'] != 'OK':
                status = 'SOURCE_UNAVAILABLE'
            elif not candidates:
                status = 'MISSING_OFFICIAL_RELEASE'
            elif any(e['status'] in ('SOURCE_UNAVAILABLE', 'MISSING_SOURCE_RESOURCE') for e in candidates):
                status = 'SOURCE_UNAVAILABLE'
            elif any(e['status'] == 'PARSE_ERROR' for e in candidates):
                status = 'PARSE_ERROR'
            elif not observed:
                status = 'MISSING_OFFICIAL_RELEASE'
            elif not cohorts or any(c['status'] != 'PASS' for c in cohorts):
                status = 'INCOMPLETE_OR_REJECTED_COHORT'
            else:
                status = 'OBSERVED'
            coverage.append(dict(month=ym, status=status, observed_release_dates=observed,
                                 records=len(accepted), note='MISSING means not observed in inspected sources; never proof no report was issued'))
    manifest.update(coverage=coverage, records=len(rows),
                    coverage_counts=dict(Counter(c['status'] for c in coverage)),
                    verified_pit_records=0, run_completed_at_utc=utc_now())
    manifest['status'] = ('COLLECTED_PIT_UNVERIFIED' if all(c['status']=='OBSERVED' for c in coverage)
                          and not manifest['source_version_conflicts'] else 'PARTIAL_OR_BLOCKED')
    rows.sort(key=lambda r: tuple(r[k] for k in ('release_date', 'marketing_year', 'metric', 'source_sha256')))
    return rows, manifest


def write_outputs(output: Path, rows: list[dict], manifest: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError('Output directory must be empty; use a new run directory to preserve vintages')
    with (output / 'wasde_vintages.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with (output / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')


def replay(manifest_path: Path, raw_dir: Path) -> tuple[list[dict], dict]:
    """Re-run parsing offline with original download receipts, not a new retrieval."""
    original = json.loads(manifest_path.read_text(encoding='utf-8'))
    items = {}
    for entry in [original['archive'], *original['sources']]:
        if 'raw_file' not in entry:
            continue
        name = entry['raw_file']
        if name != f"{entry['source_sha256']}.bin" or not re.fullmatch(r'[0-9a-f]{64}\.bin', name):
            raise ValueError('Invalid content-addressed cache path')
        raw = (raw_dir / name).read_bytes()
        if sha256(raw) != entry['source_sha256']:
            raise ValueError('Replay source SHA-256 mismatch')
        item = Download(raw, entry['source_url'], entry['retrieved_at_utc'], entry['requested_url'])
        items[entry['requested_url']] = item
    def offline_fetch(url):
        if url not in items:
            raise URLError('Source was not acquired in original run; offline replay never downloads')
        return items[url]
    # A temporary receipt directory is unnecessary: immutable cache bytes already
    # exist, but collect writes acquisition receipts. Replay uses an isolated temp.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rows, result = collect(fetch=offline_fetch, raw_dir=Path(td),
                               archive_url=original['archive']['requested_url'])
    # Keep regenerated validation results. Retain original receipts rather than
    # references to temporary files created while checking the offline cache.
    for entry in [result['archive'], *result['sources']]:
        match = next((e for e in [original['archive'], *original['sources']]
                      if e.get('requested_url') == entry.get('requested_url')), None)
        if match and 'receipt_file' in match:
            entry['receipt_file'] = match['receipt_file']
    result.update(mode='OFFLINE_REPLAY', replay_of_manifest_sha256=sha256(manifest_path.read_bytes()),
                  original_run_started_at_utc=original['run_started_at_utc'])
    return rows, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'out')
    parser.add_argument('--raw-dir', type=Path, default=HERE/'raw')
    parser.add_argument('--replay', type=Path, help='Manifest to replay without network')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output directory is not empty; choose a new directory')
    rows, manifest = (replay(args.replay, args.raw_dir) if args.replay else collect(raw_dir=args.raw_dir))
    write_outputs(args.output, rows, manifest)
    print(json.dumps({k:manifest[k] for k in ('status', 'records', 'coverage_counts', 'verified_pit_records')}, sort_keys=True))
    return 0 if manifest['status'] == 'COLLECTED_PIT_UNVERIFIED' else 2


if __name__ == '__main__':
    raise SystemExit(main())

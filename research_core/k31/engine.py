"""NASS corn condition leading signals linked to K3 WASDE official-vintage forecasts.

No hidden network access, API charges, trained model, calibrated probability, or trades.

All dates are *retrospective public availability*; a conservative next-day
12:00 UTC proxy is used because the manual record does NOT certify exact
historical release hour. This is *not* actual historical SIGNAL collection.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
import json
import re

from research_core.contracts import ContractError, instant
from research_core.k3.engine import load_fixture as load_k3_fixture, extract_current_projection, ordered_releases

CONDITION_FIELDS = ('very_poor', 'poor', 'fair', 'good', 'excellent')
SOURCE_PATH = Path(__file__).parent / 'fixtures' / 'nass_corn_condition_2026_selected.json'
MODE = 'RETROSPECTIVE_PUBLIC_RELEASE_REPLAY_NOT_HISTORICAL_SYSTEM_COLLECTION'


def load_source(path: Path | None = None) -> dict:
    return json.loads((path or SOURCE_PATH).read_text(encoding='utf-8'))


def _err(code: str, message: str):
    raise ContractError(code, message)


def validate_source(doc: dict) -> list[dict]:
    if doc.get('purpose') != 'RETROSPECTIVE_PUBLIC_RELEASE_REPLAY_ONLY':
        _err('K31_MODE', 'must explicitly declare retrospective public availability')
    if doc.get('series') != 'CORN_CONDITION_NASS_18_STATES_PCT':
        _err('K31_SERIES', 'unexpected series scope')
    if doc.get('data_status') != 'OFFICIAL_NASS_NUMBERS_MANUALLY_TRANSCRIBED_EXCERPTS_NOT_FULL_SOURCE_FILES':
        _err('K31_PROVENANCE', 'manually transcribed source must be declared')
    records = doc.get('records')
    if not isinstance(records, list) or not records:
        _err('K31_EMPTY', 'no source records')
    seen = set()
    result = []
    for rec in records:
        report_day = date.fromisoformat(rec['source_date'])
        week_day = date.fromisoformat(rec['week_ending'])
        proxy = instant(rec['available_at_proxy_utc'])
        expected = datetime.combine(report_day + timedelta(days=1), time(12), tzinfo=timezone.utc)
        if proxy != expected:
            _err('K31_PROXY', 'availability proxy must be next calendar day at 12:00 UTC')
        if not (week_day < report_day and (report_day - week_day).days <= 3):
            _err('K31_WEEK', 'observation ending is not a plausible week preceding release')
        parsed = urlsplit(rec['source_uri'])
        if (parsed.scheme != 'https' or parsed.netloc != 'esmis.nal.usda.gov' or
              not parsed.path.endswith('.txt') or not parsed.path.startswith('/sites/default/release-files/')):
            _err('K31_URL', 'only original USDA ESMIS plain-text report accepted')
        vals = [rec[k] for k in CONDITION_FIELDS]
        if any(type(v) is not int or v < 0 or v > 100 for v in vals) or sum(vals) != 100:
            _err('K31_PERCENT', 'condition categories must be integer percents summing to 100')
        row = rec['source_row']
        if not re.fullmatch(r'18 States\s*\.\.\.\.*:\s*\d+\s+\d+\s+\d+\s+\d+\s+\d+\s*', row):
            _err('K31_ROW_FORMAT', 'manual source row format is not precise')
        tail = row.partition(':')[2]
        if [int(t) for t in tail.split()] != vals:
            _err('K31_ROW_MISMATCH', 'transcribed category disagrees with source row')
        if rec['source_date'] in seen:
            _err('K31_DUPLICATE', 'duplicate official weekly edition')
        seen.add(rec['source_date'])
        val = dict(rec)
        val['good_excellent_pct'] = rec['good'] + rec['excellent']
        result.append(val)
    result.sort(key=lambda x: instant(x['available_at_proxy_utc']))
    return result


def select_latest_pair(records: list[dict], as_of: str) -> list[dict]:
    cutoff = instant(as_of)
    elig = [r for r in records if instant(r['available_at_proxy_utc']) <= cutoff]
    return elig[-2:]


def _sign(value: Decimal) -> str:
    return 'UP' if value > 0 else 'DOWN' if value < 0 else 'FLAT'


def assemble_study(doc: dict | None = None, wasde_doc: dict | None = None) -> dict:
    doc = deepcopy(doc if doc is not None else load_source())
    wasde_doc = deepcopy(wasde_doc if wasde_doc is not None else load_k3_fixture())
    signals = validate_source(doc)
    states = ordered_releases(wasde_doc)
    sources = sorted(wasde_doc['sources'], key=lambda x: instant(x['published_at']))
    if len(states) != len(sources):
        _err('K31_WASDE_ALIGNMENT', 'K3 vintage state mismatch')
    wasde = []
    for rec, state in zip(sources, states):
        if state['publication'] != rec['published_at']:
            _err('K31_WASDE_ALIGNMENT', 'K3 release order mismatch')
        yields = extract_current_projection(rec)
        wasde.append((state, yields['yield_per_acre']))
    trials = []
    for (origin, old_yield), (target, next_yield) in zip(wasde[:-1], wasde[1:]):
        origin_at, target_at = instant(origin['publication']), instant(target['publication'])
        if not origin_at < target_at:
            _err('K31_TARGET_ORDER', 'targets must be in future of forecast origin')
        usable = select_latest_pair(signals, origin['publication'])
        if not usable:
            _err('K31_NO_LEAD', 'no NASS report available at forecast origin')
        for item in usable:
            if instant(item['available_at_proxy_utc']) > origin_at:
                _err('K31_LEAK', 'post-origin signal entered forecast')
        signal_delta = None
        signal_prediction = 'ABSTAIN_INSUFFICIENT_PRIOR_SIGNAL'
        if len(usable) == 2:
            signal_delta = usable[-1]['good_excellent_pct'] - usable[-2]['good_excellent_pct']
            signal_prediction = _sign(Decimal(signal_delta))
        actual_delta = next_yield - old_yield
        actual_sign = _sign(actual_delta)
        comparable = signal_delta is not None and signal_prediction != 'FLAT' and actual_sign != 'FLAT'
        trials.append({
            'forecast_origin': origin['publication'], 'target_release': target['publication'],
            'source_edition_dates': [r['source_date'] for r in usable],
            'source_urls': [r['source_uri'] for r in usable],
            'signal_good_excellent_pct': usable[-1]['good_excellent_pct'],
            'signal_selected_edition_change_pp': signal_delta,
            'mechanical_hypothesis_next_yield_revision': signal_prediction,
            'current_wasde_yield_bushels_per_acre': str(old_yield),
            'next_wasde_yield_estimate_bushels_per_acre': str(next_yield),
            'official_yield_revision_bushels_per_acre': str(actual_delta),
            'official_yield_revision_direction': actual_sign,
            'direction_correct_if_testable': signal_prediction == actual_sign if comparable else None,
            'persistence_abs_error_bu_per_acre': str(abs(actual_delta)),
            'not_a_trained_price_model': True,
            'not_a_realized_yield': True,
        })
    comparisons = [x for x in trials if x['direction_correct_if_testable'] is not None]
    if not comparisons:
        _err('K31_NO_COMPARABLE_PAIR', 'not enough comparable signal pairs')
    # Last K3 official vintage has an eligible NASS observation but no NEXT
    # vintage in the frozen K3 fixture. Do not silently import newer targets.
    last_k3 = wasde[-1][0]
    pending = select_latest_pair(signals, last_k3['publication'])
    last_unscored = None
    if len(pending) == 2:
        d = pending[-1]['good_excellent_pct'] - pending[-2]['good_excellent_pct']
        last_unscored = {
            'as_of': last_k3['publication'],
            'source_date': pending[-1]['source_date'],
            'last_good_excellent_pct': pending[-1]['good_excellent_pct'],
            'selected_edition_delta_pp': d,
            'hypothesis_direction': _sign(Decimal(d)),
            'evaluation_status': 'NOT_SCORED_NEXT_WASDE_NOT_IN_FROZEN_K3_DATASET',
        }
    frozen = {
        'schema_version': 'signal-k31-leading-indicator-study-v1',
        'all_lead_observations': [
            {'source_date':r['source_date'], 'week_ending':r['week_ending'],
             'available_at_proxy_utc':r['available_at_proxy_utc'],
             'good_excellent_pct':r['good_excellent_pct'], 'source_uri':r['source_uri']}
            for r in signals],
        'latest_unscored_origin': last_unscored,
        'mode': MODE,
        'feature_scope': 'NASS corn good+excellent, 18 selected states',
        'forecast_target': 'next WASDE estimate of 2026/27 US corn yield (NOT realized yield)',
        'strategy': 'sign of change between the two selected NASS condition release editions',
        'no_parameter_fitting': True,
        'trials': trials,
        'comparison': {
            'target_count': len(trials),
            'direction_tested_count': len(comparisons),
            'direction_correct_count': sum(int(x['direction_correct_if_testable']) for x in comparisons),
            'baseline': 'PERSISTENCE_OF_CURRENT_WASDE_YIELD_ESTIMATE',
            'baseline_mae_bu_per_acre': str(sum(Decimal(t['persistence_abs_error_bu_per_acre']) for t in trials) / len(trials)),
            'forecast_skill_established': False,
            'price_forecast_established': False,
            'model_outperforms_baseline': None,
            'why_not_comparable': 'Direction-only hypothesis has no numerical yield estimate; it cannot be judged by MAE against a numerical persistence forecast.'
        },
        'provenance': {
            'lead': 'USDA NASS weekly Crop Progress ESMIS manual condition-row transcription',
            'target': 'K3 USDA WASDE ESMIS manually transcribed contemporaneous estimates',
            'cutoff_policy': 'Conservative next-day 12:00 UTC availability PROXY; NOT exact historical release hour',
            'weekly_sample_policy': 'Selected editions only, NOT consecutive weekly change',
            'replay': 'RETROSPECTIVE public availability; NOT SIGNAL recorded historical acquisition'
        },
        'publication_allowed': False, 'trade_allowed': False,
        'limitations': [
            'Only one marketing year and two evaluated directional predictions: no validated predictive power.',
            '18 selected states represent prior-year 91% planted acres, not nationwide census.',
            'Corn condition is not equivalent to the USDA yield forecast and may have seasonality.',
            'Later WASDE estimate is a revised forecast, not realized harvest and not futures price.',
            'No market-consensus, CME price, timing, cost, or investable performance analysis.'
        ]
    }
    return frozen

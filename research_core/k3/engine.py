"""K3 official WASDE archive *release-replay*, NOT a futures/price forecaster.

Source values: individually transcribed from the named USDA ESMIS public TXT
release, US Feed Grain and Corn Supply and Use / CORN / rightmost 2026/27 Proj.
source excerpt. K3 does not claim a certified fully automated ingestion.

Critical: `public_replay` reconstructs public-at-release availability RETROSPECTIVELY;
`system_replay` requires SIGNAL's actual archival retrieval time, not a backdated time.
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from dataclasses import asdict
from pathlib import Path
import json, re

from research_core.contracts import ContractError, SourceSnapshot, Observation, instant, number
from research_core.asof_guard import select_asof, TimePolicy
from research_core.stockflow import REQUIRED, check_balance

SCOPE='US_CORN_WASDE_MY2026_27'
UNIT='million_bushels'
MEASURE='USDA_WASDE_US_CORN_BALANCE_RELEASE_ESTIMATE'
LABELS={
 'beginning_stocks':'Beginning Stocks',
 'production':'Production',
 'imports':'Imports',
 'supply_total':'Supply, Total',
 'domestic_use':'Domestic, Total',
 'exports':'Exports',
 'total_use':'Use, Total',
 'ending_stocks':'Ending Stocks',
 'harvested_area':'Area Harvested',
 'yield_per_acre':'Yield per Harvested Acre',
}
FLOW_SIGN={'beginning_stocks':1,'production':1,'imports':1,'domestic_use':-1,'exports':-1}
NUM=r'(?:\d+(?:\.\d+)?\*?)'


def _parse_row(excerpt: str, label: str) -> Decimal:
    candidates=[]
    for line in excerpt.splitlines():
        m=re.match(r'^\s*'+re.escape(label)+r'\s{2,}(.*?)\s*$',line)
        if not m: continue
        tail=m.group(1)
        toks=tail.split()
        if len(toks)!=4 or any(re.fullmatch(NUM,t) is None for t in toks):
            raise ContractError('K3_ROW_AMBIGUOUS',f'{label}: must be four numeric historical/current columns')
        candidates.append(Decimal(toks[3].removesuffix('*')))
    if len(candidates)!=1:
        raise ContractError('K3_ROW_MISSING_OR_DUPLICATE',f'{label}: found {len(candidates)} rows')
    return candidates[0]


def extract_current_projection(record:dict)->dict[str,Decimal]:
    if record['commodity']!='CORN' or record['geography']!='US' or record['marketing_year']!='2026/27':
        raise ContractError('K3_SCOPE_MISMATCH','only USDA US corn 2026/27 release projection supported')
    excerpt=record['excerpt']
    if 'U.S. Feed Grain and Corn Supply and Use' not in excerpt or '\nCORN\n' not in excerpt or '2026/27 Proj.' not in excerpt:
        raise ContractError('K3_SOURCE_STRUCTURE','missing expected report/table/scope labels')
    values={k:_parse_row(excerpt,label) for k,label in LABELS.items()}
    if any(v<0 for v in values.values()):
        raise ContractError('K3_NEGATIVE_VALUE','negative quantities not supported for this table')
    if sum((v for v in (values['beginning_stocks'],values['production'],values['imports'])),Decimal(0))!=values['supply_total']:
        raise ContractError('K3_SUPPLY_TOTAL','reported supply disagrees with component balance')
    if values['domestic_use']+values['exports']!=values['total_use']:
        raise ContractError('K3_USE_TOTAL','reported use disagrees with components')
    if values['supply_total']-values['total_use']!=values['ending_stocks']:
        raise ContractError('K3_STOCKFLOW_BALANCE','reported ending stock disagrees with supply-use')
    return values


def build_k1_archive(doc:dict)->tuple[list[Observation],dict[str,SourceSnapshot]]:
    records=doc['sources']
    if not isinstance(records,list) or len(records)<2:
        raise ContractError('K3_TOO_FEW_VINTAGES','need at least two real release vintages')
    snapshots={}; obs=[]; dates=set(); seen_uris=set(); previous=None
    for record in sorted(records,key=lambda x:instant(x['published_at'])):
        stamp=instant(record['published_at']); retrieved=instant(record['retrieved_at'])
        if stamp>retrieved:raise ContractError('K3_INVALID_TIME_ORDER','retrieval predates publication')
        if record['release_date']!=stamp.date().isoformat():raise ContractError('K3_RELEASE_MISMATCH','date differs from publication clock')
        if record['release_date'] in dates or record['source_uri'] in seen_uris:
            raise ContractError('K3_DUPLICATE_RELEASE','repeated source vintage')
        if previous is not None and stamp<=previous:raise ContractError('K3_TIME_ORDER','publication times not increasing')
        previous=stamp
        dates.add(record['release_date']);seen_uris.add(record['source_uri'])
        if not record['source_uri'].startswith('https://esmis.nal.usda.gov/sites/default/release-files/') or not record['source_uri'].endswith('.txt'):
            raise ContractError('K3_SOURCE_INVALID','source must be original ESMIS TXT release')
        if record['excerpt_kind']!='MANUALLY_TRANSCRIBED_USDA_TXT_TABLE_ROWS_NOT_FULL_ORIGINAL_FILE':
            raise ContractError('K3_TRANSCRIPTION_STATUS','provenance not fully declared')
        values=extract_current_projection(record)
        vintage=f"USDA_WASDE_{record['release_date']}"
        source_id=f"K3_WASDE_{record['release_date']}"
        snapshots[source_id]=SourceSnapshot(
          snapshot_id=source_id,source_id='USDA_WASDE_ESMIS',source_uri=record['source_uri'],
          published_at=record['published_at'],retrieved_at=record['retrieved_at'],
          vintage_id=vintage,payload_sha256=sha256(record['excerpt'].encode('utf-8')).hexdigest(),
          rights_scope='USDA official publication, manually transcribed excerpt (not full file hash)',
          source_type='official_archive_manual_excerpt')
        for key in REQUIRED:
            obs.append(Observation(observation_id=f'{source_id}_{key}',series_id=key,
                value=str(values[key]),unit=UNIT,period='MY2026/27',frequency='marketing_year',
                available_at=record['published_at'],data_status='official_estimate',
                snapshot_id=source_id,vintage_id=vintage,commodity='corn',geography='US',
                measurement_basis=MEASURE))
        # Also verify exact same-release K1 stock-flow accounting.
        source_obs=[o for o in obs if o.snapshot_id==source_id]
        result=check_balance(source_obs)
        if not result.balanced:raise ContractError('K1_REAL_BALANCE','K1 stockflow contract failed')
    return obs,snapshots


def release_at(doc:dict, as_of:str, *, policy:str='public_replay')->dict|None:
    """No silently backdated system collection. `public_replay` is retrospective."""
    if policy not in ('public_replay','system_replay'):
        raise ContractError('K3_POLICY','policy must explicitly be public_replay or system_replay')
    observations,snapshots=build_k1_archive(doc)
    strict=(policy=='system_replay')
    selected=select_asof(observations,snapshots,as_of,
      policy=TimePolicy(require_local_retrieval=strict))
    if not selected:return None
    if set(selected)!=set(REQUIRED):raise ContractError('K3_INCOMPLETE','missing one of six components')
    result=check_balance(list(selected.values()))
    if not result.balanced:raise ContractError('K3_BAD_ASOF_BALANCE','mixed or unbalanced vintage')
    vintages={o.vintage_id for o in selected.values()}
    if len(vintages)!=1:raise ContractError('K3_MIXED_VINTAGE','multiple versions mixed at cutoff')
    s=next(iter(selected.values()))
    return {'as_of':as_of,'policy':policy,'publication':snapshots[s.snapshot_id].published_at,
        'vintage':s.vintage_id,'market_year':s.period,'scope':SCOPE,'unit':UNIT,
        'values':{k:selected[k].value for k in REQUIRED},
        'source_uri':snapshots[s.snapshot_id].source_uri}


def ordered_releases(doc:dict)->list[dict]:
    # Ordered by official release stamp, not historical collection date.
    output=[]
    for x in sorted(doc['sources'],key=lambda r:instant(r['published_at'])):
        state=release_at(doc,x['published_at'],policy='public_replay')
        if state['publication']!=x['published_at']:
            raise ContractError('K3_RELEASE_STATE','point-in-time replay returned wrong release')
        output.append(state)
    return output


def component_attribution(before:dict,after:dict)->dict:
    if before['scope']!=after['scope'] or before['unit']!=after['unit'] or before['market_year']!=after['market_year']:
        raise ContractError('K3_COMPARABILITY','different scopes or units')
    if instant(before['publication'])>=instant(after['publication']):
        raise ContractError('K3_REVISION_ORDER','revisions must compare old to new')
    b={k:number(v) for k,v in before['values'].items()}
    a={k:number(v) for k,v in after['values'].items()}
    contrib={k:(a[k]-b[k])*FLOW_SIGN[k] for k in FLOW_SIGN}
    actual=a['ending_stocks']-b['ending_stocks']
    if sum(contrib.values(),Decimal(0))!=actual:
        raise ContractError('K3_REVERSE_BALANCE','change not explained by accounting identity')
    return {'old_release':before['publication'],'new_release':after['publication'],
      'old_ending_stocks':str(b['ending_stocks']),'new_ending_stocks':str(a['ending_stocks']),
      'stock_revision':str(actual),'accounting_contributions':{k:str(v) for k,v in contrib.items()},
      'causal_identification':False,
      'interpretation':'Observed forecast REVISION decomposition, not attribution of biological/economic cause.'}


def persistence_benchmark(states:list[dict])->dict:
    """Predict next USDA release's estimate by current USDA estimate. No trading claim."""
    if len(states)<2:raise ContractError('K3_INSUFFICIENT_SAMPLES','need >=2 vintages')
    errors=[]; frozen=[]
    for before,after in zip(states[:-1],states[1:]):
        if before['market_year']!=after['market_year'] or before['scope']!=after['scope']:
            raise ContractError('K3_PERIOD_MISMATCH','forecast target differs')
        pred=number(before['values']['ending_stocks']); actual=number(after['values']['ending_stocks'])
        if instant(before['publication'])>=instant(after['publication']):
            raise ContractError('K3_LEAKAGE','forecast input postdates target announcement')
        err=actual-pred
        errors.append(abs(err))
        frozen.append({'frozen_as_of':before['publication'],'model':'PERSISTENCE_BENCHMARK',
            'target_release':after['publication'],'target_description':'next USDA WASDE 2026/27 US corn ending-stocks ESTIMATE, not realized actual stocks',
            'predicted':str(pred),'next_official_estimate':str(actual),'error_actual_minus_predicted':str(err),
            'verified_realized_inventory':False,'is_investment_signal':False})
    return {'baseline':'PERSISTENCE_BENCHMARK','data_type':'USDA_ARCHIVE_OFFICIAL_ESTIMATES',
       'replay_policy':'RETROSPECTIVE_PUBLIC_AVAILABILITY_NOT_ACTUAL_SYSTEM_HISTORY',
       'sample_count':len(errors),'mae_million_bushels':str(sum(errors,Decimal(0))/len(errors)),
       'forecasts':frozen,'model_has_outperformance_evidence':False,
       'caveat':'Only tests revisions of USDA estimates in a single crop year; not end-of-year realized stocks, futures prices, or tradable profit.'}


def load_fixture(path:Path|None=None)->dict:
    p=path or Path(__file__).parent/'fixtures'/'us_corn_wasde_2026_vintages.json'
    return json.loads(Path(p).read_text(encoding='utf-8'))

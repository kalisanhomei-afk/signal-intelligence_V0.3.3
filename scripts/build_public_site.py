#!/usr/bin/env python3
"""Generate allowlisted public SIGNAL site with approved descriptive metadata only.

No secrets, registry, unlicensed scraped titles, article text or user info.
The original editorial snapshot remains dated 2026-11-05.
"""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]

FILES={
    "index.html":"index.html",
    "source-console.html":"source-console.html",
    "data/feed.json":"data/feed.json",             # dated, manually curated 2026-11-05 snapshot
    "data/live_items.json":"data/discovered.json", # ONLY pre-reviewed official/CC0 descriptive metadata
    "data/intelligence.json":"data/intelligence.json", # AI title annotations never verified content
    "data/evidence_audit.json":"data/evidence_audit.json", # M0 provenance/gap report only
    "data/v032_candidates.json":"data/v032_candidates.json",
    "data/v032_live_probe.json":"data/v032_live_probe.json",
}


def build(output,source_root=BASE,*,strict=False):
    output=Path(output).resolve()
    source_root=Path(source_root).resolve()
    # Remove stale files so an accidental local file cannot leak into Pages.
    # Restrict destructive cleanup to output folders explicitly named for generated sites.
    if output.name not in ("_site", "public") or output == source_root:
        raise ValueError("output must be a generated _site or public directory")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True,exist_ok=True)
    for source_file, target_file in FILES.items():
        origin=source_root/source_file
        if not origin.is_file():
            raise FileNotFoundError(origin)
        target=output/target_file
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(origin,target)
    # V0.4.2 optional during legacy unit tests, mandatory in actual strict deployment.
    extra=source_root/'data/evidence_enriched.json'
    if extra.is_file():
        shutil.copyfile(extra,output/'data/evidence_enriched.json')
    elif strict:
        raise FileNotFoundError('V0.4.2 enrichment evidence is required for deployment')
    (output/'.nojekyll').write_text('',encoding='utf-8')
    # A public website MUST NOT contain personal research logs, audited license records,
    # scraped article text, private watchlists, or financial positions.
    probe=json.loads((output/'data/v032_live_probe.json').read_text(encoding='utf-8'))
    state=probe.get('meta',{}).get('state')
    if strict and state not in ('checked','not_run'):
        raise RuntimeError(f'unexpected probe state: {state}')
    live=json.loads((output/'data/discovered.json').read_text(encoding='utf-8'))
    if live.get('meta',{}).get('rights_scope')!='descriptive_public_metadata_only':
        raise RuntimeError('Unsafe metadata: rights scope not approved')
    # Revalidate source-id + publisher pair against the exact, reviewed feed allowlist.
    from collect_v034 import checked_sources
    config=json.loads((source_root/'data/v034_sources.json').read_text(encoding='utf-8')) if (source_root/'data/v034_sources.json').is_file() else json.loads((BASE/'data/v034_sources.json').read_text(encoding='utf-8'))
    approved={s['id']:s['publisher_id'] for s in checked_sources(config)}
    for item in live.get('items',[]):
        if (item.get('summary') is not None or item.get('source_id') not in approved
            or item.get('publisher_id')!=approved.get(item.get('source_id'))):
            raise RuntimeError('Unsafe metadata: unapproved source/publisher or article content in export')
    # Triage can only annotate public, approved source metadata; no unverifiable source injection.
    triage=json.loads((output/'data/intelligence.json').read_text(encoding='utf-8'))
    if triage.get('meta',{}).get('rights_scope')!='descriptive_public_metadata_only':
        raise RuntimeError('Unsafe triage scope')
    by_id={item['id']:item for item in live.get('items',[])}
    for x in triage.get('items',[]):
        source=by_id.get(x.get('id'))
        if (not source or source.get('url')!=x.get('url')
                or x.get('source_id')!=source.get('source_id')
                or x.get('verification_status')!='待人工核對'
                or x.get('independent_confirmation') is not False
                or x.get('review_required') is not True
                or x.get('analysis_mode') not in ('rules_only','ai_title_only')):
            raise RuntimeError('Unsafe triage record')
    evidence=json.loads((output/'data/evidence_audit.json').read_text(encoding='utf-8'))
    em=evidence.get('meta',{})
    if (em.get('rights_scope')!='descriptive_public_metadata_only'
            or em.get('verified_claims')!=0 or em.get('independently_confirmed_claims')!=0
            or em.get('importance_assessments')!=0):
        raise RuntimeError('Evidence data improperly promoted to verified facts')
    triage_by_id={x['id']:x for x in triage.get('items',[])}
    for e in evidence.get('items',[]):
        parent=triage_by_id.get(e.get('id'))
        if not parent or any(e.get(k)!=parent.get(k) for k in ('url','source_id','publisher_id','title')):
            raise RuntimeError('Evidence traceability mismatch')
        if (e.get('evidence_level')!='M0' or e.get('verification_status')!='未查證'
                or e.get('independent_confirmation_count')!=0
                or e.get('body_read') is not False
                or e.get('importance_assessed') is not False):
            raise RuntimeError('Evidence review status lacks a valid basis')
    augmented_path=output/'data/evidence_enriched.json'
    if augmented_path.is_file():
        aug=json.loads(augmented_path.read_text(encoding='utf-8'))
        am=aug.get('meta',{})
        if (am.get('rights_scope')!='descriptive_public_metadata_only'
                or am.get('status')!='primary_metadata_enrichment_only'
                or any(am.get(k)!=0 for k in ('verified_claims','independently_confirmed_claims',
                                               'read_bodies','importance_assessments'))):
            raise RuntimeError('Enrichment metadata falsely claims verification')
        m0_by_id={x['id']:x for x in evidence.get('items',[])}
        if len(aug.get('items',[]))!=len(m0_by_id):
            raise RuntimeError('Enrichment and evidence count mismatch')
        from urllib.parse import urlsplit
        seen=set()
        for a in aug['items']:
            parent=m0_by_id.get(a.get('id'))
            if (not parent or a['id'] in seen or any(a.get(k)!=parent.get(k)
                for k in ('fingerprint','url','title','publisher_id','source_id','published_at'))):
                raise RuntimeError('Enrichment provenance mismatch')
            seen.add(a['id'])
            if (a.get('verification_status')!='未查證'
                or a.get('body_read') is not False
                or a.get('original_document_verified') is not False
                or a.get('peer_review_confirmed') is not False
                or a.get('importance_assessed') is not False
                or a.get('independent_confirmation_count')!=0):
                raise RuntimeError('Enrichment elevated unsupported claims')
            if a.get('evidence_level')=='M0A':
                from evidence_v042 import paper_id, MAX_ABSTRACT
                if (a.get('publisher_id')!='arxiv' or not paper_id(a.get('url'))
                    or paper_id(a.get('metadata_record_url'))!=paper_id(a.get('url'))
                    or a.get('metadata_title_match') is not True
                    or a.get('metadata_read') is not True
                    or not isinstance(a.get('author_abstract'),str)
                    or not (0<len(a['author_abstract'])<=MAX_ABSTRACT)):
                    raise RuntimeError('M0A is not authenticated author metadata')
            elif a.get('evidence_level')=='M0':
                if a.get('author_abstract') is not None or a.get('metadata_read') is not False:
                    raise RuntimeError('M0 improperly contains extended text')
            else:
                raise RuntimeError('Unknown or unsupported evidence level')
    # V0.4.3 diagnostics: allowed to describe SOURCE coverage, not news/event recall.
    quality_path=source_root/'data/source_quality_v043.json'
    if quality_path.is_file():
        quality=json.loads(quality_path.read_text(encoding='utf-8'))
        qm=quality.get('meta',{})
        if (qm.get('rights_scope')!='descriptive_public_metadata_only'
            or qm.get('status')!='input_coverage_diagnostic_only'
            or qm.get('global_news_recall') is not None
            or qm.get('benchmark_event_recall') is not None
            or any(qm.get(k)!=0 for k in ('verified_claims','independently_confirmed_claims',
                'independent_corrob_evidence_items','importance_scores_created'))):
            raise RuntimeError('Source coverage report claims unsupported verification, importance or recall')
        count=len({x.get('publisher_id') for x in live.get('items',[])})
        if qm.get('observed_publishers')!=count or qm.get('observed_items')!=len(live.get('items',[])):
            raise RuntimeError('Coverage source counts do not match source metadata')
        from source_quality_v043 import DIMENSIONS
        dimensions=quality.get('dimensions',[])
        profiles={key:set(pubs) for key,label,pubs in DIMENSIONS}
        expected_keys=set(profiles)
        observed={x.get('publisher_id') for x in live.get('items',[])}
        if (len(dimensions)!=len(expected_keys) or {x.get('key') for x in dimensions}!=expected_keys
            or any(x.get('claim_coverage_confirmed') is not False for x in dimensions)
            or any(x.get('observed_publishers')!=sorted(observed.intersection(profiles[x['key']]))
                   or x.get('observed_publisher_count')!=len(observed.intersection(profiles[x['key']]))
                   for x in dimensions)
            or qm.get('domains_no_observed_publisher')!=sum(x.get('observed_publisher_count')==0 for x in dimensions)):
            raise RuntimeError('Source coverage dimension is inconsistent or asserts verification')
        dest=output/'data/source_quality_v043.json'
        shutil.copyfile(quality_path,dest)
    elif strict:
        raise FileNotFoundError('Missing V0.4.3 coverage audit; production deployment blocked')

    # V0.4.4 probationary input checks: only status/counts, never candidate headlines.
    probe_path=source_root/'data/source_expansion_v044.json'
    if probe_path.is_file():
        report=json.loads(probe_path.read_text(encoding='utf-8'))
        from source_expansion_v044 import check_report
        check_report(report)
        shutil.copyfile(probe_path,output/'data/source_expansion_v044.json')
    elif strict:
        raise FileNotFoundError('V0.4.4 candidate probe report required')
    published=sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())
    print('Public site files:',json.dumps(published,ensure_ascii=False))
    return published

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',default=str(BASE/'_site'))
    opts=ap.parse_args()
    build(opts.output,strict=True)

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
    for item in live.get('items',[]):
        if item.get('summary') is not None or item.get('source_id') not in ('fed-monetary','bea-news','arxiv-ai','arxiv-robotics'):
            raise RuntimeError('Unsafe metadata: unknown source or article content in export')
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
    published=sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())
    print('Public site files:',json.dumps(published,ensure_ascii=False))
    return published

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',default=str(BASE/'_site'))
    opts=ap.parse_args()
    build(opts.output,strict=True)

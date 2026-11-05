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
    published=sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())
    print('Public site files:',json.dumps(published,ensure_ascii=False))
    return published

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',default=str(BASE/'_site'))
    opts=ap.parse_args()
    build(opts.output,strict=True)

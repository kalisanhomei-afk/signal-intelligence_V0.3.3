#!/usr/bin/env python3
"""Deployment smoke tests: public files, metadata contract, GitHub workflow gates."""
import json, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_public_site import build
BASE=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as t:
    dest=Path(t)/'public'
    files=build(dest)
    assert 'index.html' in files and 'source-console.html' in files
    assert 'data/v032_live_probe.json' in files and 'data/v032_candidates.json' in files
    assert 'data/source_registry.json' not in files and 'data/source_audit.json' not in files
    assert '.github/workflows' not in files
    assert not list(dest.glob('scripts/*'))
    obj=json.loads((dest/'data/v032_live_probe.json').read_text(encoding='utf-8'))
    assert obj['meta']['state']=='not_run' or obj['meta']['state']=='checked'
    assert obj.get('sources',[])==[] or all(r.get('legal_approved') is False for r in obj['sources'])
    disc=json.loads((dest/'data/discovered.json').read_text(encoding='utf-8'))
    assert disc['meta']['rights_scope']=='descriptive_public_metadata_only'
    assert all(x['source_id'] in ('fed-monetary','bea-news','arxiv-ai','arxiv-robotics','eia-energy','nasa-news') and x.get('summary') is None for x in disc['items'])
    assert '來源接入' in (dest/'source-console.html').read_text(encoding='utf-8')
wf=(BASE/'.github/workflows/signal-preflight-pages.yml').read_text(encoding='utf-8')
assert 'workflow_dispatch' in wf
assert 'actions/deploy-pages' not in wf  # retired workflow never overrides live V0.4
assert 'schedule:' not in wf and 'push:' not in wf
print('PASS V0.3.3 compatibility: public allowlist, reviewed metadata only, source registry remains private')

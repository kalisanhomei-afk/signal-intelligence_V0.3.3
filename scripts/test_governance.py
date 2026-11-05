#!/usr/bin/env python3
"""Offline governance contract tests."""
import copy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_sources import audit_registry, load
BASE=Path(__file__).resolve().parents[1]
registry=load(BASE/'data/source_registry.json')
config=load(BASE/'data/sources.json')
assert len(registry['publishers'])==37
assert len({x['publisher_id'] for x in registry['publishers']})==37
pilot=audit_registry(registry,config)
assert not pilot['errors'],pilot['errors']
assert pilot['active_feed_channels']==10
assert pilot['independent_active_publishers']==6
assert pilot['sources_requiring_review']==10
assert not pilot['approved_for_production']
assert any('bbc: 4 feeds' in message for message in pilot['warnings'])
production=audit_registry(registry,config,production=True)
assert len(production['errors'])==10
# unregistered provider must be rejected
unknown=copy.deepcopy(config)
unknown['sources'][0]['publisher_id']='unknown'
assert any('no parent publisher' in x for x in audit_registry(registry,unknown)['errors'])
# new feeds may not self-select legacy_pilot to bypass governance
new_feed=copy.deepcopy(config)
new_feed['sources'].append({**config['sources'][0], 'id':'unapproved-new','publisher_id':'fed'})
assert any('cannot bypass' in x for x in audit_registry(registry,new_feed)['errors'])
# duplicate publication IDs must be rejected
duplicate=copy.deepcopy(registry)
duplicate['publishers'][1]['publisher_id']='fed'
assert any('duplicate' in x for x in audit_registry(duplicate,config)['errors'])
# approval flags alone cannot waive publisher-level licensing review
bad=copy.deepcopy(registry)
bad['publishers'][0]['automation_approved']=True
assert any('without permission' in x for x in audit_registry(bad,config)['errors'])
# Empty enabled production set must fail even with registry.
empty=copy.deepcopy(config)
for f in empty['sources']:
    f['enabled']=False
assert any('at least one' in e for e in audit_registry(registry,empty,production=True)['errors'])
# Directly setting status flags without evidence must never bypass approval.
forged=copy.deepcopy(config)
for f in forged['sources']:
    f.update(activation_status='approved', permission_status='approved',live_verified=True, live_tested_at='2026-11-05')
forged_reg=copy.deepcopy(registry)
for p in forged_reg['publishers']:
    p.update(permission_status='approved', automation_approved=True)
assert any('cannot enable in production' in x for x in audit_registry(forged_reg,forged,production=True)['errors'])
print('PASS governance: 37 unique candidates; 10 legacy feeds/6 publishers; double-counting flagged; production blocks unreviewed sources.')

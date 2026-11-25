"""Re-stage validation: openapi counts, live endpoint, validate, eval, smoke."""
import asyncio
import sys

from fastapi.testclient import TestClient

from hr_service.main import app as hr_app
from it_service.main import app as it_app

hr = TestClient(hr_app)
it = TestClient(it_app)

# 1. openapi counts
hr_ops = [v.get('operationId') for p in hr.get('/openapi.json').json()['paths'].values() for v in p.values()]
it_ops = [v.get('operationId') for p in it.get('/openapi.json').json()['paths'].values() for v in p.values()]
print('HR ops (%d):' % len(hr_ops), sorted(hr_ops))
print('IT ops (%d):' % len(it_ops), sorted(it_ops))
assert len(hr_ops) == 9, hr_ops   # 5 functional + 1 health + 3 demo
assert len(it_ops) == 11, it_ops  # 7 functional (I1-I6+L1) + 1 health + 3 demo
assert 'it_oncall_coverage' in it_ops
# H5 untouched
assert 'hr_get_oncall' in hr_ops
# 6 demo ops present but documented as allowlist-excluded
demo = [o for o in hr_ops + it_ops if 'demo' in o]
assert len(demo) == 6, demo
print('DEMO ops excluded from Synapse allowlist (6):', sorted(demo))

# 2. live endpoint 404-free with seeded data
r = it.get('/it/oncall-coverage')
print('GET /it/oncall-coverage ->', r.status_code)
assert r.status_code == 200, r.text
body = r.json()
print('coverage: team=%s oncall=%s breaches=%d owned=%s reroute=%s' % (
    body['team'], body['oncall']['email'], body['breach_count'],
    body['owned_by_oncall'], body['needs_reroute']))
assert body['team'] == 'support-night'
assert body['oncall']['employee_id'] == 'EMP-014'
assert body['breach_count'] >= 3
# explicit params
r2 = it.get('/it/oncall-coverage', params={'team': 'support-night'})
assert r2.status_code == 200, r2.text
# unknown team -> 404 like H5 (consistent, not a stage path)
r3 = it.get('/it/oncall-coverage', params={'team': 'no-such-team'})
assert r3.status_code == 404, r3.status_code
print('unknown team 404 (consistent with H5): OK')

# 3. H5 still live, unmodified behaviour
h = hr.get('/hr/oncall', params={'team': 'support-night'})
assert h.status_code == 200, h.text
print('H5 GET /hr/oncall ->', h.status_code, h.json()['employee_id'])

print('ALL LIVE-ENDPOINT CHECKS PASSED')

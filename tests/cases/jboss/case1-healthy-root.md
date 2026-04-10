# JBoss Case 1 - Healthy Root Endpoint

## Input state
- One JBoss instance running: app1
- Root URL on port 8080 returns HTTP 200
- API running on port 11000

## Captured artifacts
- docs/evidence/jboss/runtime/java-process.txt
- docs/evidence/jboss/runtime/http-head.txt
- docs/evidence/jboss/api/healthz.json
- docs/evidence/jboss/api/status-baseline.json
- docs/evidence/jboss/api/plan-dryrun.json
- docs/evidence/jboss/api/scale-baseline.json
- tests/fixtures/expected/jboss-case1-healthy-root.json

## Observed result
- healthy_count = 1
- action = hold
- target_count = 1
- policy_source = rules

## Interpretation
The control plane correctly detected a healthy steady-state JBoss instance and did not request scaling.

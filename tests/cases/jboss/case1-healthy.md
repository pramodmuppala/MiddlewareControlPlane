# JBoss Case 1 - Healthy Steady State

## Input state
- Two JBoss instances running: app1 and app2
- Root URL on app1 port 8080 returns HTTP 200
- Root URL on app2 port 8090 returns HTTP 200
- API running on port 11000

## Captured artifacts
- tests/cases/jboss/status-case1-healthy-fixed.json
- tests/cases/jboss/plan-case1-healthy-fixed.json
- tests/fixtures/expected/jboss-case1-healthy.json

## Observed result
- healthy_count = 2
- action = hold
- target_count = 2
- policy_source = rules

## Interpretation
The control plane correctly detected a healthy steady-state JBoss cluster and did not request scaling.

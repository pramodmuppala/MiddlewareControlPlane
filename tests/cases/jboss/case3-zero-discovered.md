# JBoss Case 3 - Zero Discovered Instances

## Input state
- app1 and app2 directories temporarily moved out of /opt/jboss
- no discovered instance directories
- LLM disabled for deterministic testing

## Captured artifacts
- tests/cases/jboss/status-case3-zero-discovered.json
- tests/cases/jboss/status-case3-zero-discovered.httpstatus
- tests/cases/jboss/plan-case3-zero-discovered.json
- tests/cases/jboss/plan-case3-zero-discovered.httpstatus
- tests/fixtures/expected/jboss-case3-zero-discovered.json

## Intended expectation
The control plane should detect zero discovered instances and request scale-up to the configured minimum.

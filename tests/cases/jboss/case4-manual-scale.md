# JBoss Case 4 - Manual Scale Request (Dry Run)

## Input state
- Two discovered JBoss instances: app1 and app2
- Both probes unhealthy at capture time
- API request explicitly sets target_count = 2
- dry_run = true
- LLM disabled for deterministic testing

## Captured artifacts
- tests/cases/jboss/scale-case4-manual-dryrun.json
- tests/cases/jboss/scale-case4-manual-dryrun.httpstatus
- tests/fixtures/expected/jboss-case4-manual-scale.json

## Observed result
- current_count = 2
- healthy_count = 0
- action = hold
- target_count = 2
- policy_source = api_manual
- return_code = 0

## Interpretation
The control plane accepted the manual target count and correctly held steady because the current discovered instance count already matched the requested target.

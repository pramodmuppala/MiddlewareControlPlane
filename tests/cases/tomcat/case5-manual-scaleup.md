# Tomcat Case 5 - Manual Scale Up Request

## Input state
- One discovered instance: app1
- Probe unhealthy at the time of capture
- Cooldown active
- API request explicitly set target_count = 2
- dry_run = true

## Captured artifacts
- tests/cases/tomcat/scale-case5-manual-scaleup-dryrun.json
- tests/fixtures/expected/tomcat-case5-manual-scaleup.json

## Observed result
- action = scale_up
- target_count = 2
- policy_source = api_manual
- return_code = 0
- dry_run = true

## Interpretation
The manual API scaling path accepted the requested target and produced a scale-up plan without applying changes.

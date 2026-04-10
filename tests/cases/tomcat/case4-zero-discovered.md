# Tomcat Case 4 - Zero Discovered Instances

## Input state
- app1 directory temporarily moved out of /opt/tomcat
- no discovered instance directories
- API running on port 11000

## Captured artifacts
- tests/cases/tomcat/status-case4-zero-discovered.json
- tests/cases/tomcat/plan-case4-zero-discovered.json
- tests/fixtures/expected/tomcat-case4-zero-discovered.json

## Observed result
- current_count = 0
- healthy_count = 0
- action = scale_up
- target_count = 1
- policy_source = rules

## Interpretation
The control plane correctly identified that there were no discovered Tomcat instances and requested scale-up to the configured minimum instance count.

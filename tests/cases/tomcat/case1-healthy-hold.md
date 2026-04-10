# Tomcat Case 1 - Healthy Steady State

## Inputs
- Tomcat running
- API running on port 11000
- config: configs/tomcat-local.yaml
- baseline healthy system

## Captured artifacts
- tests/cases/tomcat/status-case1-healthy.json
- tests/cases/tomcat/plan-case1-healthy.json
- tests/fixtures/expected/tomcat-case1-healthy-hold.json

## Intended expectation
With one healthy instance and minimum instances set to 1, the control plane should not request a scale-up or unsafe scale-down.

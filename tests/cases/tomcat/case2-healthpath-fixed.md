# Tomcat Case 2 - Healthy Probe Path

## Input state
- One Tomcat instance running: app1
- Health endpoint configured to /test
- API running on port 11000

## Captured artifacts
- tests/cases/tomcat/status-case2-healthpath-fixed.json
- tests/cases/tomcat/plan-case2-healthpath-fixed.json
- tests/fixtures/expected/tomcat-case2-healthy-probe.json

## Observed result
- healthy_count = 1
- probe status = 200
- action = hold
- target_count = 1

## Interpretation
The control plane correctly detected a healthy steady-state Tomcat instance and did not request scaling.

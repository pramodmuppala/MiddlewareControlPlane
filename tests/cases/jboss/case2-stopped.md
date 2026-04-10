# JBoss Case 2 - Stopped Runtime, Instance Dirs Still Present

## Input state
- JBoss processes for app1 and app2 were stopped
- instance directories still exist under /opt/jboss
- LLM disabled for deterministic testing

## Captured artifacts
- tests/cases/jboss/status-case2-stopped.json
- tests/cases/jboss/status-case2-stopped.httpstatus
- tests/cases/jboss/plan-case2-stopped.json
- tests/cases/jboss/plan-case2-stopped.httpstatus
- tests/fixtures/expected/jboss-case2-stopped.json

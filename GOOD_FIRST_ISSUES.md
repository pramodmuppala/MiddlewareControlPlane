# Good First Issues for MiddlewareControlPlane

This file lists starter contribution ideas for engineers who want to review or improve MiddlewareControlPlane. Please open an issue before starting larger changes.

## Documentation

### Add a 5-minute quickstart

Create a short path for a new user to validate the repo and run one dry-run cycle.

Include:

- prerequisites
- setup commands
- JBoss dry-run command
- Tomcat dry-run command
- expected output

Labels: `documentation`, `good first issue`

### Add sample dry-run output

Add sanitized example outputs for:

- JBoss dry-run
- Tomcat dry-run
- resolved config
- plan response

Labels: `documentation`, `testing`, `good first issue`

### Explain shared vs platform-specific logic

Add a short design note explaining what belongs in the root control plane and what belongs in `platforms/jboss` or `platforms/tomcat`.

Labels: `architecture`, `documentation`, `good first issue`

## Testing

### Add config resolution tests

Create tests for loading root configs and importing platform defaults.

Labels: `testing`, `config`, `good first issue`

### Add adapter contract tests

Add tests verifying that JBoss and Tomcat adapters return expected execution variables and commands in dry-run mode.

Labels: `testing`, `adapter`

### Add unsafe scale-down tests

Add tests showing scale-down is blocked during unhealthy periods or cooldown windows.

Labels: `testing`, `policy`, `safety`

## Benchmarking

### Add benchmark report template

Create `docs/evidence/BENCHMARK_TEMPLATE.md` with fields for environment, platform, scenario, concurrency, request count, scaling result, and observations.

Labels: `benchmark`, `documentation`, `good first issue`

### Add decision-log examples

Add sanitized examples of decision logs for no-op, scale-up, and blocked scale-down scenarios.

Labels: `benchmark`, `documentation`

### Add manual-vs-control-plane comparison

Create a simple comparison showing manual operator steps versus control-plane-assisted steps.

Labels: `benchmark`, `documentation`

## API

### Add curl examples for REST endpoints

Document examples for:

- `GET /healthz`
- `GET /status`
- `POST /plan`
- `POST /scale`
- `POST /config/resolved`

Labels: `api`, `documentation`, `good first issue`

### Add sample API responses

Add sample JSON outputs for health, status, plan, and resolved config.

Labels: `api`, `documentation`

## Observability

### Add Prometheus-style metrics proposal

Open a design note for metrics such as decisions made, scale actions, blocked actions, unhealthy instances, and last execution duration.

Labels: `observability`, `architecture`

### Add audit export proposal

Design a simple export format for decision history and scaling actions.

Labels: `observability`, `documentation`

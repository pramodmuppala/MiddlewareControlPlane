# MiddlewareControlPlane Roadmap

MiddlewareControlPlane provides a shared control-plane model for JBoss EAP and Tomcat. The roadmap focuses on making the project easier to test, easier to extend, and stronger as evidence-backed middleware automation.

## Phase 1: Review-ready repository

- Add clearer quickstart flow.
- Add screenshots or diagrams for API and architecture.
- Add example output for JBoss and Tomcat dry-runs.
- Add troubleshooting notes for common setup failures.
- Expand docs for shared vs platform-specific responsibilities.

## Phase 2: Validation and test coverage

- Strengthen `validate_repo.sh`.
- Add unit tests for config resolution.
- Add tests for adapter behavior.
- Add tests for policy decisions.
- Add tests for unhealthy-instance behavior.
- Add tests for dry-run command generation.

## Phase 3: Benchmark and evidence generation

- Add a standard benchmark report template.
- Add sample benchmark outputs under `docs/evidence/`.
- Compare manual operation vs control-plane-assisted operation.
- Add decision-log examples.
- Add repeatable load-generator scenarios.
- Add summary charts or tables for benchmark runs.

## Phase 4: API and observability

- Improve `/status`, `/plan`, `/scale`, and `/config/resolved` examples.
- Add OpenAPI screenshots.
- Add structured status output examples.
- Add Prometheus-style metrics endpoint.
- Add clearer decision and state history.
- Add audit-friendly export of decisions.

## Phase 5: Policy and safety hardening

- Improve cooldown handling.
- Strengthen scale-down protections.
- Add policy simulation mode.
- Add richer bounds validation.
- Add unhealthy-period safeguards.
- Document OpenAI recommendation guardrails.
- Add tests showing unsafe recommendations are blocked.

## Phase 6: Platform extensibility

- Clean up adapter interfaces.
- Add adapter contract documentation.
- Add example skeleton for a new middleware platform.
- Evaluate WebLogic or another Java middleware runtime as a future adapter.
- Keep Ansible execution platform-specific and control logic shared.

## Contribution priorities

Most useful contributions right now:

1. validation tests
2. dry-run examples
3. benchmark reports
4. API documentation
5. adapter cleanup
6. policy safety tests

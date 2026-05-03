# Contributing to MiddlewareControlPlane

Thanks for your interest in MiddlewareControlPlane. This project provides a shared Python control plane for JBoss EAP and Tomcat while keeping platform-specific Ansible execution in dedicated backends.

Contributions are welcome in documentation, adapters, policy logic, API usability, benchmarks, validation, observability, and evidence generation.

## Project scope

MiddlewareControlPlane centralizes common middleware automation responsibilities:

- runtime discovery
- health probing
- CPU and memory sampling
- scaling policy
- API exposure
- decision logging
- evidence generation
- adapter-based execution through platform-specific Ansible playbooks

In scope:

- shared control-loop improvements
- JBoss and Tomcat adapter improvements
- dry-run planning
- benchmark and evidence reporting
- REST API examples and documentation
- policy safety checks
- validation and testing scripts

Out of scope for now:

- production-certification claims without evidence
- replacing Ansible as the reconciler
- unsafe automatic scale-down behavior
- broad orchestration beyond the supported middleware model

## How to contribute

1. Fork the repository.
2. Create a branch:
   ```bash
   git checkout -b feature/short-description
   ```
3. Make a focused change.
4. Run validation:
   ```bash
   ./scripts/validate_repo.sh
   ```
5. Test at least one dry-run cycle:
   ```bash
   python mcp.py --config configs/jboss-local.yaml --once --dry-run
   python mcp.py --config configs/tomcat-local.yaml --once --dry-run
   ```
6. Open a pull request with:
   - what changed
   - which platform was tested
   - exact validation commands
   - logs, screenshots, or evidence output where relevant

## Development expectations

Please keep shared logic in the root control plane and platform-specific behavior in the proper adapter or platform directory.

Before moving logic into the shared layer, ask:

- Is this common to both JBoss and Tomcat?
- Does this belong in an adapter?
- Does this change affect dry-run safety?
- Does this change affect scale-up or scale-down decisions?

## Testing guidance

Useful validation areas:

- config loading and resolved config output
- runtime discovery
- health probe behavior
- CPU and memory sampling
- rule-based scale decisions
- guarded LLM recommendation behavior
- dry-run Ansible command generation
- decision logs and state persistence
- REST API responses

## Safety and guardrails

Scaling and execution changes should remain bounded, explainable, and auditable.

Any contribution touching policy or OpenAI-assisted recommendation logic should document:

- configured bounds
- step-size limits
- cooldown behavior
- unhealthy-period behavior
- scale-down protections

## Issue and discussion etiquette

Please include reproducible details:

- operating system
- Python version
- platform config used
- command or API request
- expected behavior
- actual behavior
- relevant logs or output

## Pull request checklist

- [ ] The change is focused and documented.
- [ ] Shared vs platform-specific logic is placed correctly.
- [ ] `./scripts/validate_repo.sh` was run.
- [ ] At least one dry-run command was tested.
- [ ] Safety impact is explained, if applicable.
- [ ] No secrets, tokens, or local-only paths are committed.

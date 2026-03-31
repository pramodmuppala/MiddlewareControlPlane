# Monorepo Integration Notes

This repository combines a shared middleware control plane with two vendored platform backends:

- `platforms/jboss`
- `platforms/tomcat`

## Wiring

- `configs/jboss-local.yaml` targets `platforms/jboss`
- `configs/tomcat-local.yaml` targets `platforms/tomcat`
- state and decision-log files are repo-local under `.state/`

## Preferred entrypoints

Use the shared entrypoints at the repository root:

```bash
python mcp.py --config configs/jboss-local.yaml --once --dry-run
python mcp.py --config configs/tomcat-local.yaml --once --dry-run
./scripts/run_api.sh
```

The vendored autoscaler scripts remain in place for compatibility and reference, but the shared root control plane is the intended operator-facing interface.

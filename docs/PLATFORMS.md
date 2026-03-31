# Platform Adapters

The monorepo keeps one shared control-plane core and two vendored execution backends.

## JBoss

Path: `platforms/jboss`

Used for:

- instance discovery rooted at `/opt/jboss`
- target-count reconciliation through `Deploy.yml`
- JBoss-specific runtime and scaling defaults loaded from `vars/main.yml`

## Tomcat

Path: `platforms/tomcat`

Used for:

- instance discovery rooted at `/opt/tomcat`
- target-count reconciliation through `Deploy.yml`
- Tomcat-specific runtime and scaling defaults loaded from `vars/main.yml` under `tomcat_defaults`

## Compatibility boundary

The vendored platform trees are preserved mainly as execution backends and compatibility references. The preferred entrypoints for this repository are:

- `python mcp.py --config configs/jboss-local.yaml ...`
- `python mcp.py --config configs/tomcat-local.yaml ...`
- `./scripts/run_api.sh`

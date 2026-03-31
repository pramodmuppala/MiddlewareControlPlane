#!/usr/bin/env bash
set -euo pipefail

python3 -m compileall mcp.py middleware_control_plane benchmarks >/dev/null
python3 mcp.py --config configs/jboss-local.yaml --once --dry-run >/dev/null
python3 mcp.py --config configs/tomcat-local.yaml --once --dry-run >/dev/null

echo "Validation passed: compileall + JBoss dry-run + Tomcat dry-run"

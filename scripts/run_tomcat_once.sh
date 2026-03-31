#!/usr/bin/env bash
set -euo pipefail
python mcp.py --config configs/tomcat-local.yaml --once "${@}"

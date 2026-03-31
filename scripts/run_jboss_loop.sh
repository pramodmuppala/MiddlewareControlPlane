#!/usr/bin/env bash
set -euo pipefail
python mcp.py --config configs/jboss-local.yaml "$@"

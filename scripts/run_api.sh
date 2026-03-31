#!/usr/bin/env bash
set -euo pipefail

exec uvicorn middleware_control_plane.api:app --host 0.0.0.0 --port "${PORT:-11000}"

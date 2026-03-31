#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from middleware_control_plane.benchmark import run_benchmark, write_benchmark_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simple HTTP benchmark against a middleware endpoint")
    parser.add_argument("--url", required=True)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--output-dir", default="docs/evidence")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_benchmark(
        args.url,
        concurrency=args.concurrency,
        total_requests=args.requests,
        timeout_seconds=args.timeout_seconds,
    )
    outputs = write_benchmark_outputs(summary, output_dir=args.output_dir)
    print(json.dumps({"summary": summary.to_dict(), "outputs": outputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

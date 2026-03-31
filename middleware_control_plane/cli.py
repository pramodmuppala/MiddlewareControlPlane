from __future__ import annotations

import argparse

from middleware_control_plane.config import load_config
from middleware_control_plane.engine import ControlPlaneEngine, log


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Middleware Control Plane")
    parser.add_argument("--config", required=True, help="Path to YAML configuration")
    parser.add_argument("--once", action="store_true", help="Run one control-loop cycle")
    parser.add_argument("--dry-run", action="store_true", help="Override config to avoid Ansible execution")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)
    if args.dry_run:
        cfg.dry_run = True
    engine = ControlPlaneEngine(cfg)
    if args.once:
        log(f"Running one cycle for platform={cfg.platform} dry_run={cfg.dry_run}")
        return engine.run_once()
    return engine.run_forever()

from __future__ import annotations

import json
import subprocess
from typing import List, Tuple

from middleware_control_plane.adapters.base import MiddlewareAdapter
from middleware_control_plane.config import MCPConfig


def build_ansible_cmd(cfg: MCPConfig, adapter: MiddlewareAdapter, target_count: int, destroy_enabled: bool) -> List[str]:
    extra_vars = adapter.build_scale_extra_vars(cfg, target_count, destroy_enabled)
    return [
        cfg.ansible.executable,
        "-i",
        cfg.ansible.inventory,
        cfg.ansible.playbook,
        "-e",
        json.dumps(extra_vars),
    ]


def invoke_ansible(
    cfg: MCPConfig,
    adapter: MiddlewareAdapter,
    target_count: int,
    destroy_enabled: bool,
    *,
    dry_run: bool,
) -> Tuple[int, bool, str]:
    cmd = build_ansible_cmd(cfg, adapter, target_count, destroy_enabled)
    printable = " ".join(cmd)
    if dry_run:
        return 0, False, printable
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cfg.ansible.working_directory,
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, True, output if output.strip() else printable

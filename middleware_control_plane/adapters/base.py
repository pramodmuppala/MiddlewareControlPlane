from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple

from middleware_control_plane.config import MCPConfig


class MiddlewareAdapter(ABC):
    platform_name: str
    extra_vars_key: str

    def discover_instances(self, cfg: MCPConfig) -> List[str]:
        root = Path(cfg.runtime.instance_root)
        if not root.exists():
            return []
        pattern = re.compile(rf"^{re.escape(cfg.runtime.instance_name_prefix)}(\d+)$")
        matches = [child.name for child in root.iterdir() if child.is_dir() and pattern.match(child.name)]
        return sorted(matches, key=self.instance_sort_key)

    def instance_sort_key(self, name: str) -> Tuple[str, int]:
        match = re.search(r"(\d+)$", name)
        return re.sub(r"\d+$", "", name), int(match.group(1)) if match else -1

    def instance_number(self, cfg: MCPConfig, name: str) -> int:
        return int(name[len(cfg.runtime.instance_name_prefix) :])

    def http_port_for_instance(self, cfg: MCPConfig, name: str) -> int:
        number = self.instance_number(cfg, name)
        offset = number - cfg.runtime.instance_start_index
        return cfg.runtime.base_http_port + (offset * cfg.runtime.port_stride)

    def build_scale_extra_vars(self, cfg: MCPConfig, target_count: int, destroy_enabled: bool) -> Dict[str, object]:
        return {
            self.extra_vars_key: {
                "instance_count": target_count,
                "destroy_enabled": destroy_enabled,
            }
        }

    @abstractmethod
    def describe(self) -> str:
        raise NotImplementedError

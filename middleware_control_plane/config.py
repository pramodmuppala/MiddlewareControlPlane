from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class AnsibleConfig:
    executable: str = "ansible-playbook"
    inventory: str = "hosts"
    playbook: str = "Deploy.yml"
    working_directory: str = "."


@dataclass
class RuntimeConfig:
    instance_root: str
    instance_name_prefix: str = "app"
    instance_start_index: int = 1
    base_http_port: int = 8080
    port_stride: int = 100
    health_path: str = "/"
    health_timeout_seconds: float = 2.0


@dataclass
class ScalingConfig:
    min_instances: int = 1
    max_instances: int = 10
    scale_up_cpu_percent: float = 75.0
    scale_down_cpu_percent: float = 25.0
    scale_up_mem_percent: float = 85.0
    scale_down_mem_percent: float = 50.0
    scale_up_avg_latency_ms: float = 800.0
    scale_down_avg_latency_ms: float = 250.0
    consecutive_up_required: int = 3
    consecutive_down_required: int = 5
    cooldown_seconds: int = 300
    loop_interval_seconds: int = 60
    desired_floor_at_bootstrap: Optional[int] = None


@dataclass
class StateConfig:
    state_file: str = "/tmp/middleware-control-plane-state.json"
    decision_log_file: str = "/tmp/middleware-control-plane-decisions.jsonl"


@dataclass
class LLMConfig:
    enabled: bool = False
    model: Optional[str] = None


@dataclass
class MCPConfig:
    platform: str
    ansible: AnsibleConfig
    runtime: RuntimeConfig
    scaling: ScalingConfig
    state: StateConfig
    llm: LLMConfig
    dry_run: bool = False
    legacy_vars_file: Optional[str] = None
    legacy_platform_key: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "MCPConfig":
        return cls(
            platform=str(raw["platform"]).strip().lower(),
            ansible=AnsibleConfig(**raw.get("ansible", {})),
            runtime=RuntimeConfig(**raw.get("runtime", {})),
            scaling=ScalingConfig(**raw.get("scaling", {})),
            state=StateConfig(**raw.get("state", {})),
            llm=LLMConfig(**raw.get("llm", {})),
            dry_run=bool(raw.get("dry_run", False)),
            legacy_vars_file=raw.get("legacy_vars_file"),
            legacy_platform_key=raw.get("legacy_platform_key"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "ansible": asdict(self.ansible),
            "runtime": asdict(self.runtime),
            "scaling": asdict(self.scaling),
            "state": asdict(self.state),
            "llm": asdict(self.llm),
            "dry_run": self.dry_run,
            "legacy_vars_file": self.legacy_vars_file,
            "legacy_platform_key": self.legacy_platform_key,
        }


def _read_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Configuration at {path} must be a mapping")
    return data


def _merge_if_missing(target: Dict[str, Any], source: Dict[str, Any], keys: Dict[str, str]) -> None:
    for target_key, source_key in keys.items():
        if target.get(target_key) is None and source.get(source_key) is not None:
            target[target_key] = source[source_key]


def _apply_legacy_vars(raw: Dict[str, Any], config_path: Path) -> Dict[str, Any]:
    legacy_vars_file = raw.get("legacy_vars_file")
    if not legacy_vars_file:
        return raw

    legacy_path = Path(legacy_vars_file)
    if not legacy_path.is_absolute():
        legacy_path = (config_path.parent / legacy_path).resolve()
    legacy_data = _read_yaml(legacy_path)

    platform = str(raw.get("platform", "")).strip().lower()
    platform_key = raw.get("legacy_platform_key") or platform
    legacy_platform = legacy_data.get(platform_key, {})
    if not isinstance(legacy_platform, dict):
        raise ValueError(f"Legacy vars at {legacy_path} must contain a mapping under key '{platform_key}'")

    runtime = dict(raw.get("runtime", {}))
    runtime_source = dict(legacy_platform)
    if "catalina_base_root" in legacy_platform and "instance_root" not in runtime_source:
        runtime_source["instance_root"] = legacy_platform["catalina_base_root"]
    if isinstance(legacy_platform.get("connectors"), list) and legacy_platform["connectors"]:
        connector0 = legacy_platform["connectors"][0]
        if isinstance(connector0, dict) and "port" in connector0 and "base_http_port" not in runtime_source:
            runtime_source["base_http_port"] = connector0["port"]
    if "health_url" in legacy_platform and "health_path" not in runtime_source:
        runtime_source["health_path"] = "/"

    _merge_if_missing(
        runtime,
        runtime_source,
        {
            "instance_root": "instance_root",
            "instance_name_prefix": "instance_name_prefix",
            "instance_start_index": "instance_start_index",
            "base_http_port": "base_http_port",
            "port_stride": "port_stride",
            "health_path": "health_path",
        },
    )

    if raw.get("scaling") is None:
        raw["scaling"] = {}
    scaling = dict(raw.get("scaling", {}))
    legacy_autoscale = {}
    if isinstance(legacy_data.get("autoscale"), dict):
        legacy_autoscale.update(legacy_data["autoscale"])
    if isinstance(legacy_platform.get("autoscale"), dict):
        legacy_autoscale.update(legacy_platform["autoscale"])
    _merge_if_missing(
        scaling,
        legacy_autoscale,
        {
            "min_instances": "min_instances",
            "max_instances": "max_instances",
            "scale_up_cpu_percent": "scale_up_cpu_percent",
            "scale_down_cpu_percent": "scale_down_cpu_percent",
            "scale_up_mem_percent": "scale_up_mem_percent",
            "scale_down_mem_percent": "scale_down_mem_percent",
            "scale_up_avg_latency_ms": "scale_up_avg_latency_ms",
            "scale_down_avg_latency_ms": "scale_down_avg_latency_ms",
            "consecutive_up_required": "consecutive_up_required",
            "consecutive_down_required": "consecutive_down_required",
            "cooldown_seconds": "cooldown_seconds",
            "loop_interval_seconds": "loop_interval_seconds",
            "desired_floor_at_bootstrap": "desired_floor_at_bootstrap",
        },
    )
    if scaling.get("desired_floor_at_bootstrap") is None and legacy_platform.get("instance_count") is not None:
        scaling["desired_floor_at_bootstrap"] = legacy_platform.get("instance_count")

    merged = dict(raw)
    merged["runtime"] = runtime
    merged["scaling"] = scaling
    merged["legacy_vars_file"] = str(legacy_path)
    return merged


def _resolve_relative_paths(raw: Dict[str, Any], config_path: Path) -> Dict[str, Any]:
    merged = dict(raw)

    ansible = dict(merged.get("ansible", {}))
    working_directory = ansible.get("working_directory")
    if working_directory:
        wd_path = Path(working_directory)
        if not wd_path.is_absolute():
            ansible["working_directory"] = str((config_path.parent / wd_path).resolve())
    merged["ansible"] = ansible

    state = dict(merged.get("state", {}))
    for key in ("state_file", "decision_log_file"):
        value = state.get(key)
        if value:
            path_value = Path(value)
            if not path_value.is_absolute():
                state[key] = str((config_path.parent.parent / path_value).resolve())
    merged["state"] = state
    return merged


def load_config(path: str) -> MCPConfig:
    file_path = Path(path).resolve()
    data = _read_yaml(file_path)
    data = _apply_legacy_vars(data, file_path)
    data = _resolve_relative_paths(data, file_path)
    return MCPConfig.from_dict(data)

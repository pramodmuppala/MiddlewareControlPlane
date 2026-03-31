#!/usr/bin/env python3
"""
JBoss metrics-based autoscaler with optional OpenAI policy support.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from llm_policy import decide_with_llm_guardrails
except Exception:
    decide_with_llm_guardrails = None


@dataclass
class Config:
    inventory: str = "hosts"
    playbook: str = "Deploy.yml"
    ansible_bin: str = "ansible-playbook"
    instance_root: str = "/opt/jboss"
    instance_name_prefix: str = "app"
    instance_start_index: int = 1
    base_http_port: int = 8080
    port_stride: int = 100
    health_path: str = "/"
    health_timeout_seconds: float = 2.0
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
    state_file: str = "/tmp/jboss_autoscaler_state.json"
    dry_run: bool = False
    use_llm: bool = False


@dataclass
class ProbeResult:
    instance_name: str
    port: int
    url: str
    healthy: bool
    status_code: Optional[int]
    latency_ms: Optional[float]
    error: Optional[str]


@dataclass
class State:
    up_streak: int = 0
    down_streak: int = 0
    last_scale_epoch: float = 0.0
    last_target_count: Optional[int] = None

    @classmethod
    def load(cls, path: str) -> "State":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            return cls(**json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return cls()

    def save(self, path: str) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def log(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


def read_cpu_times() -> Tuple[int, int]:
    with open("/proc/stat", "r", encoding="utf-8") as handle:
        first = handle.readline().strip().split()
    values = list(map(int, first[1:]))
    idle = values[3] + values[4]
    total = sum(values)
    return idle, total


def sample_cpu_percent(sample_seconds: float = 1.0) -> float:
    idle1, total1 = read_cpu_times()
    time.sleep(sample_seconds)
    idle2, total2 = read_cpu_times()
    delta_idle = idle2 - idle1
    delta_total = total2 - total1
    if delta_total <= 0:
        return 0.0
    busy = max(delta_total - delta_idle, 0)
    return round((busy / delta_total) * 100.0, 2)


def read_mem_percent() -> float:
    meminfo: Dict[str, int] = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.replace(":", "").split()
            if len(parts) >= 2:
                meminfo[parts[0]] = int(parts[1])
    total = meminfo.get("MemTotal", 1)
    available = meminfo.get("MemAvailable", 0)
    used = total - available
    return round((used / total) * 100.0, 2)


def discover_instances(root: str, prefix: str) -> List[str]:
    root_path = Path(root)
    if not root_path.exists():
        return []
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    matches = [child.name for child in root_path.iterdir() if child.is_dir() and pattern.match(child.name)]
    return sorted(matches, key=instance_sort_key)


def instance_sort_key(name: str) -> Tuple[str, int]:
    match = re.search(r"(\d+)$", name)
    return re.sub(r"\d+$", "", name), int(match.group(1)) if match else -1


def instance_number(name: str, prefix: str) -> int:
    return int(name[len(prefix):])


def instance_http_port(cfg: Config, name: str) -> int:
    number = instance_number(name, cfg.instance_name_prefix)
    offset = number - cfg.instance_start_index
    return cfg.base_http_port + (offset * cfg.port_stride)


def probe_url(url: str, timeout_seconds: float) -> Tuple[bool, Optional[int], Optional[float], Optional[str]]:
    start = time.perf_counter()
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            latency_ms = (time.perf_counter() - start) * 1000.0
            status = getattr(response, "status", None) or response.getcode()
            return 200 <= status < 400, status, round(latency_ms, 2), None
    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return False, exc.code, round(latency_ms, 2), str(exc)
    except Exception as exc:
        return False, None, None, str(exc)


def probe_instances(cfg: Config, instances: List[str]) -> List[ProbeResult]:
    path = cfg.health_path if cfg.health_path.startswith("/") else f"/{cfg.health_path}"
    results: List[ProbeResult] = []
    for name in instances:
        port = instance_http_port(cfg, name)
        url = f"http://127.0.0.1:{port}{path}"
        healthy, status_code, latency_ms, error = probe_url(url, cfg.health_timeout_seconds)
        results.append(ProbeResult(name, port, url, healthy, status_code, latency_ms, error))
    return results


def average_latency_ms(results: List[ProbeResult]) -> Optional[float]:
    samples = [result.latency_ms for result in results if result.healthy and result.latency_ms is not None]
    return round(sum(samples) / len(samples), 2) if samples else None


def build_ansible_cmd(cfg: Config, target_count: int, destroy_enabled: bool) -> List[str]:
    extra_vars = {"jboss": {"instance_count": target_count, "destroy_enabled": destroy_enabled}}
    return [cfg.ansible_bin, "-i", cfg.inventory, cfg.playbook, "-e", json.dumps(extra_vars)]


def invoke_ansible(cfg: Config, target_count: int, destroy_enabled: bool) -> int:
    cmd = build_ansible_cmd(cfg, target_count, destroy_enabled)
    log(f"Invoking Ansible: {' '.join(cmd)}")
    if cfg.dry_run:
        log("Dry run enabled; command not executed.")
        return 0
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


def within_cooldown(state: State, cfg: Config) -> bool:
    return (time.time() - state.last_scale_epoch) < cfg.cooldown_seconds


def decide_target_count_rules(
    cfg: Config,
    state: State,
    current_count: int,
    cpu_percent: float,
    mem_percent: float,
    avg_latency: Optional[float],
) -> Tuple[int, str]:
    if current_count < cfg.min_instances:
        return cfg.min_instances, "below minimum instance count"
    if current_count > cfg.max_instances:
        return cfg.max_instances, "above maximum instance count"

    up_signal = (
        cpu_percent >= cfg.scale_up_cpu_percent
        or mem_percent >= cfg.scale_up_mem_percent
        or (avg_latency is not None and avg_latency >= cfg.scale_up_avg_latency_ms)
    )
    down_signal = (
        cpu_percent <= cfg.scale_down_cpu_percent
        and mem_percent <= cfg.scale_down_mem_percent
        and (avg_latency is None or avg_latency <= cfg.scale_down_avg_latency_ms)
    )

    if up_signal and current_count < cfg.max_instances:
        state.up_streak += 1
        state.down_streak = 0
    elif down_signal and current_count > cfg.min_instances:
        state.down_streak += 1
        state.up_streak = 0
    else:
        state.up_streak = 0
        state.down_streak = 0

    if within_cooldown(state, cfg):
        return current_count, "cooldown active"
    if state.up_streak >= cfg.consecutive_up_required and current_count < cfg.max_instances:
        return current_count + 1, "scale-up thresholds exceeded"
    if state.down_streak >= cfg.consecutive_down_required and current_count > cfg.min_instances:
        return current_count - 1, "scale-down thresholds sustained"
    return current_count, "no scaling change"


def decide_target_count_llm(
    cfg: Config,
    state: State,
    current_count: int,
    healthy_count: int,
    cpu_percent: float,
    mem_percent: float,
    avg_latency: Optional[float],
    instances: List[str],
) -> Tuple[int, str]:
    if decide_with_llm_guardrails is None:
        raise RuntimeError("llm_policy.py not available or dependencies missing.")

    snapshot = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": "jboss-eap",
        "instances": instances,
        "current_count": current_count,
        "healthy_count": healthy_count,
        "cpu_percent": cpu_percent,
        "memory_percent": mem_percent,
        "avg_latency_ms": avg_latency,
        "cooldown_active": within_cooldown(state, cfg),
        "min_instances": cfg.min_instances,
        "max_instances": cfg.max_instances,
        "allowed_actions": ["scale_up", "scale_down", "hold"],
    }

    result = decide_with_llm_guardrails(
        snapshot,
        current_count=current_count,
        healthy_count=healthy_count,
        min_instances=cfg.min_instances,
        max_instances=cfg.max_instances,
        cooldown_active=within_cooldown(state, cfg),
    )
    raw = result["raw_recommendation"]
    guarded = result["guarded_recommendation"]
    log(f"LLM raw recommendation: {json.dumps(raw, sort_keys=True)}")
    log(f"LLM guarded recommendation: {json.dumps(guarded, sort_keys=True)}")
    return int(guarded["target_count"]), str(guarded["reason"])


def run_once(cfg: Config) -> int:
    state = State.load(cfg.state_file)
    instances = discover_instances(cfg.instance_root, cfg.instance_name_prefix)
    current_count = len(instances)

    cpu_percent = sample_cpu_percent(1.0)
    mem_percent = read_mem_percent()
    probes = probe_instances(cfg, instances)
    avg_latency = average_latency_ms(probes)
    healthy_count = sum(1 for probe in probes if probe.healthy)

    probe_summary = ", ".join(
        f"{probe.instance_name}:{'up' if probe.healthy else 'down'}@{probe.port}"
        for probe in probes
    ) or "no instances discovered"
    log(
        "instances=%s healthy=%s cpu=%.2f%% mem=%.2f%% avg_latency_ms=%s probes=[%s]"
        % (
            current_count,
            healthy_count,
            cpu_percent,
            mem_percent,
            avg_latency if avg_latency is not None else "n/a",
            probe_summary,
        )
    )

    if cfg.use_llm:
        target_count, reason = decide_target_count_llm(
            cfg,
            state,
            current_count,
            healthy_count,
            cpu_percent,
            mem_percent,
            avg_latency,
            instances,
        )
    else:
        target_count, reason = decide_target_count_rules(
            cfg,
            state,
            current_count,
            cpu_percent,
            mem_percent,
            avg_latency,
        )

    log(
        f"decision current={current_count} target={target_count} "
        f"up_streak={state.up_streak} down_streak={state.down_streak} reason={reason}"
    )

    if target_count != current_count:
        destroy_enabled = target_count < current_count
        rc = invoke_ansible(cfg, target_count, destroy_enabled)
        if rc != 0:
            log(f"Ansible scaling run failed with exit code {rc}")
            state.save(cfg.state_file)
            return rc
        state.last_scale_epoch = time.time()
        state.last_target_count = target_count
        state.up_streak = 0
        state.down_streak = 0
        log(f"Scaling action completed. New target count: {target_count}")

    state.save(cfg.state_file)
    return 0


def parse_args() -> Tuple[Config, bool]:
    parser = argparse.ArgumentParser(description="JBoss metrics-based autoscaler")
    parser.add_argument("--inventory", default="hosts")
    parser.add_argument("--playbook", default="Deploy.yml")
    parser.add_argument("--ansible-bin", default="ansible-playbook")
    parser.add_argument("--instance-root", default="/opt/jboss")
    parser.add_argument("--instance-name-prefix", default="app")
    parser.add_argument("--instance-start-index", type=int, default=1)
    parser.add_argument("--base-http-port", type=int, default=8080)
    parser.add_argument("--port-stride", type=int, default=100)
    parser.add_argument("--health-path", default="/")
    parser.add_argument("--health-timeout-seconds", type=float, default=2.0)
    parser.add_argument("--min-instances", type=int, default=1)
    parser.add_argument("--max-instances", type=int, default=10)
    parser.add_argument("--scale-up-cpu-percent", type=float, default=75.0)
    parser.add_argument("--scale-down-cpu-percent", type=float, default=25.0)
    parser.add_argument("--scale-up-mem-percent", type=float, default=85.0)
    parser.add_argument("--scale-down-mem-percent", type=float, default=50.0)
    parser.add_argument("--scale-up-avg-latency-ms", type=float, default=800.0)
    parser.add_argument("--scale-down-avg-latency-ms", type=float, default=250.0)
    parser.add_argument("--consecutive-up-required", type=int, default=3)
    parser.add_argument("--consecutive-down-required", type=int, default=5)
    parser.add_argument("--cooldown-seconds", type=int, default=300)
    parser.add_argument("--loop-interval-seconds", type=int, default=60)
    parser.add_argument("--state-file", default="/tmp/jboss_autoscaler_state.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    return Config(
        inventory=args.inventory,
        playbook=args.playbook,
        ansible_bin=args.ansible_bin,
        instance_root=args.instance_root,
        instance_name_prefix=args.instance_name_prefix,
        instance_start_index=args.instance_start_index,
        base_http_port=args.base_http_port,
        port_stride=args.port_stride,
        health_path=args.health_path,
        health_timeout_seconds=args.health_timeout_seconds,
        min_instances=args.min_instances,
        max_instances=args.max_instances,
        scale_up_cpu_percent=args.scale_up_cpu_percent,
        scale_down_cpu_percent=args.scale_down_cpu_percent,
        scale_up_mem_percent=args.scale_up_mem_percent,
        scale_down_mem_percent=args.scale_down_mem_percent,
        scale_up_avg_latency_ms=args.scale_up_avg_latency_ms,
        scale_down_avg_latency_ms=args.scale_down_avg_latency_ms,
        consecutive_up_required=args.consecutive_up_required,
        consecutive_down_required=args.consecutive_down_required,
        cooldown_seconds=args.cooldown_seconds,
        loop_interval_seconds=args.loop_interval_seconds,
        state_file=args.state_file,
        dry_run=args.dry_run,
        use_llm=args.use_llm,
    ), args.once


def main() -> int:
    cfg, once = parse_args()
    log("JBoss autoscaler started")
    if once:
        return run_once(cfg)
    while True:
        rc = run_once(cfg)
        if rc != 0:
            log(f"Cycle completed with non-zero status {rc}; continuing after sleep")
        time.sleep(cfg.loop_interval_seconds)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("Interrupted")
        raise SystemExit(130)

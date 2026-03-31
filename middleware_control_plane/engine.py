from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Optional

from middleware_control_plane.adapters import get_adapter
from middleware_control_plane.config import MCPConfig
from middleware_control_plane.decision_log import append_decision_log
from middleware_control_plane.llm_policy import decide_with_llm_guardrails, to_scale_decision
from middleware_control_plane.models import ControlLoopResult, RuntimeSnapshot, ScaleDecision
from middleware_control_plane.policy import decide_with_rules, within_cooldown
from middleware_control_plane.probes import average_latency_ms, probe_instances
from middleware_control_plane.runners import invoke_ansible
from middleware_control_plane.state import ControlState
from middleware_control_plane.system_metrics import read_memory_percent, sample_cpu_percent


def log(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


class ControlPlaneEngine:
    def __init__(self, cfg: MCPConfig):
        self.cfg = cfg
        self.adapter = get_adapter(cfg.platform)

    def collect_snapshot(self, state: ControlState) -> tuple[RuntimeSnapshot, list]:
        instances = self.adapter.discover_instances(self.cfg)
        probes = probe_instances(
            instances=instances,
            port_for_instance=lambda name: self.adapter.http_port_for_instance(self.cfg, name),
            health_path=self.cfg.runtime.health_path,
            timeout_seconds=self.cfg.runtime.health_timeout_seconds,
        )
        avg_latency = average_latency_ms(probes)
        healthy_count = sum(1 for probe in probes if probe.healthy)
        snapshot = RuntimeSnapshot(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            platform=self.cfg.platform,
            instances=instances,
            current_count=len(instances),
            healthy_count=healthy_count,
            cpu_percent=sample_cpu_percent(1.0),
            memory_percent=read_memory_percent(),
            avg_latency_ms=avg_latency,
            cooldown_active=within_cooldown(state, self.cfg),
            min_instances=self.cfg.scaling.min_instances,
            max_instances=self.cfg.scaling.max_instances,
        )
        return snapshot, probes

    def decide(self, snapshot: RuntimeSnapshot, state: ControlState) -> ScaleDecision:
        if not self.cfg.llm.enabled:
            return decide_with_rules(
                cfg=self.cfg,
                state=state,
                current_count=snapshot.current_count,
                cpu_percent=snapshot.cpu_percent,
                mem_percent=snapshot.memory_percent,
                avg_latency_ms=snapshot.avg_latency_ms,
            )

        result = decide_with_llm_guardrails(
            snapshot.to_dict(),
            current_count=snapshot.current_count,
            healthy_count=snapshot.healthy_count,
            min_instances=snapshot.min_instances,
            max_instances=snapshot.max_instances,
            cooldown_active=snapshot.cooldown_active,
            model=self.cfg.llm.model,
        )
        log(f"LLM raw recommendation: {json.dumps(result['raw_recommendation'], sort_keys=True)}")
        log(f"LLM guarded recommendation: {json.dumps(result['guarded_recommendation'], sort_keys=True)}")
        return to_scale_decision(result["guarded_recommendation"], policy_source="llm_guardrails")

    def plan(self) -> tuple[ControlState, RuntimeSnapshot, list, ScaleDecision]:
        state = ControlState.load(self.cfg.state.state_file)
        snapshot, probes = self.collect_snapshot(state)
        decision = self.decide(snapshot, state)
        return state, snapshot, probes, decision

    def execute_decision(
        self,
        state: ControlState,
        snapshot: RuntimeSnapshot,
        probes: list,
        decision: ScaleDecision,
    ) -> int:
        ansible_executed = False
        ansible_return_code: Optional[int] = None
        if decision.target_count != snapshot.current_count:
            destroy_enabled = decision.target_count < snapshot.current_count
            ansible_return_code, ansible_executed, ansible_output = invoke_ansible(
                self.cfg,
                self.adapter,
                decision.target_count,
                destroy_enabled,
                dry_run=self.cfg.dry_run,
            )
            log(f"ansible result executed={ansible_executed} rc={ansible_return_code} output={ansible_output}")
            if ansible_return_code != 0:
                result = ControlLoopResult(
                    snapshot=snapshot,
                    decision=decision,
                    ansible_return_code=ansible_return_code,
                    ansible_executed=ansible_executed,
                    dry_run=self.cfg.dry_run,
                    probes=probes,
                )
                append_decision_log(self.cfg.state.decision_log_file, result)
                state.save(self.cfg.state.state_file)
                return ansible_return_code
            state.last_scale_epoch = time.time()
            state.last_target_count = decision.target_count
            state.up_streak = 0
            state.down_streak = 0

        result = ControlLoopResult(
            snapshot=snapshot,
            decision=decision,
            ansible_return_code=ansible_return_code,
            ansible_executed=ansible_executed,
            dry_run=self.cfg.dry_run,
            probes=probes,
        )
        append_decision_log(self.cfg.state.decision_log_file, result)
        state.save(self.cfg.state.state_file)
        return 0

    def scale_to(self, target_count: int, *, reason: str = "manual_api_request") -> dict:
        state = ControlState.load(self.cfg.state.state_file)
        snapshot, probes = self.collect_snapshot(state)
        target = max(self.cfg.scaling.min_instances, min(int(target_count), self.cfg.scaling.max_instances))
        action = "hold"
        if target > snapshot.current_count:
            action = "scale_up"
        elif target < snapshot.current_count:
            action = "scale_down"
        decision = ScaleDecision(
            action=action,
            target_count=target,
            reason=reason,
            confidence=1.0,
            policy_source="api_manual",
        )
        rc = self.execute_decision(state, snapshot, probes, decision)
        return {
            "return_code": rc,
            "snapshot": snapshot.to_dict(),
            "decision": asdict(decision),
            "probes": [asdict(p) for p in probes],
            "dry_run": self.cfg.dry_run,
        }

    def run_once(self) -> int:
        state, snapshot, probes, decision = self.plan()
        probe_summary = ", ".join(
            f"{probe.instance_name}:{'up' if probe.healthy else 'down'}@{probe.port}" for probe in probes
        ) or "no instances discovered"
        log(
            "platform=%s instances=%s healthy=%s cpu=%.2f%% mem=%.2f%% avg_latency_ms=%s probes=[%s]"
            % (
                self.cfg.platform,
                snapshot.current_count,
                snapshot.healthy_count,
                snapshot.cpu_percent,
                snapshot.memory_percent,
                snapshot.avg_latency_ms if snapshot.avg_latency_ms is not None else "n/a",
                probe_summary,
            )
        )

        log(
            f"decision source={decision.policy_source} current={snapshot.current_count} "
            f"target={decision.target_count} reason={decision.reason} confidence={decision.confidence:.2f}"
        )
        return self.execute_decision(state, snapshot, probes, decision)

    def run_forever(self) -> int:
        log(f"Middleware Control Plane started for platform={self.cfg.platform}")
        while True:
            rc = self.run_once()
            if rc != 0:
                log(f"Control loop completed with non-zero status {rc}; sleeping before next cycle")
            time.sleep(self.cfg.scaling.loop_interval_seconds)

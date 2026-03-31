from __future__ import annotations

from middleware_control_plane.config import MCPConfig
from middleware_control_plane.models import ScaleDecision
from middleware_control_plane.state import ControlState


def within_cooldown(state: ControlState, cfg: MCPConfig) -> bool:
    import time

    return (time.time() - state.last_scale_epoch) < cfg.scaling.cooldown_seconds


def decide_with_rules(
    *,
    cfg: MCPConfig,
    state: ControlState,
    current_count: int,
    cpu_percent: float,
    mem_percent: float,
    avg_latency_ms: float | None,
) -> ScaleDecision:
    min_instances = cfg.scaling.min_instances
    max_instances = cfg.scaling.max_instances

    if current_count < min_instances:
        return ScaleDecision(
            action="scale_up",
            target_count=min_instances,
            reason="current instance count is below configured minimum",
            confidence=1.0,
            policy_source="rules",
        )
    if current_count > max_instances:
        return ScaleDecision(
            action="scale_down",
            target_count=max_instances,
            reason="current instance count is above configured maximum",
            confidence=1.0,
            policy_source="rules",
        )

    up_signal = (
        cpu_percent >= cfg.scaling.scale_up_cpu_percent
        or mem_percent >= cfg.scaling.scale_up_mem_percent
        or (avg_latency_ms is not None and avg_latency_ms >= cfg.scaling.scale_up_avg_latency_ms)
    )
    down_signal = (
        cpu_percent <= cfg.scaling.scale_down_cpu_percent
        and mem_percent <= cfg.scaling.scale_down_mem_percent
        and (avg_latency_ms is None or avg_latency_ms <= cfg.scaling.scale_down_avg_latency_ms)
    )

    if up_signal and current_count < max_instances:
        state.up_streak += 1
        state.down_streak = 0
    elif down_signal and current_count > min_instances:
        state.down_streak += 1
        state.up_streak = 0
    else:
        state.up_streak = 0
        state.down_streak = 0

    if within_cooldown(state, cfg):
        return ScaleDecision(
            action="hold",
            target_count=current_count,
            reason="cooldown active",
            confidence=1.0,
            policy_source="rules",
        )

    if state.up_streak >= cfg.scaling.consecutive_up_required and current_count < max_instances:
        return ScaleDecision(
            action="scale_up",
            target_count=current_count + 1,
            reason="scale-up thresholds exceeded for the required number of cycles",
            confidence=0.95,
            policy_source="rules",
        )

    if state.down_streak >= cfg.scaling.consecutive_down_required and current_count > min_instances:
        return ScaleDecision(
            action="scale_down",
            target_count=current_count - 1,
            reason="scale-down thresholds sustained for the required number of cycles",
            confidence=0.95,
            policy_source="rules",
        )

    bootstrap_floor = cfg.scaling.desired_floor_at_bootstrap
    if bootstrap_floor is not None and current_count < bootstrap_floor:
        return ScaleDecision(
            action="scale_up",
            target_count=min(bootstrap_floor, max_instances),
            reason="bootstrap floor requested in configuration",
            confidence=1.0,
            policy_source="rules",
        )

    return ScaleDecision(
        action="hold",
        target_count=current_count,
        reason="no scaling change",
        confidence=0.75,
        policy_source="rules",
    )

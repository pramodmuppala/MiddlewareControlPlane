#!/usr/bin/env python3
"""
LLM policy module for tomcat_autoscaler.py.

Install:
  pip install openai pydantic

Environment:
  export OPENAI_API_KEY=...
  export OPENAI_MODEL=gpt-5.4
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from openai import OpenAI
from pydantic import BaseModel, Field


Action = Literal["scale_up", "scale_down", "hold"]


class ScaleDecision(BaseModel):
    action: Action
    target_count: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=600)
    confidence: float = Field(ge=0.0, le=1.0)


@dataclass
class GuardrailConfig:
    min_instances: int = 1
    max_instances: int = 10
    max_step_change: int = 1
    block_scale_down_when_unhealthy: bool = True
    minimum_healthy_fraction_for_scale_down: float = 1.0


SYSTEM_PROMPT = """You are an infrastructure scaling policy assistant.

You receive a JSON snapshot for a Tomcat multi-instance deployment.
Recommend exactly one of:
- scale_up
- scale_down
- hold

Rules:
- Be conservative.
- Prefer hold when evidence is mixed or weak.
- Recommend scale_up when load is sustained and capacity is likely insufficient.
- Recommend scale_down only when load is clearly low and stable.
- Never recommend a target_count below min_instances or above max_instances.
- Return only the structured result.
"""


def _make_user_prompt(snapshot: Dict[str, Any]) -> str:
    return (
        "Evaluate this Tomcat scaling snapshot and recommend one action.\n\n"
        f"{json.dumps(snapshot, indent=2, sort_keys=True)}"
    )


def get_llm_recommendation(
    snapshot: Dict[str, Any],
    *,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    chosen_model = model or os.getenv("OPENAI_MODEL", "gpt-5.4")

    api_client = client or OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    response = api_client.responses.parse(
        model=chosen_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _make_user_prompt(snapshot)},
        ],
        text_format=ScaleDecision,
    )

    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("LLM returned no parsed structured output")

    if isinstance(parsed, ScaleDecision):
        return parsed.model_dump()

    if isinstance(parsed, BaseModel):
        return parsed.model_dump()

    if isinstance(parsed, dict):
        return ScaleDecision(**parsed).model_dump()

    raise RuntimeError(f"Unexpected parsed response type: {type(parsed)!r}")


def apply_guardrails(
    recommendation: Dict[str, Any],
    *,
    current_count: int,
    healthy_count: int,
    cfg: GuardrailConfig,
    cooldown_active: bool = False,
) -> Dict[str, Any]:
    decision = ScaleDecision(**recommendation)

    target = max(cfg.min_instances, min(decision.target_count, cfg.max_instances))

    if cooldown_active:
        return {
            "action": "hold",
            "target_count": current_count,
            "reason": f"Cooldown active; original LLM reason: {decision.reason}",
            "confidence": decision.confidence,
        }

    if decision.action == "hold":
        target = current_count
    elif decision.action == "scale_up":
        if target <= current_count:
            target = min(current_count + 1, cfg.max_instances)
    elif decision.action == "scale_down":
        if target >= current_count:
            target = max(current_count - 1, cfg.min_instances)

    delta = target - current_count
    if abs(delta) > cfg.max_step_change:
        target = (
            current_count + cfg.max_step_change
            if delta > 0
            else current_count - cfg.max_step_change
        )

    if cfg.block_scale_down_when_unhealthy and target < current_count:
        healthy_fraction = (healthy_count / current_count) if current_count > 0 else 1.0
        if healthy_fraction < cfg.minimum_healthy_fraction_for_scale_down:
            return {
                "action": "hold",
                "target_count": current_count,
                "reason": (
                    "Scale-down blocked because instance health is below threshold; "
                    f"original LLM reason: {decision.reason}"
                ),
                "confidence": decision.confidence,
            }

    if target > current_count:
        final_action: Action = "scale_up"
    elif target < current_count:
        final_action = "scale_down"
    else:
        final_action = "hold"

    return {
        "action": final_action,
        "target_count": target,
        "reason": decision.reason,
        "confidence": decision.confidence,
    }


def decide_with_llm_guardrails(
    snapshot: Dict[str, Any],
    *,
    current_count: int,
    healthy_count: int,
    min_instances: int,
    max_instances: int,
    cooldown_active: bool,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    raw = get_llm_recommendation(snapshot, model=model, client=client)

    guarded = apply_guardrails(
        raw,
        current_count=current_count,
        healthy_count=healthy_count,
        cfg=GuardrailConfig(
            min_instances=min_instances,
            max_instances=max_instances,
            max_step_change=1,
            block_scale_down_when_unhealthy=True,
            minimum_healthy_fraction_for_scale_down=1.0,
        ),
        cooldown_active=cooldown_active,
    )

    return {
        "raw_recommendation": raw,
        "guarded_recommendation": guarded,
    }


if __name__ == "__main__":
    example_snapshot = {
        "timestamp": "2026-03-21T01:00:00Z",
        "instances": ["app1", "app2", "app3"],
        "current_count": 3,
        "healthy_count": 3,
        "cpu_percent": 82.4,
        "memory_percent": 74.1,
        "avg_latency_ms": 912.0,
        "cooldown_active": False,
        "min_instances": 1,
        "max_instances": 5,
        "allowed_actions": ["scale_up", "scale_down", "hold"],
    }

    result = decide_with_llm_guardrails(
        example_snapshot,
        current_count=3,
        healthy_count=3,
        min_instances=1,
        max_instances=5,
        cooldown_active=False,
    )
    print(json.dumps(result, indent=2))

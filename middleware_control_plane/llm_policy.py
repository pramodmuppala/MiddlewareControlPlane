from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency at import time
    OpenAI = None

from middleware_control_plane.models import ScaleDecision

Action = Literal["scale_up", "scale_down", "hold"]


class StructuredScaleDecision(BaseModel):
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

You receive a JSON snapshot for a middleware deployment.
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
        "Evaluate this middleware scaling snapshot and recommend one action.\n\n"
        f"{json.dumps(snapshot, indent=2, sort_keys=True)}"
    )


def get_llm_recommendation(
    snapshot: Dict[str, Any],
    *,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    chosen_model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if client is None:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed; install requirements.txt to use llm mode")
        api_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        api_client = client

    response = api_client.responses.parse(
        model=chosen_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _make_user_prompt(snapshot)},
        ],
        text_format=StructuredScaleDecision,
    )

    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("LLM returned no parsed structured output")
    if isinstance(parsed, StructuredScaleDecision):
        return parsed.model_dump()
    if isinstance(parsed, BaseModel):
        return parsed.model_dump()
    if isinstance(parsed, dict):
        return StructuredScaleDecision(**parsed).model_dump()
    raise RuntimeError(f"Unexpected parsed response type: {type(parsed)!r}")


def apply_guardrails(
    recommendation: Dict[str, Any],
    *,
    current_count: int,
    healthy_count: int,
    cfg: GuardrailConfig,
    cooldown_active: bool = False,
) -> Dict[str, Any]:
    decision = StructuredScaleDecision(**recommendation)
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
    elif decision.action == "scale_up" and target <= current_count:
        target = min(current_count + 1, cfg.max_instances)
    elif decision.action == "scale_down" and target >= current_count:
        target = max(current_count - 1, cfg.min_instances)

    delta = target - current_count
    if abs(delta) > cfg.max_step_change:
        target = current_count + cfg.max_step_change if delta > 0 else current_count - cfg.max_step_change

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

    final_action: Action
    if target > current_count:
        final_action = "scale_up"
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
    return {"raw_recommendation": raw, "guarded_recommendation": guarded}


def to_scale_decision(guarded_result: Dict[str, Any], *, policy_source: str) -> ScaleDecision:
    return ScaleDecision(
        action=guarded_result["action"],
        target_count=int(guarded_result["target_count"]),
        reason=str(guarded_result["reason"]),
        confidence=float(guarded_result.get("confidence", 0.5)),
        policy_source=policy_source,
    )

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

Action = Literal["scale_up", "scale_down", "hold"]


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
class RuntimeSnapshot:
    timestamp: str
    platform: str
    instances: List[str]
    current_count: int
    healthy_count: int
    cpu_percent: float
    memory_percent: float
    avg_latency_ms: Optional[float]
    cooldown_active: bool
    min_instances: int
    max_instances: int
    allowed_actions: List[Action] = field(default_factory=lambda: ["scale_up", "scale_down", "hold"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScaleDecision:
    action: Action
    target_count: int
    reason: str
    confidence: float = 1.0
    policy_source: str = "rules"


@dataclass
class ControlLoopResult:
    snapshot: RuntimeSnapshot
    decision: ScaleDecision
    ansible_return_code: Optional[int]
    ansible_executed: bool
    dry_run: bool
    probes: List[ProbeResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "decision": asdict(self.decision),
            "ansible_return_code": self.ansible_return_code,
            "ansible_executed": self.ansible_executed,
            "dry_run": self.dry_run,
            "probes": [asdict(probe) for probe in self.probes],
        }

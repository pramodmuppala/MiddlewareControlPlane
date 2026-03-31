from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ControlState:
    up_streak: int = 0
    down_streak: int = 0
    last_scale_epoch: float = 0.0
    last_target_count: Optional[int] = None

    @classmethod
    def load(cls, path: str) -> "ControlState":
        file_path = Path(path)
        if not file_path.exists():
            return cls()
        try:
            return cls(**json.loads(file_path.read_text(encoding="utf-8")))
        except Exception:
            return cls()

    def save(self, path: str) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

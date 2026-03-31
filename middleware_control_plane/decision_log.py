from __future__ import annotations

import json
from pathlib import Path

from middleware_control_plane.models import ControlLoopResult


def append_decision_log(path: str, result: ControlLoopResult) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), sort_keys=True) + "\n")

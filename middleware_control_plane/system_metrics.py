from __future__ import annotations

import time
from typing import Dict, Tuple

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    psutil = None


def _read_cpu_times_from_proc() -> Tuple[int, int]:
    with open("/proc/stat", "r", encoding="utf-8") as handle:
        first = handle.readline().strip().split()
    values = list(map(int, first[1:]))
    idle = values[3] + values[4]
    total = sum(values)
    return idle, total


def sample_cpu_percent(sample_seconds: float = 1.0) -> float:
    if psutil is not None:
        return round(float(psutil.cpu_percent(interval=sample_seconds)), 2)

    idle1, total1 = _read_cpu_times_from_proc()
    time.sleep(sample_seconds)
    idle2, total2 = _read_cpu_times_from_proc()
    delta_idle = idle2 - idle1
    delta_total = total2 - total1
    if delta_total <= 0:
        return 0.0
    busy = max(delta_total - delta_idle, 0)
    return round((busy / delta_total) * 100.0, 2)


def read_memory_percent() -> float:
    if psutil is not None:
        return round(float(psutil.virtual_memory().percent), 2)

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

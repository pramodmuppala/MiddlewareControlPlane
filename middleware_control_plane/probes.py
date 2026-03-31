from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Iterable, List, Optional, Tuple

from middleware_control_plane.models import ProbeResult


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


def probe_instances(*, instances: Iterable[str], port_for_instance, health_path: str, timeout_seconds: float) -> List[ProbeResult]:
    path = health_path if health_path.startswith("/") else f"/{health_path}"
    results: List[ProbeResult] = []
    for name in instances:
        port = port_for_instance(name)
        url = f"http://127.0.0.1:{port}{path}"
        healthy, status_code, latency_ms, error = probe_url(url, timeout_seconds)
        results.append(
            ProbeResult(
                instance_name=name,
                port=port,
                url=url,
                healthy=healthy,
                status_code=status_code,
                latency_ms=latency_ms,
                error=error,
            )
        )
    return results


def average_latency_ms(results: Iterable[ProbeResult]) -> Optional[float]:
    samples = [result.latency_ms for result in results if result.healthy and result.latency_ms is not None]
    return round(sum(samples) / len(samples), 2) if samples else None

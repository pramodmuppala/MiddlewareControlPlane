from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional


@dataclass
class RequestResult:
    status_code: Optional[int]
    latency_ms: Optional[float]
    ok: bool
    error: Optional[str]


@dataclass
class BenchmarkSummary:
    url: str
    concurrency: int
    total_requests: int
    successes: int
    failures: int
    success_rate: float
    elapsed_seconds: float
    achieved_rps: float
    avg_latency_ms: Optional[float]
    p50_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]
    p99_latency_ms: Optional[float]
    min_latency_ms: Optional[float]
    max_latency_ms: Optional[float]
    status_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


_lock = threading.Lock()


def _percentile(values: List[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[int(rank)], 2)
    weight = rank - lower
    value = ordered[lower] * (1 - weight) + ordered[upper] * weight
    return round(value, 2)


def _one_request(url: str, timeout_seconds: float) -> RequestResult:
    started = time.perf_counter()
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            latency_ms = (time.perf_counter() - started) * 1000.0
            status_code = getattr(response, "status", None) or response.getcode()
            return RequestResult(status_code=status_code, latency_ms=round(latency_ms, 2), ok=200 <= status_code < 400, error=None)
    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - started) * 1000.0
        return RequestResult(status_code=exc.code, latency_ms=round(latency_ms, 2), ok=False, error=str(exc))
    except Exception as exc:
        return RequestResult(status_code=None, latency_ms=None, ok=False, error=str(exc))


def run_benchmark(url: str, *, concurrency: int, total_requests: int, timeout_seconds: float) -> BenchmarkSummary:
    started = time.perf_counter()
    results: List[RequestResult] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_one_request, url, timeout_seconds) for _ in range(total_requests)]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = max(time.perf_counter() - started, 0.0001)

    latencies = [r.latency_ms for r in results if r.latency_ms is not None]
    successes = sum(1 for r in results if r.ok)
    failures = len(results) - successes
    status_counts: Dict[str, int] = {}
    for result in results:
        key = str(result.status_code if result.status_code is not None else "error")
        status_counts[key] = status_counts.get(key, 0) + 1

    return BenchmarkSummary(
        url=url,
        concurrency=concurrency,
        total_requests=len(results),
        successes=successes,
        failures=failures,
        success_rate=round((successes / len(results)) * 100.0, 2) if results else 0.0,
        elapsed_seconds=round(elapsed, 2),
        achieved_rps=round(len(results) / elapsed, 2),
        avg_latency_ms=round(mean(latencies), 2) if latencies else None,
        p50_latency_ms=_percentile(latencies, 0.50),
        p95_latency_ms=_percentile(latencies, 0.95),
        p99_latency_ms=_percentile(latencies, 0.99),
        min_latency_ms=round(min(latencies), 2) if latencies else None,
        max_latency_ms=round(max(latencies), 2) if latencies else None,
        status_counts=status_counts,
    )


def write_benchmark_outputs(summary: BenchmarkSummary, *, output_dir: str) -> Dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = path / f"benchmark-{timestamp}.json"
    md_path = path / f"benchmark-{timestamp}.md"
    json_path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
    md_path.write_text(_markdown_report(summary), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _markdown_report(summary: BenchmarkSummary) -> str:
    return f"""# Benchmark Report

- URL: `{summary.url}`
- Concurrency: `{summary.concurrency}`
- Total requests: `{summary.total_requests}`
- Success rate: `{summary.success_rate}%`
- Elapsed seconds: `{summary.elapsed_seconds}`
- Achieved RPS: `{summary.achieved_rps}`

## Latency

- Average: `{summary.avg_latency_ms}` ms
- P50: `{summary.p50_latency_ms}` ms
- P95: `{summary.p95_latency_ms}` ms
- P99: `{summary.p99_latency_ms}` ms
- Min: `{summary.min_latency_ms}` ms
- Max: `{summary.max_latency_ms}` ms

## Status counts

```json
{json.dumps(summary.status_counts, indent=2, sort_keys=True)}
```
"""

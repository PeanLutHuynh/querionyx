"""Lightweight metrics helpers for low-resource Querionyx evaluation."""

from __future__ import annotations

import os
import statistics
import time
from contextlib import contextmanager
from typing import Dict, Iterable, Iterator, List, Optional


def percentile(values: Iterable[float], pct: float) -> Optional[float]:
    ordered = sorted(float(v) for v in values if v is not None)
    if not ordered:
        return None
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)


def latency_summary(values: Iterable[float]) -> Dict[str, Optional[float]]:
    numbers = [float(v) for v in values if v is not None]
    if not numbers:
        return {"avg": None, "p50": None, "p95": None, "p99": None}
    return {
        "avg": round(statistics.fmean(numbers), 2),
        "p50": percentile(numbers, 0.50),
        "p95": percentile(numbers, 0.95),
        "p99": percentile(numbers, 0.99),
    }


def process_resource_snapshot() -> Dict[str, Optional[float]]:
    try:
        import psutil  # type: ignore

        proc = psutil.Process(os.getpid())
        return {
            "cpu_percent": round(proc.cpu_percent(interval=0.01), 2),
            "ram_mb": round(proc.memory_info().rss / (1024 * 1024), 2),
        }
    except Exception:
        return {"cpu_percent": None, "ram_mb": None}


@contextmanager
def timed() -> Iterator[Dict[str, float]]:
    holder: Dict[str, float] = {}
    started = time.perf_counter()
    try:
        yield holder
    finally:
        holder["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)

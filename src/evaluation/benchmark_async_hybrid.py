"""Benchmark sequential versus async hybrid branch execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.benchmark_runner import load_dataset
from src.hybrid.hybrid_handler import HybridQueryHandler
from src.runtime.config import RuntimeConfig
from src.runtime.logging import write_csv, write_json, write_markdown
from src.runtime.schemas import now_iso


async def run_mode(question: str, parallel_enabled: bool) -> Dict[str, Any]:
    config = RuntimeConfig.from_env()
    config.parallel_enabled = parallel_enabled
    handler = HybridQueryHandler(runtime_config=config)
    started = time.perf_counter()
    output = await handler.aquery(question, router_intent="HYBRID")
    return {
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "rag_latency_ms": (output.get("trace") or {}).get("rag_latency_ms"),
        "sql_latency_ms": (output.get("trace") or {}).get("sql_latency_ms"),
        "fusion_latency_ms": (output.get("trace") or {}).get("fusion_latency_ms"),
        "fallback_mode": output.get("fallback_mode"),
        "rag_status": output.get("rag_status"),
        "sql_status": output.get("sql_status"),
    }


async def benchmark(dataset_path: Path, output_dir: Path, limit: int) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        case for case in load_dataset(dataset_path)
        if str(case.get("ground_truth_intent", "")).upper() == "HYBRID"
    ][:limit]
    rows: List[Dict[str, Any]] = []
    for case in cases:
        question = case["question"]
        for mode, parallel in [("sequential", False), ("async", True)]:
            result = await run_mode(question, parallel)
            row = {"query_id": case.get("id"), "mode": mode, "question": question, **result}
            rows.append(row)
            print(f"{case.get('id')} {mode}: {result['latency_ms']}ms")

    summary = summarize(rows)
    write_json(output_dir / "async_hybrid_detailed.json", {"timestamp": now_iso(), "summary": summary, "results": rows})
    write_csv(output_dir / "async_hybrid_detailed.csv", rows)
    write_markdown(output_dir / "async_vs_sequential.md", markdown_summary(summary))
    return summary


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for mode in ["sequential", "async"]:
        values = sorted(float(row["latency_ms"]) for row in rows if row["mode"] == mode)
        if not values:
            continue
        summary[mode] = {
            "queries": len(values),
            "p50_ms": percentile(values, 0.50),
            "p95_ms": percentile(values, 0.95),
            "avg_ms": round(sum(values) / len(values), 2),
        }
    if "sequential" in summary and "async" in summary:
        seq = summary["sequential"]["p50_ms"]
        async_p50 = summary["async"]["p50_ms"]
        summary["speedup_p50"] = round(seq / async_p50, 3) if async_p50 else None
    return summary


def percentile(values: List[float], pct: float) -> float:
    if len(values) == 1:
        return round(values[0], 2)
    rank = (len(values) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(values) - 1)
    weight = rank - lower
    return round(values[lower] * (1 - weight) + values[upper] * weight, 2)


def markdown_summary(summary: Dict[str, Any]) -> str:
    lines = [
        "# Async Hybrid Benchmark",
        "",
        f"**Timestamp**: {now_iso()}",
        "",
        "| Mode | Queries | P50 (ms) | P95 (ms) | Average (ms) |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode in ["sequential", "async"]:
        if mode in summary:
            m = summary[mode]
            lines.append(f"| {mode} | {m['queries']} | {m['p50_ms']:.2f} | {m['p95_ms']:.2f} | {m['avg_ms']:.2f} |")
    if summary.get("speedup_p50"):
        lines.extend(["", f"Async P50 speedup: {summary['speedup_p50']}x"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark async hybrid execution.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "metrics" / "async_hybrid")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(benchmark(args.dataset, args.output, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

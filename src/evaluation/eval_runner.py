"""Run Querionyx V3 ablation configurations against one benchmark dataset."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.benchmark_runner import run_benchmark
from src.runtime.logging import write_csv, write_json


DEFAULT_CONFIGS = [
    "full_v3",
    "no_cache",
    "no_parallel",
    "no_hybrid",
    "force_merge_llm",
    "full_rag_mode",
    "sql_only_mode",
    "rag_only_mode",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Querionyx ablation evaluation.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "benchmarks" / "datasets" / "smoke_9_queries.json")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "benchmarks" / "manifests" / "default_manifest.json")
    parser.add_argument("--configs-dir", type=Path, default=PROJECT_ROOT / "ablation" / "configs")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-latency-ms", type=int, default=8000)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    root = args.output_dir or PROJECT_ROOT / "reports" / "experiment_runs" / f"{time.strftime('%Y%m%d_%H%M%S')}_ablation"
    rows = []
    for name in DEFAULT_CONFIGS:
        config_path = args.configs_dir / f"{name}.json"
        run_dir = root / name
        print(f"\n=== Running {name} ===")
        summary = run_benchmark(args.dataset, config_path, args.manifest, run_dir, args.seed, args.max_latency_ms, args.limit)
        rows.append(
            {
                "config_name": name,
                "pass_rate": summary["pass_rate"],
                "avg_latency": summary["latency"]["avg"],
                "p50_latency": summary["latency"]["p50"],
                "p95_latency": summary["latency"]["p95"],
                "p99_latency": summary["latency"]["p99"],
                "avg_ram_mb": summary["avg_ram_mb"],
                "llm_calls_avg": summary["llm_calls_avg"],
                "timeout_rate": summary["timeout_rate"],
                "fallback_rate": summary["fallback_rate"],
                "sql_success_rate": summary["sql_success_rate"],
                "hybrid_success_rate": summary["hybrid_success_rate"],
                "cache_hit_rate": summary["cache_hit_rate"],
                "startup_ms": summary["startup_ms"],
            }
        )
    write_json(root / "ablation_summary.json", rows)
    write_csv(root / "ablation_summary.csv", rows)
    write_csv(PROJECT_ROOT / "reports" / "tables" / "ablation_summary.csv", rows)


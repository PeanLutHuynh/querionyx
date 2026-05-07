"""Build paper-ready CSV tables from Week 7 evaluation artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from src.runtime.logging import write_csv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_tables(uat_json: Path, router_json: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    uat_payload = json.loads(uat_json.read_text(encoding="utf-8"))
    router_payload = json.loads(router_json.read_text(encoding="utf-8"))

    summary = uat_payload["summary"]
    rows = uat_payload["rows"]

    overall = [
        {
            "non_crash_rate": summary["non_crash_rate"],
            "non_empty_rate": summary["non_empty_rate"],
            "timeout_rate": summary["timeout_rate"],
            "cache_hit_rate": summary["cache_hit_rate"],
            "avg_latency_ms": summary["latency"]["avg"],
            "p50_latency_ms": summary["latency"]["p50"],
            "p95_latency_ms": summary["latency"]["p95"],
            "p99_latency_ms": summary["latency"]["p99"],
        }
    ]
    write_csv(output_dir / "overall_performance.csv", overall)

    by_intent = []
    for intent, item in summary["performance_by_intent"].items():
        by_intent.append(
            {
                "intent": intent,
                "query_count": item["query_count"],
                "success_rate": item["success_rate"],
                "avg_latency_ms": item["latency"]["avg"],
                "p50_latency_ms": item["latency"]["p50"],
                "p95_latency_ms": item["latency"]["p95"],
                "p99_latency_ms": item["latency"]["p99"],
                "cache_hit_rate": item["cache_hit_rate"],
            }
        )
    write_csv(output_dir / "performance_by_intent.csv", by_intent)

    cache_impact = [
        {
            "phase": "first_run",
            "avg_latency_ms": summary["first_run_latency"]["avg"],
            "p50_latency_ms": summary["first_run_latency"]["p50"],
            "p95_latency_ms": summary["first_run_latency"]["p95"],
            "p99_latency_ms": summary["first_run_latency"]["p99"],
        },
        {
            "phase": "cached_run",
            "avg_latency_ms": summary["cached_run_latency"]["avg"],
            "p50_latency_ms": summary["cached_run_latency"]["p50"],
            "p95_latency_ms": summary["cached_run_latency"]["p95"],
            "p99_latency_ms": summary["cached_run_latency"]["p99"],
        },
    ]
    write_csv(output_dir / "cache_impact.csv", cache_impact)

    confusion = []
    for expected, cols in router_payload["confusion_matrix"].items():
        row = {"expected_intent": expected}
        row.update(cols)
        confusion.append(row)
    write_csv(output_dir / "router_confusion_matrix.csv", confusion)

    per_class = []
    for label, metrics in router_payload["per_class"].items():
        per_class.append({"intent": label, **metrics})
    write_csv(output_dir / "router_per_class.csv", per_class)

    misrouting = [{"category": key, "count": value} for key, value in router_payload["misrouting_breakdown"].items()]
    write_csv(output_dir / "router_misrouting_breakdown.csv", misrouting)

    failure_taxonomy = [{"failure_type": key, "count": value} for key, value in summary["failure_taxonomy"].items()]
    write_csv(output_dir / "failure_taxonomy.csv", failure_taxonomy)

    hybrid_modes = _hybrid_modes(rows)
    write_csv(output_dir / "hybrid_modes.csv", hybrid_modes)


def _hybrid_modes(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for row in rows:
        if row.get("repeated"):
            continue
        if str(row.get("intent") or "").upper() != "HYBRID":
            continue
        mode = str(row.get("hybrid_branch_usage") or "unknown")
        counts[mode] = counts.get(mode, 0) + 1
    return [{"hybrid_branch_usage": key, "count": value} for key, value in sorted(counts.items())]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build paper-ready CSV tables for Week 7.")
    parser.add_argument("--uat-json", type=Path, default=PROJECT_ROOT / "reports" / "experiment_runs" / "week7_uat_90_paper" / "uat_results.json")
    parser.add_argument("--router-json", type=Path, default=PROJECT_ROOT / "reports" / "experiment_runs" / "week7_router_stress_100" / "router_stress_summary.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "tables")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_tables(args.uat_json, args.router_json, args.output_dir)

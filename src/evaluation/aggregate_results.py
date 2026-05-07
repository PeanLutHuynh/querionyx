"""Aggregate Querionyx benchmark query logs into paper-ready metrics."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.runtime.logging import read_jsonl, write_csv, write_json
from src.runtime.metrics import latency_summary


def aggregate(query_rows: List[Dict[str, Any]], failure_rows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    failure_rows = failure_rows or []
    latencies = [row.get("latency_ms") for row in query_rows if row.get("latency_ms") is not None]
    summary = latency_summary(latencies)
    total = len(query_rows)
    passed = sum(1 for row in query_rows if row.get("passed") is True)
    by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in query_rows:
        by_intent[str(row.get("expected_intent") or row.get("intent") or "UNKNOWN")].append(row)

    def rate(predicate) -> float:
        return round(sum(1 for row in query_rows if predicate(row)) / total, 4) if total else 0.0

    result = {
        "query_count": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "latency": summary,
        "avg_ram_mb": _avg([row.get("ram_mb") for row in query_rows]),
        "avg_cpu_percent": _avg([row.get("cpu_percent") for row in query_rows]),
        "llm_calls_avg": _avg([row.get("llm_calls") for row in query_rows]) or 0.0,
        "timeout_rate": rate(lambda row: row.get("timeout_triggered") is True),
        "fallback_rate": rate(lambda row: row.get("fallback_used") is True),
        "empty_answer_rate": rate(lambda row: row.get("answer_nonempty") is False),
        "cache_hit_rate": rate(lambda row: row.get("cache_hit") is True),
        "sql_success_rate": _conditional_success_rate(
            query_rows,
            lambda row: row.get("expected_intent") in {"SQL", "HYBRID"} or "sql" in (row.get("branches_used") or []),
            "sql_success",
        ),
        "rag_success_rate": _conditional_success_rate(
            query_rows,
            lambda row: row.get("expected_intent") in {"RAG", "HYBRID"} or "rag" in (row.get("branches_used") or []),
            "rag_success",
        ),
        "hybrid_success_rate": _intent_pass_rate(query_rows, "HYBRID"),
        "router_accuracy": rate(lambda row: row.get("expected_intent") in {None, "", row.get("intent")}),
        "failure_counts": dict(Counter(row.get("failure_type") for row in failure_rows)),
        "resolved_failure_rate": _resolved_failure_rate(failure_rows),
        "per_intent": {},
    }
    for intent, rows in by_intent.items():
        result["per_intent"][intent] = {
            "query_count": len(rows),
            "pass_rate": round(sum(1 for row in rows if row.get("passed") is True) / len(rows), 4) if rows else 0.0,
            "latency": latency_summary(row.get("latency_ms") for row in rows),
            "fallback_rate": round(sum(1 for row in rows if row.get("fallback_used") is True) / len(rows), 4) if rows else 0.0,
        }
    return result


def flatten_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    row = {
        "query_count": summary["query_count"],
        "pass_rate": summary["pass_rate"],
        "avg_latency": summary["latency"]["avg"],
        "p50_latency": summary["latency"]["p50"],
        "p95_latency": summary["latency"]["p95"],
        "p99_latency": summary["latency"]["p99"],
        "avg_ram_mb": summary["avg_ram_mb"],
        "avg_cpu_percent": summary["avg_cpu_percent"],
        "llm_calls_avg": summary["llm_calls_avg"],
        "timeout_rate": summary["timeout_rate"],
        "fallback_rate": summary["fallback_rate"],
        "empty_answer_rate": summary["empty_answer_rate"],
        "cache_hit_rate": summary["cache_hit_rate"],
        "sql_success_rate": summary["sql_success_rate"],
        "rag_success_rate": summary["rag_success_rate"],
        "hybrid_success_rate": summary["hybrid_success_rate"],
        "router_accuracy": summary["router_accuracy"],
    }
    return [row]


def write_summary_markdown(path: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Benchmark Summary",
        "",
        f"- Query count: {summary['query_count']}",
        f"- Pass rate: {summary['pass_rate']}",
        f"- Avg latency: {summary['latency']['avg']} ms",
        f"- p50 latency: {summary['latency']['p50']} ms",
        f"- p95 latency: {summary['latency']['p95']} ms",
        f"- p99 latency: {summary['latency']['p99']} ms",
        f"- LLM calls/query: {summary['llm_calls_avg']}",
        f"- Timeout rate: {summary['timeout_rate']}",
        f"- Fallback rate: {summary['fallback_rate']}",
        f"- Cache hit rate: {summary['cache_hit_rate']}",
        "",
        "## Per Intent",
        "",
        "| Intent | Queries | Pass Rate | Avg Latency | p95 Latency | Fallback Rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for intent, row in summary["per_intent"].items():
        lines.append(
            f"| {intent} | {row['query_count']} | {row['pass_rate']} | "
            f"{row['latency']['avg']} | {row['latency']['p95']} | {row['fallback_rate']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _avg(values: List[Any]) -> Optional[float]:
    numbers = [float(v) for v in values if v is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 4)


def _intent_pass_rate(rows: List[Dict[str, Any]], intent: str) -> float:
    selected = [row for row in rows if row.get("expected_intent") == intent]
    if not selected:
        return 0.0
    return round(sum(1 for row in selected if row.get("passed") is True) / len(selected), 4)


def _conditional_success_rate(rows: List[Dict[str, Any]], selector, field: str) -> float:
    selected = [row for row in rows if selector(row) and row.get(field) is not None]
    if not selected:
        return 0.0
    return round(sum(1 for row in selected if row.get(field) is True) / len(selected), 4)


def _resolved_failure_rate(rows: List[Dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if row.get("resolved") is True) / len(rows), 4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate Querionyx benchmark logs.")
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    queries = read_jsonl(args.run_dir / "query_logs.jsonl")
    failures = read_jsonl(args.run_dir / "failure_logs.jsonl")
    output = aggregate(queries, failures)
    write_json(args.run_dir / "results.json", output)
    write_csv(args.run_dir / "results.csv", flatten_summary(output))
    write_summary_markdown(args.run_dir / "summary.md", output)

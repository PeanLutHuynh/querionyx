"""Benchmark sequential versus async hybrid branch execution."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.benchmark_runner import load_dataset
from src.evaluation.evidence import REAL_EXECUTION_MODES, build_experiment_manifest, git_state
from src.hybrid.hybrid_handler import HybridQueryHandler
from src.runtime.config import RuntimeConfig
from src.runtime.logging import write_csv, write_json, write_markdown
from src.runtime.schemas import now_iso


async def run_mode(question: str, parallel_enabled: bool, execution_mode: str) -> Dict[str, Any]:
    config = RuntimeConfig.from_env()
    config.execution_mode = execution_mode
    config.parallel_enabled = parallel_enabled
    handler = HybridQueryHandler(runtime_config=config)
    started = time.perf_counter()
    output = await handler.aquery(question, router_intent="HYBRID")
    rag_result = output.get("rag_result") or {}
    sql_result = output.get("sql_result") or {}
    canonical_output = {
        "answer": normalize_text(output.get("answer")),
        "sources": sorted(str(value) for value in output.get("sources") or []),
        "sql_rows": sql_result.get("rows") or [],
        "citations": sorted(str(value) for value in rag_result.get("citations") or []),
        "contribution": output.get("contribution"),
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            canonical_output,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=json_safe_default,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "rag_latency_ms": (output.get("trace") or {}).get("rag_latency_ms"),
        "sql_latency_ms": (output.get("trace") or {}).get("sql_latency_ms"),
        "fusion_latency_ms": (output.get("trace") or {}).get("fusion_latency_ms"),
        "fallback_mode": output.get("fallback_mode"),
        "rag_status": output.get("rag_status"),
        "sql_status": output.get("sql_status"),
        "answer": output.get("answer") or "",
        "sources": json.dumps(output.get("sources") or [], ensure_ascii=False),
        "sql_rows": json.dumps(
            sql_result.get("rows") or [],
            ensure_ascii=False,
            sort_keys=True,
            default=json_safe_default,
        ),
        "citations": json.dumps(rag_result.get("citations") or [], ensure_ascii=False),
        "contribution": output.get("contribution"),
        "output_fingerprint": fingerprint,
    }


async def benchmark(
    dataset_path: Path,
    output_dir: Path,
    limit: int,
    execution_mode: str = "evaluation_real",
) -> Dict[str, Any]:
    run_git_state = git_state()
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        case for case in load_dataset(dataset_path)
        if str(case.get("ground_truth_intent", "")).upper() == "HYBRID"
    ][:limit]
    rows: List[Dict[str, Any]] = []
    for case in cases:
        question = case["question"]
        for mode, parallel in [("sequential", False), ("async", True)]:
            result = await run_mode(question, parallel, execution_mode)
            row = {"query_id": case.get("id"), "mode": mode, "question": question, **result}
            rows.append(row)
            print(f"{case.get('id')} {mode}: {result['latency_ms']}ms")

    annotate_pair_matches(rows)
    summary = summarize(rows)
    write_json(
        output_dir / "async_hybrid_detailed.json",
        {
            "timestamp": now_iso(),
            "execution_mode": execution_mode,
            "evidence_type": "measured",
            "summary": summary,
            "results": rows,
        },
    )
    config = RuntimeConfig.from_env()
    config.execution_mode = execution_mode
    manifest = build_experiment_manifest(
            run_id=output_dir.name,
            execution_mode=execution_mode,
            benchmark_path=dataset_path,
            config=config.to_dict(),
            query_count=len(cases),
            extra={
                "evaluation": "paired_async_hybrid",
                "paired_modes": ["sequential", "async"],
                "query_ids": [str(case.get("id")) for case in cases],
                "output_equivalence_method": "canonical_exact_fingerprint",
            },
            git_state_at_start=run_git_state,
        )
    write_json(
        output_dir / "manifest.json",
        manifest,
    )
    write_csv(output_dir / "async_hybrid_detailed.csv", rows)
    write_markdown(output_dir / "async_vs_sequential.md", markdown_summary(summary))
    write_json(
        output_dir / "async_automatic_summary.json",
        {
            "schema_version": "1.0",
            "artifact": "async_hybrid_automatic_summary",
            "evidence_type": manifest["evidence_type"],
            "thesis_reporting_allowed": manifest["thesis_reporting_allowed"],
            "equivalence_method": "canonical_exact_fingerprint",
            "summary": summary,
        },
    )
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
    pair_rows = [row for row in rows if row.get("mode") == "async"]
    summary["paired_outputs"] = len(pair_rows)
    summary["exact_output_matches"] = sum(row.get("paired_output_match") is True for row in pair_rows)
    summary["exact_output_match_rate"] = (
        round(summary["exact_output_matches"] / len(pair_rows), 4) if pair_rows else None
    )
    return summary


def annotate_pair_matches(rows: List[Dict[str, Any]]) -> None:
    fingerprints: Dict[str, Dict[str, str]] = {}
    for row in rows:
        query_id = str(row.get("query_id") or "")
        mode = str(row.get("mode") or "")
        fingerprints.setdefault(query_id, {})[mode] = str(row.get("output_fingerprint") or "")
    for row in rows:
        pair = fingerprints.get(str(row.get("query_id") or ""), {})
        row["paired_output_match"] = bool(
            pair.get("sequential")
            and pair.get("async")
            and pair["sequential"] == pair["async"]
        )


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def json_safe_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


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
    if summary.get("exact_output_match_rate") is not None:
        lines.extend(
            [
                "",
                f"Exact paired-output match rate: {summary['exact_output_match_rate']:.2%}",
                "Equivalence is measured by a canonical exact-output fingerprint.",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark async hybrid execution.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--execution-mode", choices=sorted(REAL_EXECUTION_MODES), default="evaluation_real")
    args = parser.parse_args()
    output_dir = args.output or (
        PROJECT_ROOT
        / "reports"
        / "experiment_runs"
        / f"{time.strftime('%Y%m%d_%H%M%S')}_async_hybrid"
    )
    asyncio.run(benchmark(args.dataset, output_dir, args.limit, args.execution_mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

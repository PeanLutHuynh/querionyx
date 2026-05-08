"""Deterministic benchmark runner for Querionyx V3."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.aggregate_results import aggregate, flatten_summary, write_summary_markdown
from src.evaluation.scoring import expected_intent, query_id, score_case
from src.pipeline_v3 import QueryonixPipelineV3
from src.runtime.config import RuntimeConfig
from src.runtime.error_taxonomy import classify_error
from src.runtime.logging import append_jsonl, write_csv, write_json
from src.runtime.metrics import process_resource_snapshot
from src.runtime.schemas import QueryExecutionLog, now_iso


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload.get("queries", payload)


def load_manifest(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_benchmark(
    dataset_path: Path,
    config_path: Optional[Path],
    manifest_path: Optional[Path],
    output_dir: Path,
    seed: int,
    max_latency_ms: int,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    random.seed(seed)
    manifest = load_manifest(manifest_path)
    config = RuntimeConfig.from_file(config_path) if config_path else RuntimeConfig.from_env()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "query_logs.jsonl").write_text("", encoding="utf-8")
    (output_dir / "failure_logs.jsonl").write_text("", encoding="utf-8")
    (output_dir / "per_query_traces.jsonl").write_text("", encoding="utf-8")

    dataset = load_dataset(dataset_path)
    if manifest.get("shuffle_queries"):
        random.shuffle(dataset)
    if limit:
        dataset = dataset[:limit]

    manifest_out = {
        "dataset": str(dataset_path),
        "config": config.to_dict(),
        "manifest": manifest,
        "seed": seed,
        "max_latency_ms": max_latency_ms,
        "query_count": len(dataset),
        "started_at": now_iso(),
    }
    write_json(output_dir / "manifest.json", manifest_out)
    if config_path:
        shutil.copyfile(config_path, output_dir / "ablation_config.json")

    init_started = time.perf_counter()
    pipeline = QueryonixPipelineV3(max_total_latency_ms=max_latency_ms, runtime_config=config)
    startup_ms = round((time.perf_counter() - init_started) * 1000, 2)
    write_json(
        output_dir / "cold_start.json",
        {
            "pipeline_init_ms": startup_ms,
            "timestamp": now_iso(),
            "resource_snapshot": process_resource_snapshot(),
        },
    )

    query_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    latencies: List[float] = []

    for index, case in enumerate(dataset, start=1):
        qid = query_id(case, index)
        question = case["question"]
        cold_start = index == 1
        try:
            output = pipeline.query(question)
        except Exception as exc:
            output = {
                "answer": "",
                "sources": [],
                "intent": "UNKNOWN",
                "latency_ms": None,
                "confidence": 0.0,
                "router_type_used": "uncaught_exception",
                "llm_call_count": 0,
                "branches": [],
                "fallback_used": True,
                "timeout_triggered": False,
                "sql_success": None,
                "rag_success": None,
                "merge_used": False,
                "answer_nonempty": False,
                "cache_hit": None,
                "timings": {},
                "raw": {"failures": [{"failure_type": "unexpected_exception", "stage": "pipeline", "exception": str(exc)}]},
            }

        latency = output.get("latency_ms")
        if latency is not None:
            latencies.append(float(latency))
        score = score_case(case, output, max_latency_ms=max_latency_ms)
        resources = process_resource_snapshot()
        timings = output.get("timings") or {}
        p50 = _rolling_percentile(latencies, 0.50)
        p95 = _rolling_percentile(latencies, 0.95)
        query_log = QueryExecutionLog(
            query_id=qid,
            question=question,
            intent=output.get("intent"),
            branches_used=output.get("branches") or [],
            router_type=output.get("router_type_used"),
            llm_calls=int(output.get("llm_call_count") or 0),
            latency_ms=float(latency or 0.0),
            router_latency_ms=timings.get("router_latency_ms"),
            sql_latency_ms=timings.get("sql_latency_ms"),
            rag_latency_ms=timings.get("rag_latency_ms"),
            merge_latency_ms=timings.get("merge_latency_ms"),
            formatting_latency_ms=timings.get("formatting_latency_ms"),
            p50_latency=p50,
            p95_latency=p95,
            cpu_percent=resources["cpu_percent"],
            ram_mb=resources["ram_mb"],
            cold_start=cold_start,
            timeout_triggered=bool(output.get("timeout_triggered")),
            fallback_used=bool(output.get("fallback_used")),
            sql_success=output.get("sql_success"),
            rag_success=output.get("rag_success"),
            merge_used=bool(output.get("merge_used")),
            confidence=output.get("confidence"),
            answer_nonempty=bool(output.get("answer_nonempty")),
            cache_hit=output.get("cache_hit"),
            timestamp=now_iso(),
        ).to_dict()
        query_log.update(
            {
                "expected_intent": expected_intent(case),
                "passed": score["passed"],
                "intent_ok": score["intent_ok"],
                "router_ambiguous": ((output.get("raw") or {}).get("router_trace") or {}).get("ambiguous"),
                "router_signals": ((output.get("raw") or {}).get("router_trace") or {}).get("signals"),
                "answer_preview": str(output.get("answer") or "")[:180],
            }
        )
        append_jsonl(output_dir / "query_logs.jsonl", query_log)
        query_rows.append(query_log)

        trace = build_per_query_trace(qid, case, output, score)
        append_jsonl(output_dir / "per_query_traces.jsonl", trace)

        for failure in ((output.get("raw") or {}).get("failures") or []):
            failure.setdefault("query_id", qid)
            failure.setdefault("error_type", classify_error(failure.get("stage", ""), failure.get("exception", "")))
            append_jsonl(output_dir / "failure_logs.jsonl", failure)
            failure_rows.append(failure)

        status = "OK" if score["passed"] else "FAIL"
        print(f"[{index}/{len(dataset)}] {status} {qid} expected={expected_intent(case)} actual={output.get('intent')} latency={latency}ms")

    summary = aggregate(query_rows, failure_rows)
    summary["startup_ms"] = startup_ms
    write_json(output_dir / "results.json", summary)
    write_csv(output_dir / "results.csv", flatten_summary(summary))
    write_summary_markdown(output_dir / "summary.md", summary)
    return summary


def build_per_query_trace(
    qid: str,
    case: Dict[str, Any],
    output: Dict[str, Any],
    score: Dict[str, Any],
) -> Dict[str, Any]:
    raw = output.get("raw") or {}
    router_trace = raw.get("router_trace") or {}
    hybrid = raw.get("hybrid") or {}
    hybrid_trace = hybrid.get("trace") or {}
    sql_payload = raw.get("sql") or hybrid.get("sql_result") or {}
    rag_payload = raw.get("rag") or hybrid.get("rag_result") or {}
    failures = raw.get("failures") or []
    error_types = [
        failure.get("error_type") or classify_error(failure.get("stage", ""), failure.get("exception", ""))
        for failure in failures
    ]
    if expected_intent(case) and output.get("intent") and expected_intent(case) != str(output.get("intent")).upper():
        error_types.append("misrouting")

    return {
        "query_id": qid,
        "query": case.get("question", ""),
        "true_intent": expected_intent(case),
        "router_prediction": output.get("intent"),
        "router_confidence": output.get("confidence"),
        "router_signals": router_trace.get("signals"),
        "router_ambiguous": router_trace.get("ambiguous"),
        "matched_sql_keywords": router_trace.get("matched_sql_keywords"),
        "matched_rag_keywords": router_trace.get("matched_rag_keywords"),
        "branches": output.get("branches") or [],
        "rag_status": hybrid.get("rag_status") or hybrid_trace.get("rag_status"),
        "sql_status": hybrid.get("sql_status") or hybrid_trace.get("sql_status"),
        "fallback_mode": hybrid.get("fallback_mode") or hybrid_trace.get("fallback_mode"),
        "rag_latency_ms": (rag_payload.get("timings") or {}).get("total_ms") or output.get("timings", {}).get("rag_latency_ms"),
        "sql_latency_ms": (sql_payload.get("timings") or {}).get("total_ms") or output.get("timings", {}).get("sql_latency_ms"),
        "fusion_latency_ms": hybrid_trace.get("fusion_latency_ms") or output.get("timings", {}).get("merge_latency_ms"),
        "retrieved_chunks": hybrid_trace.get("retrieved_chunks") or _compact_chunks(rag_payload),
        "generated_sql": hybrid_trace.get("generated_sql") or sql_payload.get("sql_query"),
        "sql_result": hybrid_trace.get("sql_result") or sql_payload.get("rows"),
        "final_answer": output.get("answer"),
        "answer_preview": str(output.get("answer") or "")[:240],
        "passed": score.get("passed"),
        "error_type": sorted(set(error_types)),
    }


def _compact_chunks(rag_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunks = rag_payload.get("retrieved_chunks") or rag_payload.get("context_passages") or []
    citations = rag_payload.get("citations") or []
    compact = []
    for idx, chunk in enumerate(chunks[:3]):
        if isinstance(chunk, dict):
            compact.append(
                {
                    "text": str(chunk.get("text", ""))[:300],
                    "citation": chunk.get("source") or (citations[idx] if idx < len(citations) else None),
                    "page": chunk.get("page"),
                }
            )
        else:
            compact.append({"text": str(chunk)[:300], "citation": citations[idx] if idx < len(citations) else None})
    return compact


def _rolling_percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a deterministic Querionyx V3 benchmark.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "benchmarks" / "datasets" / "smoke_9_queries.json")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "ablation" / "configs" / "full_v3.json")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "benchmarks" / "manifests" / "default_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-latency-ms", type=int, default=8000)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_name = f"{time.strftime('%Y%m%d_%H%M%S')}_{args.config.stem if args.config else 'runtime'}"
    output_dir = args.output_dir or PROJECT_ROOT / "reports" / "experiment_runs" / run_name
    run_benchmark(args.dataset, args.config, args.manifest, output_dir, args.seed, args.max_latency_ms, args.limit)

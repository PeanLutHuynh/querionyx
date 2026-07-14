"""Deterministic benchmark runner for Querionyx V3."""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.aggregate_results import aggregate, flatten_summary, write_summary_markdown
from src.evaluation.automatic_scoring import AutomaticScorer, DEFAULT_REFERENCE_PATH
from src.evaluation.evidence import build_experiment_manifest, git_state, relative_path, sha256_file
from src.evaluation.scoring import expected_intent, query_id, score_case
from src.pipeline_v3 import QuerionyxPipelineV3
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
    query_ids: Optional[List[str]] = None,
    reference_path: Optional[Path] = None,
    git_state_at_start: Optional[Tuple[Optional[str], Optional[bool]]] = None,
) -> Dict[str, Any]:
    run_git_state = git_state_at_start if git_state_at_start is not None else git_state()
    random.seed(seed)
    manifest = load_manifest(manifest_path)
    config = RuntimeConfig.from_file(config_path) if config_path else RuntimeConfig.from_env()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "query_logs.jsonl").write_text("", encoding="utf-8")
    (output_dir / "failure_logs.jsonl").write_text("", encoding="utf-8")
    (output_dir / "per_query_traces.jsonl").write_text("", encoding="utf-8")

    dataset = load_dataset(dataset_path)
    if query_ids is not None:
        by_id = {
            str(case.get("query_id") or case.get("id")): case
            for case in dataset
        }
        missing = [item for item in query_ids if item not in by_id]
        if missing:
            raise ValueError(f"Selected query IDs are missing from benchmark: {', '.join(missing)}")
        dataset = [by_id[item] for item in query_ids]
    if manifest.get("shuffle_queries"):
        random.shuffle(dataset)
    if limit:
        dataset = dataset[:limit]

    resolved_reference = reference_path
    if resolved_reference is None and dataset_path.resolve() == (PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json").resolve():
        resolved_reference = DEFAULT_REFERENCE_PATH
    automatic_scorer = AutomaticScorer(resolved_reference) if resolved_reference else None

    manifest_out = build_experiment_manifest(
        run_id=output_dir.name,
        execution_mode=config.execution_mode,
        benchmark_path=dataset_path,
        config=config.to_dict(),
        config_path=config_path,
        manifest_path=manifest_path,
        seed=seed,
        query_count=len(dataset),
        max_latency_ms=max_latency_ms,
        extra={
            # Backward-compatible fields used by replay.py.
            "dataset": str(dataset_path),
            "manifest": manifest,
            "started_at": now_iso(),
            "selected_query_ids": query_ids,
            "automatic_reference_file": relative_path(resolved_reference),
            "automatic_reference_sha256": sha256_file(resolved_reference),
            "scoring_method": "deterministic_reference_and_evidence_alignment" if automatic_scorer else "technical_only",
        },
        git_state_at_start=run_git_state,
    )
    write_json(output_dir / "manifest.json", manifest_out)
    if config_path:
        shutil.copyfile(config_path, output_dir / "run_config.json")

    init_started = time.perf_counter()
    pipeline = QuerionyxPipelineV3(max_total_latency_ms=max_latency_ms, runtime_config=config)
    startup_ms = round((time.perf_counter() - init_started) * 1000, 2)
    retrieval_warmup_ms = 0.0
    if not config.lightweight_rag and str(config.force_mode or "").upper() != "SQL":
        warmup_started = time.perf_counter()
        pipeline.warm_up_retrieval()
        retrieval_warmup_ms = round((time.perf_counter() - warmup_started) * 1000, 2)
    write_json(
        output_dir / "cold_start.json",
        {
            "pipeline_init_ms": startup_ms,
            "retrieval_warmup_ms": retrieval_warmup_ms,
            "total_startup_ms": round(startup_ms + retrieval_warmup_ms, 2),
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
        automatic_score = automatic_scorer.score(case, output) if automatic_scorer else None
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
                "execution_mode": config.execution_mode,
                "expected_intent": expected_intent(case),
                "passed": score["passed"],
                "intent_ok": score["intent_ok"],
                "router_ambiguous": ((output.get("raw") or {}).get("router_trace") or {}).get("ambiguous"),
                "router_signals": ((output.get("raw") or {}).get("router_trace") or {}).get("signals"),
                "answer_preview": str(output.get("answer") or "")[:180],
                "technical_pass": score["passed"],
                "automatic_score": automatic_score.get("automatic_score") if automatic_score else None,
                "automatic_pass": automatic_score.get("automatic_pass") if automatic_score else None,
                "sql_result_f1": ((automatic_score or {}).get("sql") or {}).get("result_f1"),
                "rag_evidence_score": ((automatic_score or {}).get("rag") or {}).get("score"),
                "hybrid_integration_score": ((automatic_score or {}).get("integration") or {}).get("score"),
            }
        )
        append_jsonl(output_dir / "query_logs.jsonl", query_log)
        query_rows.append(query_log)

        trace = build_per_query_trace(
            qid,
            case,
            output,
            score,
            execution_mode=config.execution_mode,
            automatic_score=automatic_score,
        )
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
    summary["execution_mode"] = config.execution_mode
    summary["evidence_type"] = manifest_out["evidence_type"]
    summary["thesis_reporting_allowed"] = manifest_out["thesis_reporting_allowed"]
    summary["scoring_method"] = manifest_out["scoring_method"]
    summary["automatic_reference_file"] = manifest_out["automatic_reference_file"]
    summary["automatic_reference_sha256"] = manifest_out["automatic_reference_sha256"]
    write_json(output_dir / "results.json", summary)
    write_json(
        output_dir / "automatic_summary.json",
        {
            "schema_version": "1.0",
            "artifact": "automatic_answer_quality_summary",
            "evidence_type": summary["evidence_type"],
            "thesis_reporting_allowed": summary["thesis_reporting_allowed"],
            "scoring_method": summary["scoring_method"],
            "reference_file": summary["automatic_reference_file"],
            "reference_sha256": summary["automatic_reference_sha256"],
            "summary": summary,
        },
    )
    write_csv(output_dir / "results.csv", flatten_summary(summary))
    write_summary_markdown(output_dir / "summary.md", summary)
    if automatic_scorer:
        automatic_scorer.close()
    return summary


def build_per_query_trace(
    qid: str,
    case: Dict[str, Any],
    output: Dict[str, Any],
    score: Dict[str, Any],
    execution_mode: str = "evaluation_real",
    automatic_score: Optional[Dict[str, Any]] = None,
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

    compact_chunks = hybrid_trace.get("retrieved_chunks") or _compact_chunks(rag_payload)
    retrieved_sources = _retrieved_sources(output.get("sources") or [], compact_chunks)
    latency_ms = output.get("latency_ms")
    answer = output.get("answer")
    retrieved_sources = list(dict.fromkeys(retrieved_sources + _answer_citations(str(answer or ""))))
    return {
        "schema_version": "1.0",
        "execution_mode": execution_mode,
        "evidence_type": "measured",
        "query_id": qid,
        "query_text": case.get("question", ""),
        "query": case.get("question", ""),
        "ground_truth_intent": expected_intent(case),
        "true_intent": expected_intent(case),
        "predicted_intent": output.get("intent"),
        "router_prediction": output.get("intent"),
        "route_confidence": output.get("confidence"),
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
        "retrieved_sources": retrieved_sources,
        "retrieved_chunks": compact_chunks,
        "generated_sql": hybrid_trace.get("generated_sql") or sql_payload.get("sql_query"),
        "sql_result": hybrid_trace.get("sql_result") or sql_payload.get("rows"),
        "answer": answer,
        "final_answer": answer,
        "answer_preview": str(answer or "")[:240],
        "latency_ms": latency_ms,
        "technical_pass": score.get("passed"),
        "passed": score.get("passed"),
        "automatic_evaluation": automatic_score,
        "error_type": sorted(set(error_types)),
    }


def _retrieved_sources(sources: List[Any], chunks: List[Dict[str, Any]]) -> List[str]:
    values: List[str] = []
    for source in sources:
        if isinstance(source, dict):
            value = source.get("source") or source.get("citation") or source.get("filename")
        else:
            value = source
        if value:
            values.append(str(value))
    for chunk in chunks:
        value = chunk.get("citation") or chunk.get("source")
        if value:
            values.append(str(value))
    return list(dict.fromkeys(values))


def _answer_citations(answer: str) -> List[str]:
    """Extract file/page citations emitted by the no-Ollama answer formatter."""
    matches = re.findall(r"[A-Za-z0-9_.-]+\.pdf#p\d+", answer, flags=re.IGNORECASE)
    return list(dict.fromkeys(matches))


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
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "benchmarks" / "configs" / "full_v3.json")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "benchmarks" / "manifests" / "default_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-latency-ms", type=int, default=8000)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--references", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_name = f"{time.strftime('%Y%m%d_%H%M%S')}_{args.config.stem if args.config else 'runtime'}"
    output_dir = args.output_dir or PROJECT_ROOT / "reports" / "experiment_runs" / run_name
    run_benchmark(
        args.dataset,
        args.config,
        args.manifest,
        output_dir,
        args.seed,
        args.max_latency_ms,
        args.limit,
        reference_path=args.references,
    )

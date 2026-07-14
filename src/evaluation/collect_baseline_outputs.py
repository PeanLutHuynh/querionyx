"""Run and automatically score the frozen 20-query baseline comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.evidence import (
    REAL_EXECUTION_MODES,
    build_experiment_manifest,
    git_state,
    sha256_file,
)
from src.evaluation.automatic_scoring import AutomaticScorer, DEFAULT_REFERENCE_PATH
from src.runtime.config import RuntimeConfig
from src.runtime.logging import append_jsonl, write_json


FROZEN_SETS = PROJECT_ROOT / "benchmarks" / "manifests" / "frozen_evaluation_sets.json"
DEFAULT_CONFIG = PROJECT_ROOT / "benchmarks" / "configs" / "full_v3.json"
SYSTEMS = ["llm_only", "plain_rag", "querionyx"]
LLM_ONLY_PROMPT = (
    "Answer the enterprise question directly. Do not claim access to documents "
    "or databases. If you do not know, say that you do not know.\n"
    "Question: {question}\nAnswer:"
)


def load_frozen_cases(manifest_path: Path = FROZEN_SETS) -> tuple[Path, List[Dict[str, Any]], Dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selection = manifest["baseline_20"]
    if selection.get("systems") != SYSTEMS:
        raise RuntimeError(
            f"Frozen baseline systems mismatch: expected {SYSTEMS}, got {selection.get('systems')}"
        )
    source = manifest["datasets"][selection["source_dataset"]]
    dataset_path = PROJECT_ROOT / source["path"]
    actual_hash = sha256_file(dataset_path)
    if actual_hash != source["sha256"]:
        raise RuntimeError(
            f"Frozen baseline source hash mismatch: expected {source['sha256']}, got {actual_hash}"
        )
    payload = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    rows = payload.get("queries", payload)
    by_id = {str(row.get("id") or row.get("query_id")): row for row in rows}
    missing = [query_id for query_id in selection["query_ids"] if query_id not in by_id]
    if missing:
        raise RuntimeError(f"Frozen baseline query IDs are missing: {', '.join(missing)}")
    cases = [by_id[query_id] for query_id in selection["query_ids"]]
    return dataset_path, cases, manifest


def collect(
    *,
    output_dir: Path,
    config_path: Path,
    execution_mode: str,
    model: str,
    temperature: float,
) -> Dict[str, Any]:
    run_git_state = git_state()
    dataset_path, cases, frozen_manifest = load_frozen_cases()
    validate_protocol_configuration(frozen_manifest, config_path, model, temperature)
    config = RuntimeConfig.from_file(config_path)
    config.execution_mode = execution_mode
    config.cache_enabled = False
    config.use_llm_router = False

    llm, preflight_ms = initialize_llm_only(model, temperature)

    from src.hybrid.hybrid_handler import HybridQueryHandler
    from src.pipeline_v3 import QuerionyxPipelineV3

    plain_rag = HybridQueryHandler(runtime_config=config)
    full_system = QuerionyxPipelineV3(runtime_config=config)

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "baseline_outputs.jsonl"
    raw_path.write_text("", encoding="utf-8")
    scored_rows: List[Dict[str, Any]] = []
    technical_failures = 0
    scorer = AutomaticScorer(DEFAULT_REFERENCE_PATH)

    for index, case in enumerate(cases, start=1):
        query_id = str(case.get("id") or case.get("query_id") or f"baseline_{index:03d}")
        for system in SYSTEMS:
            started = time.perf_counter()
            try:
                output = execute_system(
                    system=system,
                    question=case["question"],
                    llm=llm,
                    plain_rag=plain_rag,
                    full_system=full_system,
                )
                error = None
            except Exception as exc:
                output = {"answer": "", "sources": [], "error": str(exc)}
                error = str(exc)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            normalized = normalize_output(system, case, output, latency_ms, error)
            scoring_output = dict(output)
            if system != "querionyx":
                scoring_output["intent"] = str(case.get("ground_truth_intent") or "").upper()
            automatic = scorer.score(case, scoring_output)
            normalized["automatic_evaluation"] = automatic
            normalized["automatic_score"] = automatic["automatic_score"]
            normalized["automatic_pass"] = automatic["automatic_pass"]
            if normalized["technical_status"] != "success":
                technical_failures += 1
            append_jsonl(raw_path, normalized)
            scored_rows.append(normalized)
            print(
                f"[{index:02d}/{len(cases)}] {query_id} {system}: "
                f"{normalized['technical_status']} {latency_ms:.2f}ms"
            )

    scorer.close()
    manifest = build_experiment_manifest(
        run_id=output_dir.name,
        execution_mode=execution_mode,
        benchmark_path=dataset_path,
        config={
            **config.to_dict(),
            "config_name": "baseline_20_automatic",
            "systems": SYSTEMS,
            "llm_only_model": model,
            "llm_only_temperature": temperature,
            "llm_only_prompt": LLM_ONLY_PROMPT,
        },
        config_path=config_path,
        query_count=len(cases),
        extra={
            "evaluation": "baseline_20_automatic",
            "frozen_selection_manifest": str(FROZEN_SETS.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "frozen_selection_manifest_sha256": sha256_file(FROZEN_SETS),
            "query_ids": [str(case.get("id") or case.get("query_id")) for case in cases],
            "system_order": SYSTEMS,
            "ollama_enabled": True,
            "ollama_preflight_ms": preflight_ms,
            "automatic_reference_file": str(DEFAULT_REFERENCE_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "automatic_reference_sha256": sha256_file(DEFAULT_REFERENCE_PATH),
            "scoring_method": "deterministic_reference_and_evidence_alignment",
        },
        git_state_at_start=run_git_state,
    )
    write_json(output_dir / "manifest.json", manifest)
    summary = {
        "query_count": len(cases),
        "output_count": len(scored_rows),
        "systems": SYSTEMS,
        "intent_distribution": dict(Counter(str(case.get("ground_truth_intent")) for case in cases)),
        "technical_failures": technical_failures,
        "scoring_method": "deterministic_reference_and_evidence_alignment",
        "per_system": summarize_systems(scored_rows),
        "thesis_reporting_allowed": manifest["thesis_reporting_allowed"],
    }
    write_json(
        output_dir / "baseline_automatic_summary.json",
        {
            "schema_version": "1.0",
            "artifact": "baseline_automatic_evaluation_summary",
            "evidence_type": manifest["evidence_type"],
            "thesis_reporting_allowed": manifest["thesis_reporting_allowed"],
            "scoring_method": summary["scoring_method"],
            "reference_file": manifest["automatic_reference_file"],
            "reference_sha256": manifest["automatic_reference_sha256"],
            "summary": summary["per_system"],
        },
    )
    return summary


def validate_protocol_configuration(
    frozen_manifest: Dict[str, Any],
    config_path: Path,
    model: str,
    temperature: float,
) -> None:
    protocol = frozen_manifest["baseline_20"]
    frozen_config = protocol["querionyx_config"]
    expected_path = (PROJECT_ROOT / frozen_config["path"]).resolve()
    if config_path.resolve() != expected_path or sha256_file(config_path) != frozen_config["sha256"]:
        raise RuntimeError("Querionyx baseline configuration does not match the frozen protocol")
    llm_protocol = protocol["llm_only"]
    prompt_hash = hashlib.sha256(LLM_ONLY_PROMPT.encode("utf-8")).hexdigest()
    if model != llm_protocol["model"] or temperature != float(llm_protocol["temperature"]):
        raise RuntimeError("LLM-only model or temperature does not match the frozen protocol")
    if prompt_hash != llm_protocol["prompt_sha256"]:
        raise RuntimeError("LLM-only prompt does not match the frozen protocol")


def initialize_llm_only(model: str, temperature: float) -> tuple[Any, float]:
    try:
        from langchain_ollama import OllamaLLM
    except Exception as exc:
        raise RuntimeError("langchain_ollama is required for the real LLM-only baseline") from exc

    llm = OllamaLLM(
        model=model,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        temperature=temperature,
        num_predict=180,
        num_ctx=1024,
        sync_client_kwargs={"timeout": 90},
    )
    started = time.perf_counter()
    try:
        llm.invoke("Reply with exactly: OK")
    except Exception as exc:
        raise RuntimeError(
            "The real LLM-only/Ollama baseline is unavailable. Collection stopped before benchmark execution."
        ) from exc
    return llm, round((time.perf_counter() - started) * 1000, 2)


def execute_system(
    *,
    system: str,
    question: str,
    llm: Any,
    plain_rag: Any,
    full_system: Any,
) -> Dict[str, Any]:
    if system == "llm_only":
        return {"answer": str(llm.invoke(LLM_ONLY_PROMPT.format(question=question))).strip(), "sources": []}
    if system == "plain_rag":
        return plain_rag.query(question, router_intent="RAG")
    if system == "querionyx":
        return full_system.query(question)
    raise ValueError(f"Unknown baseline system: {system}")


def normalize_output(
    system: str,
    case: Dict[str, Any],
    output: Dict[str, Any],
    latency_ms: float,
    error: str | None,
) -> Dict[str, Any]:
    raw = output.get("raw") or {}
    hybrid = raw.get("hybrid") or output
    trace = hybrid.get("trace") or {}
    sql_payload = raw.get("sql") or hybrid.get("sql_result") or {}
    rag_payload = raw.get("rag") or hybrid.get("rag_result") or output.get("rag_result") or {}
    sources = output.get("sources") or rag_payload.get("citations") or []
    generated_sql = trace.get("generated_sql") or sql_payload.get("sql_query") or ""
    sql_result = trace.get("sql_result") or sql_payload.get("rows") or []
    answer = str(output.get("answer") or "")
    effective_error = error or output.get("error")
    technical_status = "success" if answer.strip() and not effective_error else "failed"
    return {
        "schema_version": "1.0",
        "query_id": str(case.get("id") or case.get("query_id")),
        "system": system,
        "ground_truth_intent": str(case.get("ground_truth_intent") or "").upper(),
        "query_text": case.get("question", ""),
        "ground_truth_note": case.get("ground_truth_answer", ""),
        "answer": answer,
        "sources": sources,
        "generated_sql": generated_sql,
        "sql_result": sql_result,
        "rag_status": hybrid.get("rag_status"),
        "sql_status": hybrid.get("sql_status"),
        "fallback_mode": hybrid.get("fallback_mode"),
        "latency_ms": latency_ms,
        "technical_status": technical_status,
        "error": effective_error,
    }


def summarize_systems(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for system in SYSTEMS:
        selected = [row for row in rows if row["system"] == system]
        per_intent: Dict[str, Any] = {}
        for intent in ("RAG", "SQL", "HYBRID"):
            subset = [row for row in selected if row["ground_truth_intent"] == intent]
            if subset:
                per_intent[intent] = round(mean(row["automatic_score"] for row in subset), 4)
        summary[system] = {
            "query_count": len(selected),
            "automatic_score": round(mean(row["automatic_score"] for row in selected), 4),
            "automatic_pass_rate": round(sum(row["automatic_pass"] for row in selected) / len(selected), 4),
            "technical_success_rate": round(
                sum(row["technical_status"] == "success" for row in selected) / len(selected),
                4,
            ),
            "mean_latency_ms": round(mean(row["latency_ms"] for row in selected), 2),
            "per_intent_score": per_intent,
        }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--execution-mode", choices=sorted(REAL_EXECUTION_MODES), default="evaluation_real")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path, cases, frozen_manifest = load_frozen_cases()
    validate_protocol_configuration(frozen_manifest, args.config, args.model, args.temperature)
    if args.dry_run:
        print(f"Frozen source: {dataset_path}")
        print(f"Source SHA-256: {sha256_file(dataset_path)}")
        print(f"Selected queries: {len(cases)}")
        print(f"Distribution: {dict(Counter(case['ground_truth_intent'] for case in cases))}")
        print(f"Query IDs: {[case.get('id') for case in cases]}")
        return 0

    output_dir = args.output_dir or (
        PROJECT_ROOT
        / "reports"
        / "experiment_runs"
        / f"{time.strftime('%Y%m%d_%H%M%S')}_baseline_20"
    )
    summary = collect(
        output_dir=output_dir,
        config_path=args.config,
        execution_mode=args.execution_mode,
        model=args.model,
        temperature=args.temperature,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

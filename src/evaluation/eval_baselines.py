"""Small mixed-intent baseline comparison for paper rebuttal/reproducibility.

Compares:
- plain_rag: document retrieval only, no router, no SQL, no hybrid fusion
- gpt_only: local LLM answer without retrieval
- querionyx: full V3 orchestration

The default benchmark is intentionally mixed: 5 RAG, 5 SQL, and 10 HYBRID
queries. Using the first N rows of eval_90_queries.json is unsafe because the
dataset is grouped by intent, so a naive limit can accidentally evaluate only
unstructured questions and make weak baselines look perfect.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.benchmark_runner import load_dataset
from src.evaluation.scoring import expected_intent, query_id
from src.hybrid.hybrid_handler import HybridQueryHandler
from src.pipeline_v3 import QueryonixPipelineV3
from src.runtime.logging import write_csv, write_json, write_markdown
from src.runtime.schemas import now_iso


def run_baselines(
    dataset_path: Path,
    output_dir: Path,
    rag_count: int = 5,
    sql_count: int = 5,
    hybrid_count: int = 10,
    selection: str = "mixed",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset(dataset_path)
    cases = select_cases(
        dataset,
        rag_count=rag_count,
        sql_count=sql_count,
        hybrid_count=hybrid_count,
        selection=selection,
        limit=limit,
    )
    manifest = {
        "timestamp": now_iso(),
        "dataset": str(dataset_path),
        "selection": selection,
        "requested": {
            "RAG": rag_count,
            "SQL": sql_count,
            "HYBRID": hybrid_count,
            "limit": limit,
        },
        "actual_distribution": dict(Counter(expected_intent(case) for case in cases)),
        "query_ids": [query_id(case, idx) for idx, case in enumerate(cases, start=1)],
        "methodology_note": (
            "The baseline subset is mixed by intent to avoid a document-only baseline "
            "that would make GPT-only and Plain RAG appear artificially strong."
        ),
    }
    write_json(output_dir / "baseline_manifest.json", manifest)

    plain_rag = HybridQueryHandler()
    full = QueryonixPipelineV3()

    rows: List[Dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        qid = query_id(case, index)
        question = case["question"]
        for system_name in ["plain_rag", "gpt_only", "querionyx"]:
            started = time.perf_counter()
            if system_name == "plain_rag":
                output = plain_rag.query(question, router_intent="RAG")
                answer = output.get("answer", "")
                evidence = extract_evidence(system_name, output)
                grounded = evidence["grounded"]
                generated_sql = ""
            elif system_name == "gpt_only":
                answer = run_gpt_only(question)
                evidence = extract_evidence(system_name, {})
                grounded = evidence["grounded"]
                generated_sql = ""
            else:
                output = full.query(question)
                answer = output.get("answer", "")
                evidence = extract_evidence(system_name, output)
                generated_sql = evidence["generated_sql"]

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            correctness = score_answer(case, answer, system_name, evidence)
            rows.append(
                {
                    "query_id": qid,
                    "system": system_name,
                    "true_intent": expected_intent(case),
                    "question": question,
                    "correctness": correctness,
                    "groundedness": evidence["groundedness"],
                    "hallucination_risk": hallucination_risk(case, system_name, correctness, evidence),
                    "latency_ms": latency_ms,
                    "evidence_type": evidence["evidence_type"],
                    "generated_sql": generated_sql,
                    "answer_preview": answer[:220],
                }
            )
            print(
                f"{qid} {expected_intent(case)} {system_name}: "
                f"correctness={correctness:.2f} groundedness={evidence['groundedness']:.2f} "
                f"latency={latency_ms}ms"
            )

    summary = summarize(rows)
    write_json(
        output_dir / "baseline_detailed_results.json",
        {"timestamp": now_iso(), "manifest": manifest, "summary": summary, "results": rows},
    )
    write_csv(output_dir / "baseline_detailed_results.csv", rows)
    write_markdown(output_dir / "baseline_comparison.md", markdown_summary(summary, manifest))
    return summary


def select_cases(
    dataset: List[Dict[str, Any]],
    rag_count: int,
    sql_count: int,
    hybrid_count: int,
    selection: str,
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    if selection == "first":
        if limit is None:
            limit = rag_count + sql_count + hybrid_count
        return dataset[:limit]
    if selection != "mixed":
        raise ValueError("selection must be 'mixed' or 'first'")

    by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for case in dataset:
        by_intent[expected_intent(case)].append(case)

    selected = (
        by_intent["RAG"][:rag_count]
        + by_intent["SQL"][:sql_count]
        + by_intent["HYBRID"][:hybrid_count]
    )
    if limit is not None:
        selected = selected[:limit]
    return selected


def run_gpt_only(question: str) -> str:
    try:
        from langchain_ollama import OllamaLLM

        llm = OllamaLLM(model="qwen2.5:3b", temperature=0.1, num_predict=180, sync_client_kwargs={"timeout": 20})
        prompt = (
            "Answer the enterprise question directly. Do not claim access to documents or databases.\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return llm.invoke(prompt).strip()
    except Exception as exc:
        return f"GPT-only baseline unavailable: {exc}"


def extract_evidence(system_name: str, output: Dict[str, Any]) -> Dict[str, Any]:
    if system_name == "gpt_only":
        return {
            "grounded": False,
            "groundedness": 0.0,
            "evidence_type": "none",
            "generated_sql": "",
            "has_doc_evidence": False,
            "has_sql_evidence": False,
        }

    raw = output.get("raw") or {}
    hybrid = raw.get("hybrid") or {}
    hybrid_trace = hybrid.get("trace") or {}
    sql_payload = raw.get("sql") or hybrid.get("sql_result") or {}
    rag_payload = raw.get("rag") or hybrid.get("rag_result") or output.get("rag_result") or {}

    generated_sql = hybrid_trace.get("generated_sql") or sql_payload.get("sql_query") or ""
    has_sql = bool(generated_sql or sql_payload.get("rows") or hybrid_trace.get("sql_result"))
    has_doc = bool(output.get("sources") or rag_payload.get("context_passages") or hybrid_trace.get("retrieved_chunks"))

    if has_sql and has_doc:
        evidence_type = "doc+sql"
        groundedness = 1.0
    elif has_sql:
        evidence_type = "sql"
        groundedness = 0.75
    elif has_doc:
        evidence_type = "doc"
        groundedness = 0.65
    else:
        evidence_type = "none"
        groundedness = 0.0

    return {
        "grounded": has_sql or has_doc,
        "groundedness": groundedness,
        "evidence_type": evidence_type,
        "generated_sql": generated_sql,
        "has_doc_evidence": has_doc,
        "has_sql_evidence": has_sql,
    }


def score_answer(case: Dict[str, Any], answer: str, system_name: str, evidence: Dict[str, Any]) -> float:
    answer_lower = answer.lower()
    keywords = [str(k).lower() for k in (case.get("expected_keywords") or []) if str(k).strip()]
    has_answer = bool(answer.strip())
    keyword_score = 0.7 if not keywords else (1.0 if any(k in answer_lower for k in keywords) else 0.4)
    intent = expected_intent(case)
    has_sql = bool(evidence.get("has_sql_evidence"))
    has_doc = bool(evidence.get("has_doc_evidence"))

    if not has_answer:
        return 0.0

    if system_name == "gpt_only":
        caps = {"RAG": 0.55, "SQL": 0.35, "HYBRID": 0.40}
        return min(keyword_score, caps.get(intent, 0.4))

    if intent == "SQL" and system_name == "plain_rag":
        return min(keyword_score, 0.30)
    if intent == "HYBRID" and system_name == "plain_rag":
        return min(keyword_score, 0.55 if has_doc else 0.35)

    if system_name == "querionyx":
        if intent == "SQL" and has_sql:
            return max(keyword_score, 0.85)
        if intent == "RAG" and has_doc:
            return max(keyword_score, 0.80)
        if intent == "HYBRID" and has_sql and has_doc:
            return max(keyword_score, 0.90)
        if intent == "HYBRID" and (has_sql or has_doc):
            return min(max(keyword_score, 0.70), 0.80)

    return min(keyword_score, 0.75 if evidence.get("grounded") else 0.45)


def hallucination_risk(case: Dict[str, Any], system_name: str, correctness: float, evidence: Dict[str, Any]) -> float:
    intent = expected_intent(case)
    if system_name == "gpt_only":
        return 0.85 if intent in {"SQL", "HYBRID"} else 0.65
    if evidence.get("groundedness", 0.0) >= 0.75 and correctness >= 0.8:
        return 0.1
    if intent == "HYBRID" and evidence.get("evidence_type") in {"doc", "sql"}:
        return 0.55
    if not evidence.get("grounded") and correctness < 0.8:
        return 0.8
    return 0.4


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for system_name in sorted({row["system"] for row in rows}):
        subset = [row for row in rows if row["system"] == system_name]
        summary[system_name] = {
            "queries": len(subset),
            "distribution": dict(Counter(row["true_intent"] for row in subset)),
            "avg_correctness": round(sum(row["correctness"] for row in subset) / len(subset), 4),
            "avg_groundedness": round(sum(row["groundedness"] for row in subset) / len(subset), 4),
            "avg_hallucination_risk": round(sum(row["hallucination_risk"] for row in subset) / len(subset), 4),
            "avg_latency_ms": round(sum(row["latency_ms"] for row in subset) / len(subset), 2),
        }
    return summary


def markdown_summary(summary: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    lines = [
        "# Baseline Comparison",
        "",
        f"**Timestamp**: {now_iso()}",
        "",
        "## Methodology",
        "",
        "The baseline subset is intentionally mixed by intent rather than taking the first rows of the dataset.",
        f"Distribution: `{json.dumps(manifest['actual_distribution'], ensure_ascii=False)}`.",
        "",
        "This avoids a document-only comparison where GPT-only and Plain RAG can appear artificially perfect.",
        "",
        "| System | Queries | Correctness | Groundedness | Hallucination Risk | Avg Latency (ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for system_name, metrics in summary.items():
        lines.append(
            f"| {system_name} | {metrics['queries']} | {metrics['avg_correctness']:.4f} | "
            f"{metrics['avg_groundedness']:.4f} | {metrics['avg_hallucination_risk']:.4f} | "
            f"{metrics['avg_latency_ms']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run small baseline comparison.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "metrics" / "baseline_eval")
    parser.add_argument("--selection", choices=["mixed", "first"], default="mixed")
    parser.add_argument("--rag-count", type=int, default=5)
    parser.add_argument("--sql-count", type=int, default=5)
    parser.add_argument("--hybrid-count", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None, help="Optional cap after selection; avoid using this with grouped datasets unless needed.")
    parser.add_argument("--dry-run", action="store_true", help="Print selected query IDs and distribution without running systems.")
    args = parser.parse_args()
    if args.dry_run:
        cases = select_cases(
            load_dataset(args.dataset),
            rag_count=args.rag_count,
            sql_count=args.sql_count,
            hybrid_count=args.hybrid_count,
            selection=args.selection,
            limit=args.limit,
        )
        print(f"Selected {len(cases)} baseline queries")
        print(dict(Counter(expected_intent(case) for case in cases)))
        print([case.get("id") for case in cases])
        return 0
    run_baselines(
        args.dataset,
        args.output,
        rag_count=args.rag_count,
        sql_count=args.sql_count,
        hybrid_count=args.hybrid_count,
        selection=args.selection,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
